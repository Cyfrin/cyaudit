import subprocess
import sys
from argparse import Namespace
from pathlib import Path

import tomli_w
import tomllib
from github import Github

from cyaudit.config import load_config
from cyaudit.constants import REPORT_FOLDER
from cyaudit.logging import logger
from cyaudit.utils.create_report import fetch_issues, generate_markdown_from_issues

"""
This command sets up the `source` folder in the audit github repo.

To set it up to generate the report.
"""


def main(args: Namespace) -> int:
    # 2. If yes, update the files in the `source` folder
    source_command()

    # Update these:
    # severity_counts.toml
    # summary_information.toml
    return 0


def source_command():
    (
        source_url,
        target_repo_name,
        target_organization,
        _,
        commit_hash,
        personal_github_token,
        org_github_token,
        project_title,
        _,
        _,
        _,
    ) = load_config()
    swap_to_report_branch()
    check_for_report_folder()
    update_summary_information(source_url, commit_hash, project_title)
    if org_github_token is None:
        org_github_token = personal_github_token
    g = Github(org_github_token)
    github_repo = g.get_repo(target_organization + "/" + target_repo_name)
    issues_dict, summary_of_findings = fetch_issues(github_repo, g)
    generate_markdown_from_issues(issues_dict, summary_of_findings)
    # update severity count


def update_summary_information(source_url, commit_hash, project_title):
    toml_path = Path(f"./{REPORT_FOLDER}/source/summary_information.toml")
    try:
        with open(toml_path, "rb") as f:
            data = tomllib.load(f)
        data["summary"]["project_name"] = project_title
        data["summary"]["project_github"] = source_url
        data["summary"]["commit_hash"] = commit_hash
        with open(toml_path, "wb") as f:
            tomli_w.dump(data, f)
        return True
    except FileNotFoundError:
        print(f"TOML file not found at {toml_path}")
        return False
    except Exception as e:
        print(f"Error updating TOML file: {e}")
        return False


def check_for_report_folder():
    if not Path(Path.cwd() / REPORT_FOLDER).exists():
        logger.error(f"Report folder '{REPORT_FOLDER}' not found in report branch")
        sys.exit(1)
        return False
    return True


def swap_to_report_branch():
    # current_branch = subprocess.check_output(
    #     ["git", "rev-parse", "--abbrev-ref", "HEAD"], universal_newlines=True
    # ).strip()
    subprocess.check_call(["git", "checkout", "report"])
    return True
