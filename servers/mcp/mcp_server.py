"""Enterprise Access Portal MCP Server using FastMCP"""
import json
import logging
from pathlib import Path
from typing import Any, Dict

from mcp.server.fastmcp import FastMCP

# Create the MCP server
mcp = FastMCP("EnterpriseAccessPortal", port=8000)

# --- IMPORTANT: Path to knowdocs from the server location ---
KNOWDOCS_PATH = Path(__file__).parent.parent.parent / "coded_tools" / "enterprise_access_portal" / "tools" / "knowdocs"

# Prompt templates
from prompt_templates import PROMPT_TEMPLATES

@mcp.tool()
def user_verification(user_id: str, dataiku_id: str) -> bool:
    """
    Verifies a user's identity against the central users table.
    
    Args:
        user_id: The user's ID in the system
        dataiku_id: The user's Dataiku ID
    """
    logging.info(f"[MCP-Tool] Verifying user_id={user_id}, dataiku_id={dataiku_id}")
    
    file_path = KNOWDOCS_PATH / "users.md"
    try:
        lines = [line.strip() for line in file_path.read_text(encoding="utf-8").splitlines()]
        rows = [ln for ln in lines if "|" in ln][2:]  # Skip header + separator
        
        for row in rows:
            parts = [p.strip() for p in row.strip("|").split("|")]
            if len(parts) >= 5:
                if (parts[0] == user_id and 
                    parts[2] == dataiku_id and 
                    parts[4].upper() == "A"):
                    logging.info("[MCP-Tool] ✅ User verification successful")
                    return True
        
        logging.warning("[MCP-Tool] ❌ User verification failed - no match found")
        return False
    except Exception as e:
        logging.error(f"Error in user verification: {e}")
        return False

@mcp.tool()
def training_requirements(env: str) -> Dict[str, Any]:
    """
    Returns training requirements for a specific environment.
    
    Args:
        env: The environment type (DEV, QA, PROD, CORE++)
    """
    env = env.upper()
    logging.info(f"[MCP-Tool] Getting requirements for env={env}")
    
    file_path = KNOWDOCS_PATH / "training_requirements.md"
    try:
        text = file_path.read_text(encoding="utf-8")
        data = json.loads(text[text.find("{"):text.rfind("}") + 1])
        return data.get(env, {})
    except Exception as e:
        logging.error(f"Error getting training requirements: {e}")
        return {"error": str(e)}

@mcp.tool()
def training_completions(user_id: str, training_name: str, certificate_id: str) -> bool:
    """
    Checks if a user has completed a specific training using their certificate ID.
    
    Args:
        user_id: The user's ID in the system
        training_name: The name of the training to verify
        certificate_id: The user's provided certificate ID for the training
    """
    logging.info(f"[MCP-Tool] Checking completion for user {user_id}, training {training_name}")
    
    file_path = KNOWDOCS_PATH / "training_completions.md"
    try:
        lines = [line.strip() for line in file_path.read_text(encoding="utf-8").splitlines()]
        rows = [ln for ln in lines if "|" in ln][2:]
        
        for row in rows:
            parts = [p.strip() for p in row.strip("|").split("|")]
            if len(parts) >= 4:
                if (parts[0] == user_id and 
                    parts[2] == training_name and 
                    parts[3] == certificate_id):
                    logging.info("[MCP-Tool] ✅ Training completion verified")
                    return True
        
        logging.warning("[MCP-Tool] ❌ Training completion not found")
        return False
    except Exception as e:
        logging.error(f"Error checking training completions: {e}")
        return False

@mcp.tool()
def approvals_required(env: str, access_type: str) -> bool:
    """
    Checks if a requested access type is permitted for a given environment based on company policies.
    
    Args:
        env: The environment type (e.g., DEV, PROD)
        access_type: The type of access requested (e.g., Read, Write)
    """
    env = env.upper()
    access_type = access_type.capitalize()
    logging.info(f"[MCP-Tool] Checking policy for env={env}, access={access_type}")
    
    file_path = KNOWDOCS_PATH / "access_policies.md"
    try:
        lines = [line.strip() for line in file_path.read_text(encoding="utf-8").splitlines()]
        rows = [ln for ln in lines if "|" in ln][2:]
        for row in rows:
            parts = [p.strip() for p in row.strip("|").split("|")]
            if len(parts) >= 3 and parts[0].upper() == env and parts[1].capitalize() == access_type:
                return parts[2].lower() == "yes"
        return False
    except Exception as e:
        logging.error(f"Error checking approvals: {e}")
        return False

@mcp.tool()
def prompt_retriever(agent_name: str, use_case: str = None) -> str:
    """
    Retrieves agent instructions/prompts from the MCP server.
    This tool allows agents to dynamically fetch their instructions.
    
    Args:
        agent_name: The name of the agent to get instructions for
        use_case: The specific use case for agents that support multiple applications (optional)
    """
    logging.info(f"[MCP-Tool] Retrieving prompt for agent: {agent_name}, use_case: {use_case}")
    
    if not agent_name:
        return "Error: agent_name parameter is required"

    
    prompt_name = agent_name
    if not prompt_name:
        return f"Error: No prompt found for agent '{agent_name}'. Available agents: ['access_request_orchestrator_agent', 'ons_agent']"
    
    if prompt_name not in PROMPT_TEMPLATES:
        return f"Error: Prompt template '{prompt_name}' not found in server"
    
    prompt_template = PROMPT_TEMPLATES[prompt_name]
    
    # Handle nested structure for agents with multiple use cases
    if isinstance(prompt_template, dict):
        if not use_case:
            # Use default if available, otherwise require use_case
            if "default" in prompt_template:
                prompt = prompt_template["default"]
                logging.info(f"[MCP-Tool] Using default prompt for agent '{agent_name}'")
            else:
                available_cases = ", ".join(prompt_template.keys())
                return f"Error: Agent '{agent_name}' supports multiple use cases. Please specify use_case parameter. Available use cases: {available_cases}"
        else:
            if use_case not in prompt_template:
                available_cases = ", ".join(prompt_template.keys())
                return f"Error: Use case '{use_case}' not found for agent '{agent_name}'. Available use cases: {available_cases}"
            
            prompt = prompt_template[use_case]
    else:
        # Handle simple string prompts (backward compatibility)
        if use_case:
            logging.warning(f"[MCP-Tool] Agent '{agent_name}' does not support multiple use cases, ignoring use_case parameter")
        prompt = prompt_template
    
    # Auto-format prompts that contain instructions_prefix placeholder
    if "{instructions_prefix}" in prompt:
        instructions_prefix = PROMPT_TEMPLATES.get("instructions_prefix", "")
        prompt = prompt.format(instructions_prefix=instructions_prefix)
    
    logging.info(f"[MCP-Tool] Retrieved prompt for '{agent_name}' (use_case: {use_case}), length: {len(prompt)} chars")
    return prompt

if __name__ == "__main__":
    # Run the MCP server using streamable HTTP transport
    mcp.run(transport="streamable-http")