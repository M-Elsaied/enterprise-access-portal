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


class ONSTicketVerificationTool(CodedTool):
    """Verify ServiceNow incident tickets via REST API."""

    def __init__(self):
        """Initialize with ServiceNow configuration."""
        self.snow_instance = os.getenv('SNOW_INSTANCE')
        self.username = os.getenv('SNOW_USERNAME')
        self.password = os.getenv('SNOW_PASSWORD')

        # Enable mock mode if credentials are missing
        self.mock_mode = not all([self.snow_instance, self.username, self.password])

        if self.mock_mode:
            logging.info("[ONSTicketVerificationTool] Running in MOCK mode - ServiceNow credentials not configured")
            self.api_url = None
        else:
            self.api_url = f"{self.snow_instance}/api/now/table/incident"

    def invoke(self, args: Dict[str, Any], sly_data: Dict[str, Any]) -> Union[str, bool, Dict[str, Any]]:
        """
        Verify a ServiceNow incident exists and retrieve its details.

        Args:
            args: Dictionary containing:
                - ticket_number: The incident number to verify (e.g., 'INC0010374')
                - return_details: If True, return full incident details (optional, defaults to False)
            sly_data: Additional context data

        Returns:
            - If return_details is False: Boolean indicating if ticket exists
            - If return_details is True: Dictionary with incident details or error
        """
        ticket_number = str(args.get("ticket_number", "")).strip()
        return_details = args.get("return_details", False)

        logging.info(
            "[ONSTicketVerificationTool] Input ticket_number=%s, return_details=%s",
            ticket_number, return_details
        )

        # Return mock response if in mock mode
        if self.mock_mode:
            logging.info("[ONSTicketVerificationTool] MOCK MODE - Returning mock verification for %s", ticket_number)
            if return_details:
                return {
                    "number": ticket_number,
                    "state": "New",
                    "short_description": "Access request incident",
                    "verified": True
                }
            return True

        # Basic validation - check if ticket number format is valid
        if not ticket_number:
            logging.error("[ONSTicketVerificationTool] Empty ticket number provided")
            return False if not return_details else {"error": "Empty ticket number"}

        # Check if it's a valid ServiceNow incident number format
        if not ticket_number.startswith("INC"):
            logging.warning(
                "[ONSTicketVerificationTool] Invalid format - expected INCxxxxxxx, got %s",
                ticket_number
            )
            return False if not return_details else {"error": f"Invalid ticket format: {ticket_number}"}

        try:
            # Query parameters
            params = {
                "sysparm_query": f"number={ticket_number}",
                "sysparm_limit": "1",
                "sysparm_display_value": "true",
                "sysparm_fields": "number,sys_id,short_description,state,urgency,impact,priority,category,opened_at,opened_by,caller_id,description"
            }

            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }

            # Make API request
            response = requests.get(
                self.api_url,
                params=params,
                headers=headers,
                auth=(self.username, self.password),
                timeout=30,
                verify=False
            )

            if response.status_code == 200:
                result = response.json()

                if 'result' in result and isinstance(result['result'], list):
                    if len(result['result']) > 0:
                        incident = result['result'][0]
                        logging.info(
                            "[ONSTicketVerificationTool] Incident %s found - State: %s",
                            ticket_number,
                            incident.get('state', 'Unknown')
                        )

                        if return_details:
                            # Return full incident details
                            return {
                                "exists": True,
                                "incident": incident,
                                "summary": {
                                    "number": incident.get('number'),
                                    "short_description": incident.get('short_description'),
                                    "state": incident.get('state'),
                                    "urgency": incident.get('urgency'),
                                    "impact": incident.get('impact'),
                                    "opened_at": incident.get('opened_at'),
                                    "caller": incident.get('caller_id')
                                }
                            }
                        else:
                            # Return simple boolean
                            return True
                    else:
                        logging.info(
                            "[ONSTicketVerificationTool] Incident %s not found",
                            ticket_number
                        )
                        if return_details:
                            return {"exists": False, "error": f"Incident {ticket_number} not found"}
                        else:
                            return False
                else:
                    error_msg = "Unexpected response format from ServiceNow"
                    logging.error("[ONSTicketVerificationTool] %s", error_msg)
                    if return_details:
                        return {"error": error_msg, "response": result}
                    else:
                        return False

            elif response.status_code == 401:
                error_msg = "Authentication failed - check ServiceNow credentials"
                logging.error("[ONSTicketVerificationTool] %s", error_msg)
                if return_details:
                    return {"error": error_msg}
                else:
                    return False

            else:
                error_msg = f"Failed to verify incident - Status: {response.status_code}"
                logging.error("[ONSTicketVerificationTool] %s", error_msg)
                if return_details:
                    try:
                        error_details = response.json()
                        return {"error": error_msg, "details": error_details}
                    except:
                        return {"error": error_msg, "response": response.text[:500]}
                else:
                    return False

        except requests.exceptions.ConnectionError as e:
            error_msg = f"Cannot connect to ServiceNow: {str(e)[:200]}"
            logging.error("[ONSTicketVerificationTool] %s", error_msg)
            if return_details:
                return {"error": error_msg}
            else:
                return False

        except requests.exceptions.Timeout:
            error_msg = "Request to ServiceNow timed out"
            logging.error("[ONSTicketVerificationTool] %s", error_msg)
            if return_details:
                return {"error": error_msg}
            else:
                return False

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logging.error("[ONSTicketVerificationTool] %s", error_msg)
            if return_details:
                return {"error": error_msg}
            else:
                return False
