import uuid
from typing import Any, Dict, Union
import logging
import requests
import json
import warnings
import os
from urllib3.exceptions import InsecureRequestWarning
from dotenv import load_dotenv
from neuro_san.interfaces.coded_tool import CodedTool

# Suppress SSL warnings
warnings.filterwarnings('ignore', category=InsecureRequestWarning)

# Load environment variables
load_dotenv('.env')


class IssueCreatorTool(CodedTool):
    """Create actual ServiceNow incident tickets via REST API."""

    def __init__(self):
        """Initialize with ServiceNow configuration."""
        self.snow_instance = os.getenv('SNOW_INSTANCE')
        self.username = os.getenv('SNOW_USERNAME')
        self.password = os.getenv('SNOW_PASSWORD')
        self.caller_id = os.getenv('SNOW_CALLER_ID')

        # Enable mock mode if credentials are missing
        self.mock_mode = not all([self.snow_instance, self.username, self.password, self.caller_id])

        if self.mock_mode:
            logging.info("[IssueCreatorTool] Running in MOCK mode - ServiceNow credentials not configured")
            self.api_url = None
        else:
            self.api_url = f"{self.snow_instance}/api/now/table/incident"

    def invoke(self, args: Dict[str, Any], sly_data: Dict[str, Any]) -> Union[str, Dict[str, Any]]:
        """
        Create a ServiceNow incident and return the incident number.

        Args:
            args: Dictionary containing incident details:
                - short_description: Brief description of the incident
                - description: Detailed description (optional)
                - urgency: 1-3 (optional, defaults to 3)
                - impact: 1-3 (optional, defaults to 3)
                - category: Category (optional, defaults to 'inquiry')
            sly_data: Additional context data

        Returns:
            Incident number string or error dictionary
        """
        # Return mock ticket if in mock mode
        if self.mock_mode:
            mock_ticket = f"INC{uuid.uuid4().int % 10000000:07d}"
            logging.info("[IssueCreatorTool] MOCK MODE - Generated mock ticket: %s", mock_ticket)
            return mock_ticket

        try:
            # Extract incident details from args
            short_description = args.get('short_description', 'Incident created via automation')
            description = args.get('description', 'This incident was created via automated workflow')
            urgency = str(args.get('urgency', '3'))
            impact = str(args.get('impact', '3'))
            category = args.get('category', 'inquiry')

            # Log the input
            logging.info(
                "[ONSTicketCreatorTool] Creating incident with short_description=%s",
                short_description
            )

            # Prepare incident data
            incident_data = {
                "short_description": short_description,
                "description": description,
                "urgency": urgency,
                "impact": impact,
                "category": category,
                "caller_id": self.caller_id
            }

            # Query parameters
            params = {
                "sysparm_fields": "number,sys_id,short_description,state",
                "sysparm_display_value": "true"
            }

            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }

            # Make API request
            response = requests.post(
                self.api_url,
                params=params,
                json=incident_data,
                headers=headers,
                auth=(self.username, self.password),
                timeout=30,
                verify=False
            )

            if response.status_code == 201:
                result = response.json()
                if 'result' in result:
                    incident = result['result']
                    incident_number = incident.get('number', '')
                    sys_id = incident.get('sys_id', '')

                    logging.info(
                        "[ONSTicketCreatorTool] Successfully created incident %s (sys_id=%s)",
                        incident_number, sys_id
                    )

                    # Return incident number in expected format
                    return incident_number
                else:
                    error_msg = "Unexpected response format from ServiceNow"
                    logging.error("[ONSTicketCreatorTool] %s", error_msg)
                    return {"error": error_msg, "response": result}

            elif response.status_code == 401:
                error_msg = "Authentication failed - check ServiceNow credentials"
                logging.error("[ONSTicketCreatorTool] %s", error_msg)
                return {"error": error_msg}

            else:
                error_msg = f"Failed to create incident - Status: {response.status_code}"
                logging.error("[ONSTicketCreatorTool] %s", error_msg)
                try:
                    error_details = response.json()
                    return {"error": error_msg, "details": error_details}
                except:
                    return {"error": error_msg, "response": response.text[:500]}

        except requests.exceptions.ConnectionError as e:
            error_msg = f"Cannot connect to ServiceNow: {str(e)[:200]}"
            logging.error("[ONSTicketCreatorTool] %s", error_msg)
            return {"error": error_msg}

        except requests.exceptions.Timeout:
            error_msg = "Request to ServiceNow timed out"
            logging.error("[ONSTicketCreatorTool] %s", error_msg)
            return {"error": error_msg}

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logging.error("[ONSTicketCreatorTool] %s", error_msg)
            return {"error": error_msg}