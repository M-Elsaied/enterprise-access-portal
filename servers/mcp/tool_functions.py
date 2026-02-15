# servers/mcp/tool_functions.py
import json
import logging
from pathlib import Path
from typing import Any, Dict, Union

# Import prompt functions to access prompts
from prompt_templates import PROMPT_TEMPLATES

# --- IMPORTANT: Path to knowdocs from the new server location ---
# This assumes the server file is in servers/mcp/
KNOWDOCS_PATH = Path(__file__).parent.parent.parent / "coded_tools" / "enterprise_access_portal" / "tools" / "knowdocs"

def user_verification(args: Dict[str, Any], sly_data: Dict[str, Any]) -> Union[bool, str]:
    """
    Verifies a user's identity against the central users table using secure context.
    """
    user_id = sly_data.get("user_id", "").strip()
    dataiku_id = sly_data.get("dataiku_id", "").strip()
    logging.info(f"[MCP-Tool] Verifying user_id={user_id}, dataiku_id={dataiku_id}")

    file_path = KNOWDOCS_PATH / "users.md"
    # ... (The rest of the logic is identical to your original UserVerificationTool.invoke)
    try:
        lines = [line.strip() for line in file_path.read_text(encoding="utf-8").splitlines()]
        rows = [ln for ln in lines if "|" in ln][2:]
        for row in rows:
            parts = [p.strip() for p in row.strip("|").split("|")]
            if len(parts) >= 5 and parts[0] == user_id and parts[2] == dataiku_id and parts[4].upper() == "A":
                return True
        return False
    except Exception as e:
        return f"Error: {e}"

def training_requirements(args: Dict[str, Any], sly_data: Dict[str, Any]) -> Union[Dict[str, Any], str]:
    """
    Returns training requirements for a specific environment.
    :param env: The environment type (DEV, QA, PROD, CORE++).
    """
    env = str(args.get("env", "")).upper()
    logging.info("[MCP-Tool] Getting requirements for env=%s", env)
    file_path = KNOWDOCS_PATH / "training_requirements.md"
    # ... (The rest of the logic is identical to your original TrainingRequirementsTool.invoke)
    try:
        text = file_path.read_text(encoding="utf-8")
        data = json.loads(text[text.find("{"):text.rfind("}") + 1])
        return data.get(env, {})
    except Exception as e:
        return f"Error: {e}"


def training_completions(args: Dict[str, Any], sly_data: Dict[str, Any]) -> Union[bool, str]:
    """
    Checks if a user has completed a specific training using their certificate ID.
    :param training_name: The name of the training to verify.
    :param certificate_id: The user's provided certificate ID for the training.
    """
    user_id = sly_data.get("user_id", "").strip()
    training_name = str(args.get("training_name", "")).strip()
    certificate_id = str(args.get("certificate_id", "")).strip()
    logging.info(f"[MCP-Tool] Checking completion for user {user_id}, training {training_name}")

    file_path = KNOWDOCS_PATH / "training_completions.md"
    # ... (The rest of the logic is identical to your original TrainingCompletionsTool.invoke)
    try:
        lines = [line.strip() for line in file_path.read_text(encoding="utf-8").splitlines()]
        rows = [ln for ln in lines if "|" in ln][2:]
        for row in rows:
            parts = [p.strip() for p in row.strip("|").split("|")]
            if len(parts) >= 4 and parts[0] == user_id and parts[2] == training_name and parts[3] == certificate_id:
                return True
        return False
    except Exception as e:
        return f"Error: {e}"


def approvals_required(args: Dict[str, Any], sly_data: Dict[str, Any]) -> Union[bool, str]:
    """
    Checks if a requested access type is permitted for a given environment based on company policies.
    :param env: The environment type (e.g., DEV, PROD).
    :param access_type: The type of access requested (e.g., Read, Write).
    """
    env = str(args.get("env", "")).upper()
    access_type = str(args.get("access_type", "")).capitalize()
    logging.info(f"[MCP-Tool] Checking policy for env={env}, access={access_type}")
    file_path = KNOWDOCS_PATH / "access_policies.md"
    # ... (The rest of the logic is identical to your original ApprovalsRequiredTool.invoke)
    try:
        lines = [line.strip() for line in file_path.read_text(encoding="utf-8").splitlines()]
        rows = [ln for ln in lines if "|" in ln][2:]
        for row in rows:
            parts = [p.strip() for p in row.strip("|").split("|")]
            if len(parts) >= 3 and parts[0].upper() == env and parts[1].capitalize() == access_type:
                return parts[2].lower() == "yes"
        return False
    except Exception as e:
        return f"Error: {e}"

def prompt_retriever(args: Dict[str, Any], sly_data: Dict[str, Any]) -> str:
    """
    Retrieves agent instructions/prompts from the MCP server.
    This tool allows agents to dynamically fetch their instructions.
    
    :param agent_name: The name of the agent to get instructions for.
    :param use_case: The specific use case for agents that support multiple applications (optional).
    """
    agent_name = str(args.get("agent_name", "")).strip()
    use_case = str(args.get("use_case", "")).strip() if args.get("use_case") else None
    logging.info(f"[MCP-Tool] Retrieving prompt for agent: {agent_name}, use_case: {use_case}")
    
    if not agent_name:
        return "Error: agent_name parameter is required"
    
    # Map agent names to prompt templates
    agent_prompt_mapping = {
        "access_request_orchestrator_agent": "access_request_orchestrator_agent",
        "ons_agent": "ons_agent",
        "instructions_prefix": "instructions_prefix"
    }
    
    prompt_name = agent_prompt_mapping.get(agent_name)
    if not prompt_name:
        available = ", ".join(agent_prompt_mapping.keys())
        return f"Error: No prompt found for agent '{agent_name}'. Available agents: {available}"
    
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

# --- This dictionary maps the function names to the actual functions ---
AVAILABLE_MCP_TOOLS = {
    "user_verification": user_verification,
    "training_requirements": training_requirements,
    "training_completions": training_completions,
    "approvals_required": approvals_required,
    "prompt_retriever": prompt_retriever,
}