import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from cyaudit.config import load_config
from argparse import Namespace


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
        config_file.unlink()  # Remove the original file

    if target_repo is not None:
        target_organization, target_repo = get_org_repo(target_repo)

    if org_github_token is None:
        org_github_token = personal_github_token

    # Form the repository URL
    repo_url = f"https://{org_github_token}@github.com/{target_organization}/{target_repo_name}.git"

    try:
        subprocess.run(["git", "clone", repo_url, "."], check=True)

        # Restore the config file if we saved it
        if temp_config:
            shutil.copy2(temp_config.name, config_file)
            os.unlink(temp_config.name)

            # Stage the restored file
            subprocess.run(["git", "add", "cyaudit.toml"])

        print(
            f"Successfully cloned {target_organization}/{target_repo_name} and restored cyaudit.toml"
        )

    except subprocess.CalledProcessError as e:
        print(f"Error during git operations: {str(e)}")
        # Restore cyaudit.toml in case of failure
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
