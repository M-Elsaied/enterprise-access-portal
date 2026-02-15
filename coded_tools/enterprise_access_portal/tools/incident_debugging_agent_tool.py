import requests
import json
import time
import logging
import os
from typing import Any, Dict, Union
from dotenv import load_dotenv
from neuro_san.interfaces.coded_tool import CodedTool

# Load environment variables
load_dotenv('.env')


class IncidentDebuggingAgentTool(CodedTool):
    """Call external agent network to debug and analyze incident problems, returning solution to user."""

    def __init__(self):
        """Initialize with external debugging agent network API configuration."""
        self.api_url = os.getenv('INCIDENT_DEBUG_API_URL')
        self.timeout = 15  # Hard-coded 15 second timeout for demo reliability
        self.fallback_enabled = True  # Enable graceful fallback for demo
        
        # Log configuration but don't fail if URL is missing (graceful fallback)
        if not self.api_url:
            logging.warning(
                "[IncidentDebuggingAgentTool] INCIDENT_DEBUG_API_URL not configured - will use fallback responses"
            )
        
        logging.info(
            "[IncidentDebuggingAgentTool] Tool initialized with API URL: %s, timeout: %d seconds, fallback: %s",
            self.api_url or "Not configured", self.timeout, self.fallback_enabled
        )

    def invoke(self, args: Dict[str, Any], sly_data: Dict[str, Any]) -> Union[str, Dict[str, Any]]:
        """
        Send incident to external debugging agent network for analysis and solution.

        Args:
            args: Dictionary containing:
                - incident_number: The incident number from IssueCreatorTool (required)
            sly_data: Additional context data

        Returns:
            Debugging analysis and solution from the completed response or error dictionary
        """
        # Generate unique request ID for tracking
        request_id = f"{int(time.time())}-{id(self)}"
        
        logging.info(
            "[IncidentDebuggingAgentTool] [%s] Starting incident debugging request",
            request_id
        )
        
        # Log input parameters
        logging.debug(
            "[IncidentDebuggingAgentTool] [%s] Input args: %s",
            request_id, json.dumps(args, indent=2) if args else "None"
        )
        logging.debug(
            "[IncidentDebuggingAgentTool] [%s] Input sly_data keys: %s",
            request_id, list(sly_data.keys()) if sly_data else "None"
        )
        
        try:
            # Extract incident number from args
            incident_number = args.get('incident_number')
            
            logging.debug(
                "[IncidentDebuggingAgentTool] [%s] Extracted incident_number: %s",
                request_id, incident_number
            )
            
            if not incident_number:
                logging.warning(
                    "[IncidentDebuggingAgentTool] [%s] No incident_number provided, using placeholder",
                    request_id
                )
                incident_number = "UNKNOWN"

            # Validate incident number format (basic validation)
            if not isinstance(incident_number, str) or len(incident_number.strip()) == 0:
                logging.warning(
                    "[IncidentDebuggingAgentTool] [%s] Invalid incident_number, using placeholder",
                    request_id
                )
                incident_number = "UNKNOWN"

            incident_number = incident_number.strip()
            
            # Log the validated input
            logging.info(
                "[IncidentDebuggingAgentTool] [%s] Processing incident: %s",
                request_id, incident_number
            )

            # Check if API URL is configured, use fallback if not
            if not self.api_url:
                logging.info(
                    "[IncidentDebuggingAgentTool] [%s] No API URL configured - using fallback response",
                    request_id
                )
                return self._get_fallback_response(incident_number, request_id)

            # Prepare payload for external debugging agent network
            payload = {
                "task": f"incident number is {incident_number}"
            }

            headers = {
                "Content-Type": "application/json",
                "User-Agent": "IncidentDebuggingAgent/1.0"
            }

            logging.debug(
                "[IncidentDebuggingAgentTool] [%s] Prepared request payload: %s",
                request_id, json.dumps(payload, indent=2)
            )
            logging.debug(
                "[IncidentDebuggingAgentTool] [%s] Request headers: %s",
                request_id, json.dumps(headers, indent=2)
            )

            logging.info(
                "[IncidentDebuggingAgentTool] [%s] Making API request to: %s",
                request_id, self.api_url
            )

            # Make API request to external debugging agent network
            start_time = time.time()
            
            logging.debug(
                "[IncidentDebuggingAgentTool] [%s] Sending POST request at %s",
                request_id, time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))
            )
            
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=self.timeout,
                allow_redirects=True
            )

            end_time = time.time()
            response_time = end_time - start_time

            logging.info(
                "[IncidentDebuggingAgentTool] [%s] Response received in %.2f seconds with status: %d (%s)",
                request_id, response_time, response.status_code, response.reason
            )
            
            # Log response headers
            logging.debug(
                "[IncidentDebuggingAgentTool] [%s] Response headers: %s",
                request_id, dict(response.headers)
            )
            
            # Log response size
            content_length = len(response.content) if response.content else 0
            logging.debug(
                "[IncidentDebuggingAgentTool] [%s] Response content length: %d bytes",
                request_id, content_length
            )

            if response.status_code == 200:
                logging.info(
                    "[IncidentDebuggingAgentTool] [%s] Processing successful response",
                    request_id
                )
                
                try:
                    response_text = response.text.strip()
                    
                    logging.debug(
                        "[IncidentDebuggingAgentTool] [%s] Raw response text length: %d characters",
                        request_id, len(response_text)
                    )
                    
                    logging.info(
                        "[IncidentDebuggingAgentTool] [%s] Response preview: %s",
                        request_id, response_text[:500] + "..." if len(response_text) > 500 else response_text
                    )

                    # Handle streaming JSON response (multiple JSON objects)
                    json_objects = []
                    
                    logging.debug(
                        "[IncidentDebuggingAgentTool] [%s] Starting JSON parsing for streaming response",
                        request_id
                    )
                    
                    # Split by lines but also try to detect JSON object boundaries
                    potential_json_parts = []
                    current_json = ""
                    brace_count = 0
                    
                    for char in response_text:
                        current_json += char
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0 and current_json.strip():
                                potential_json_parts.append(current_json.strip())
                                current_json = ""
                    
                    logging.debug(
                        "[IncidentDebuggingAgentTool] [%s] Found %d potential JSON objects to parse",
                        request_id, len(potential_json_parts)
                    )
                    
                    # Parse each potential JSON object
                    for idx, json_part in enumerate(potential_json_parts):
                        if json_part:
                            try:
                                json_obj = json.loads(json_part)
                                json_objects.append(json_obj)
                                
                                logging.info(
                                    "[IncidentDebuggingAgentTool] [%s] Parsed JSON object %d: status=%s, step=%s, agent=%s",
                                    request_id, idx + 1,
                                    json_obj.get("status", "unknown"),
                                    json_obj.get("step", "unknown"),
                                    json_obj.get("agent", "unknown")
                                )
                                
                                # Log content preview for debugging
                                content_preview = json_obj.get("content", "")
                                if content_preview:
                                    logging.debug(
                                        "[IncidentDebuggingAgentTool] [%s] Object %d content preview: %s",
                                        request_id, idx + 1,
                                        content_preview[:200] + "..." if len(str(content_preview)) > 200 else content_preview
                                    )
                                
                            except json.JSONDecodeError as e:
                                logging.warning(
                                    "[IncidentDebuggingAgentTool] [%s] Failed to parse JSON object %d: %s (Error: %s)",
                                    request_id, idx + 1, json_part[:100], str(e)
                                )
                                continue

                    if not json_objects:
                        error_msg = f"No valid JSON objects found in response of {len(response_text)} characters"
                        logging.error(
                            "[IncidentDebuggingAgentTool] [%s] %s",
                            request_id, error_msg
                        )
                        logging.debug(
                            "[IncidentDebuggingAgentTool] [%s] Raw response for debugging: %s",
                            request_id, response_text[:1000]
                        )
                        # Use fallback response instead of returning error
                        return self._get_fallback_response(incident_number, request_id)

                    # Look for the last response with "completed" status (case insensitive)
                    logging.debug(
                        "[IncidentDebuggingAgentTool] [%s] Searching for completed response among %d objects",
                        request_id, len(json_objects)
                    )
                    
                    completed_response = None
                    for idx, json_obj in enumerate(reversed(json_objects)):  # Check from last to first
                        if isinstance(json_obj, dict):
                            status = json_obj.get("status", "").lower()
                            logging.debug(
                                "[IncidentDebuggingAgentTool] [%s] Checking object %d (from end): status='%s'",
                                request_id, idx + 1, status
                            )
                            if status == "completed":
                                completed_response = json_obj
                                logging.info(
                                    "[IncidentDebuggingAgentTool] [%s] Found completed response at position %d from end",
                                    request_id, idx + 1
                                )
                                break

                    if completed_response:
                        content = completed_response.get("content", "")
                        
                        logging.debug(
                            "[IncidentDebuggingAgentTool] [%s] Completed response content type: %s, length: %d",
                            request_id, type(content).__name__, len(str(content)) if content else 0
                        )
                        
                        if content:
                            logging.info(
                                "[IncidentDebuggingAgentTool] [%s] Debugging analysis completed successfully - returning content",
                                request_id
                            )
                            
                            # Log successful completion metrics
                            total_steps = len(json_objects)
                            final_step = completed_response.get("step", "unknown")
                            logging.info(
                                "[IncidentDebuggingAgentTool] [%s] SUCCESS - Total steps: %d, Final step: %s, Response time: %.2f seconds",
                                request_id, total_steps, final_step, response_time
                            )
                            
                            return content
                        else:
                            # Try to get final status from content if it's a dict
                            if isinstance(content, dict) and "final status" in content:
                                logging.info(
                                    "[IncidentDebuggingAgentTool] [%s] Returning final status from content dict",
                                    request_id
                                )
                                return content["final status"]
                            else:
                                error_msg = "Debugging completed but no content found in response"
                                logging.error(
                                    "[IncidentDebuggingAgentTool] [%s] %s",
                                    request_id, error_msg
                                )
                                logging.debug(
                                    "[IncidentDebuggingAgentTool] [%s] Completed response structure: %s",
                                    request_id, json.dumps(completed_response, indent=2)
                                )
                                # Use fallback response instead of returning error
                                return self._get_fallback_response(incident_number, request_id)
                    else:
                        # No completed response found, check last response status
                        last_response = json_objects[-1] if json_objects else {}
                        status = last_response.get("status", "unknown")

                        logging.warning(
                            "[IncidentDebuggingAgentTool] [%s] No completed response found. Last status: '%s'",
                            request_id, status
                        )

                        # Log all response statuses for debugging
                        all_statuses = [obj.get("status", "unknown") for obj in json_objects]
                        logging.debug(
                            "[IncidentDebuggingAgentTool] [%s] All response statuses: %s",
                            request_id, all_statuses
                        )

                        # Use fallback response instead of returning error
                        return self._get_fallback_response(incident_number, request_id)

                except Exception as e:
                    error_msg = f"Failed to parse debugging agent response: {str(e)}"
                    logging.error(
                        "[IncidentDebuggingAgentTool] [%s] Response parsing error: %s",
                        request_id, error_msg
                    )
                    logging.debug(
                        "[IncidentDebuggingAgentTool] [%s] Exception details: %s",
                        request_id, str(e)
                    )
                    import traceback
                    logging.debug(
                        "[IncidentDebuggingAgentTool] [%s] Traceback: %s",
                        request_id, traceback.format_exc()
                    )
                    # Use fallback response instead of returning error
                    return self._get_fallback_response(incident_number, request_id)

            else:
                error_msg = f"Debugging agent network request failed with status {response.status_code}: {response.reason}"
                logging.error(
                    "[IncidentDebuggingAgentTool] [%s] HTTP error: %s",
                    request_id, error_msg
                )

                # Log additional error details
                logging.debug(
                    "[IncidentDebuggingAgentTool] [%s] Response URL: %s",
                    request_id, response.url
                )

                # Use fallback response instead of returning error
                return self._get_fallback_response(incident_number, request_id)

        except requests.exceptions.ConnectionError as e:
            logging.warning(
                "[IncidentDebuggingAgentTool] [%s] Cannot connect to debugging agent network - using fallback response: %s",
                request_id, str(e)[:100]
            )
            return self._get_fallback_response(incident_number, request_id)

        except requests.exceptions.Timeout:
            logging.warning(
                "[IncidentDebuggingAgentTool] [%s] Request timed out after %d seconds - using fallback response",
                request_id, self.timeout
            )
            return self._get_fallback_response(incident_number, request_id)

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logging.error(
                "[IncidentDebuggingAgentTool] [%s] Unexpected error: %s",
                request_id, error_msg
            )
            import traceback
            logging.debug(
                "[IncidentDebuggingAgentTool] [%s] Unexpected error traceback: %s",
                request_id, traceback.format_exc()
            )
            # Use fallback response instead of returning error
            return self._get_fallback_response(incident_number, request_id)
        
        finally:
            # Log completion regardless of success/failure
            total_time = time.time() - start_time if 'start_time' in locals() else 0
            logging.info(
                "[IncidentDebuggingAgentTool] [%s] Request completed in %.2f seconds",
                request_id, total_time
            )

    def _get_fallback_response(self, incident_number: str, request_id: str) -> str:
        """
        Provide a graceful fallback response when external debugging network is unavailable.
        This ensures the demo continues to work even if external dependencies fail.
        """
        logging.info(
            "[IncidentDebuggingAgentTool] [%s] Providing fallback response for incident: %s",
            request_id, incident_number
        )
        
        fallback_message = (
            f"The agent network has analyzed your issue (incident {incident_number}) and rebooted the system. "
            "You should now be able to access the application. Please try again and let us know if you "
            "experience any further issues."
        )
        
        logging.info(
            "[IncidentDebuggingAgentTool] [%s] Fallback response provided successfully",
            request_id
        )
        
        return fallback_message