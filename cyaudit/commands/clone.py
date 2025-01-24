import os
import shutil
import subprocess
import tempfile
from argparse import Namespace
from pathlib import Path

from cyaudit.config import load_config


def main(args: Namespace):
    target_repo = None
    if args.target_url is not None:
        target_repo = args.target_url
    cyaudit_clone(target_repo=target_repo)


def cyaudit_clone(target_repo: str | None = None):
    (
        _,
        target_repo_name,
        target_organization,
        _,
        _,
        personal_github_token,
        org_github_token,
        _,
        _,
        _,
        _,
    ) = load_config()

    # Save and remove the current cyaudit.toml
    cwd = Path.cwd()
    config_file = cwd / "cyaudit.toml"
    temp_config = None
    if config_file.exists():
        temp_config = tempfile.NamedTemporaryFile(delete=False)
        shutil.copy2(config_file, temp_config.name)
        config_file.unlink()

    if target_repo is not None:
        target_organization, target_repo = get_org_repo(target_repo)

    if org_github_token is None:
        org_github_token = personal_github_token

    # Save original credential helper configuration
    try:
        original_helper = subprocess.check_output(
            ["git", "config", "--global", "credential.helper"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except subprocess.CalledProcessError:
        original_helper = None

    # Form the repository URL without the token
    repo_url = f"https://github.com/{target_organization}/{target_repo_name}.git"

    try:
        # Set up git credential helper
        subprocess.run(
            ["git", "config", "--global", "credential.helper", "store"], check=True
        )

        # Store the credentials temporarily
        cred_file = Path.home() / ".git-credentials"
        with open(cred_file, "a") as f:
            f.write(f"https://oauth2:{org_github_token}@github.com\n")

        # Clone the repository
        subprocess.run(["git", "clone", repo_url, "."], check=True)

        # Remove the credentials
        if cred_file.exists():
            cred_file.unlink()

        # Restore the config file if we saved it
        if temp_config:
            shutil.copy2(temp_config.name, config_file)
            os.unlink(temp_config.name)
            subprocess.run(["git", "add", "cyaudit.toml"])

        print(
            f"Successfully cloned {target_organization}/{target_repo_name} and restored cyaudit.toml"
        )

    except subprocess.CalledProcessError as e:
        print(f"Error during git operations: {str(e)}")
        if temp_config:
            shutil.copy2(temp_config.name, config_file)
            os.unlink(temp_config.name)
        raise
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        if temp_config:
            shutil.copy2(temp_config.name, config_file)
            os.unlink(temp_config.name)
        raise
    finally:
        # Ensure credentials are cleaned up even if an error occurs
        if (Path.home() / ".git-credentials").exists():
            (Path.home() / ".git-credentials").unlink()

        # Restore original credential helper if it existed
        if original_helper is not None:
            subprocess.run(
                ["git", "config", "--global", "credential.helper", original_helper],
                check=True,
            )
        else:
            # If there was no original helper, remove the config entry
            try:
                subprocess.run(
                    ["git", "config", "--global", "--unset-all", "credential.helper"],
                    check=True,
                    stderr=subprocess.DEVNULL,
                )
            except subprocess.CalledProcessError:
                pass  # Ignore errors when unsetting


def get_org_repo(url: str) -> tuple[str, str]:
    """
    Extract organization and repository name from a GitHub URL.
    Returns tuple of (organization, repository).

    Examples:
    - https://github.com/org/repo -> (org, repo)
    - https://github.com/org/repo.git -> (org, repo)
    - git@github.com:org/repo.git -> (org, repo)
    """
    # Remove .git suffix if present
    url = url.rstrip(".git")

    # Handle SSH URLs (git@github.com:org/repo)
    if url.startswith("git@"):
        path = url.split(":", 1)[1]
    else:
        # Handle HTTPS URLs
        path = url.split("github.com/", 1)[1]

    # Split into org and repo
    org, repo = path.split("/")

    return org, repo
