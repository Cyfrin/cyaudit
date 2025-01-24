import os
from pathlib import Path
import tomllib
from typing import Tuple


def load_config() -> Tuple[str, str, str, list[str], str, str, str, str, str]:
    """
    Load configuration from cyaudit.toml file and substitute environment variables.
    Uses default empty values for missing fields.

    Returns:
        Tuple containing:
            source_url (str): URL of the source repository
            target_repo_name (str): Name of the target repository
            target_organization (str): Name of the target organization
            auditors (list[str]): List of auditor GitHub usernames
            commit_hash (str): Commit hash to audit
            personal_github_token (str): Personal GitHub token
            org_github_token (str): Organization GitHub token
            project_title (str): Title of the project
            template_project_id (str): Template project ID

    Raises:
        FileNotFoundError: If cyaudit.toml doesn't exist
        ValueError: If environment variable substitution fails
    """
    config_path = Path("cyaudit.toml")
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, "rb") as f:
        config = tomllib.load(f)

    def substitute_env_vars(value: str) -> str:
        """Replace $VAR or ${VAR} with environment variable values."""
        if not isinstance(value, str):
            return value

        if value.startswith("$"):
            # Handle both $VAR and ${VAR} formats
            env_var = value[1:] if not value.startswith("${") else value[2:-1]
            if env_var not in os.environ:
                raise ValueError(f"Environment variable not found: {env_var}")
            return os.environ[env_var]
        if value == "":
            return None
        return value

    cyaudit_config = config.get("cyaudit", {})

    # Extract and process each value with defaults
    source_url = substitute_env_vars(cyaudit_config.get("source_url", None))
    target_repo_name = substitute_env_vars(cyaudit_config.get("target_repo_name", None))
    target_organization = substitute_env_vars(
        cyaudit_config.get("target_organization", None)
    )
    auditors = [substitute_env_vars(a) for a in cyaudit_config.get("auditors", None)]
    commit_hash = substitute_env_vars(cyaudit_config.get("commit_hash", None))
    personal_github_token = os.getenv("CYAUDIT_PERSONAL_GITHUB_TOKEN")
    org_github_token = os.getenv("CYAUDIT_ORG_GITHUB_TOKEN")
    project_title = substitute_env_vars(cyaudit_config.get("project_title", None))
    template_project_id = substitute_env_vars(
        cyaudit_config.get("template_project_id", None)
    )
    give_users_access = substitute_env_vars(
        cyaudit_config.get("give_users_access", None)
    )
    give_teams_access = substitute_env_vars(
        cyaudit_config.get("give_teams_access", None)
    )

    return (
        source_url,
        target_repo_name,
        target_organization,
        auditors,
        commit_hash,
        personal_github_token,
        org_github_token,
        project_title,
        template_project_id,
        give_users_access,
        give_teams_access,
    )
