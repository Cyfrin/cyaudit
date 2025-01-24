import os
import shutil
import subprocess
import tempfile
from argparse import Namespace
from datetime import date
from getpass import getpass
from importlib import resources
from pathlib import Path
from typing import List, Tuple
from urllib.parse import urlparse

import tomli_w
import tomllib
from github import Github, GithubException, Organization, Repository

from cyaudit.config import give_access_to_users_and_teams, load_config
from cyaudit.constants import (
    DEFAULT_LABELS,
    GITHUB_WORKFLOW_ACTION_NAME,
    ISSUE_TEMPLATE,
    MAIN_BRANCH_NAME,
    REPORT_BRANCH_NAME,
    REPORT_FOLDER,
    SEVERITY_DATA,
    TEMPLATE_PROJECT_ID,
)
from cyaudit.create_action import create_action
from cyaudit.github_project_utils import clone_project
from cyaudit.logging import logger


def main(args: Namespace) -> int:
    (
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
    ) = load_config()

    if args.source_url is not None:
        source_url = args.source_url
    if args.target_repo_name is not None:
        target_repo_name = args.target_repo_name
    if args.target_organization is not None:
        target_organization = args.target_organization
    if args.auditors is not None:
        auditors = args.auditors
    if args.commit_hash is not None:
        commit_hash = args.commit_hash
    if args.project_title is not None:
        project_title = args.project_title
    if args.github_token is not None:
        personal_github_token = args.github_token
    if args.organization_github_token is not None:
        org_github_token = args.organization_github_token
    if args.template_project_id is not None:
        template_project_id = args.template_project_id
    if args.give_users_access is not None:
        give_users_access = args.give_users_access
    if args.give_teams_access is not None:
        give_teams_access = args.give_teams_access

    (
        source_url,
        target_repo_name,
        target_organization,
        auditors,
        commit_hash,
        personal_github_token,
        org_github_token,
        project_title,
        template_project_id,
    ) = prompt_for_missing(
        source_url,
        target_repo_name,
        target_organization,
        auditors,
        commit_hash,
        project_title,
        personal_github_token,
        org_github_token,
        template_project_id,
    )
    setup_repo(
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
    return 0


def setup_repo(
    source_url: str,
    target_repo_name: str,
    target_organization: str,
    auditors: List[str],
    commit_hash: str,
    personal_github_token: str,
    org_github_token: str | None = None,
    project_title: str = "DEFAULT PROJECT",
    template_project_id: str = TEMPLATE_PROJECT_ID,
    give_users_access: List[str] | None = None,
    give_teams_access: List[str] | None = None,
) -> None:
    missing_params = []

    if not source_url:
        missing_params.append("source_url")
    if not auditors:
        missing_params.append("auditors")
    if not target_organization:
        missing_params.append("target_organization")

    if missing_params:
        raise ValueError(f"Missing required parameters: {', '.join(missing_params)}")

    if not personal_github_token:
        personal_github_token = os.getenv("CYAUDIT_PERSONAL_GITHUB_TOKEN")
        raise ValueError(
            "At least a classic GitHub token is required, but ideally two fine-grained tokens. Please provide it through:\n"
            "- Environment variable CYAUDIT_PERSONAL_GITHUB_TOKEN"
        )

    clean_url = source_url.replace(".git", "")
    parsed = urlparse(clean_url)
    path_parts = parsed.path.strip("/").split("/")
    source_username = path_parts[-2]
    source_repo_name = path_parts[-1]

    repo = None

    with tempfile.TemporaryDirectory() as temp_dir:
        repo = try_clone_repo(
            target_organization,
            target_repo_name,
            source_repo_name,
            source_username,
            temp_dir,
            commit_hash,
            personal_github_token,
            org_github_token,
        )
        repo = create_audit_tag(repo, temp_dir, commit_hash)
        repo = add_issue_template_to_repo(repo)
        repo = replace_labels_in_repo(repo)
        repo = create_branches_for_auditors(repo, auditors, commit_hash)
        repo = create_report_branch(repo, commit_hash)
        repo = add_report_branch_data(
            repo,
            source_repo_name,
            target_repo_name,
            source_username,
            target_organization,
            temp_dir,
            commit_hash,
        )

        org_repo = get_org_repo(repo, org_github_token)

        repo = set_up_ci(org_repo, temp_dir)
        set_up_project_board(
            org_repo,
            org_github_token,
            target_organization,
            target_repo_name,
            template_project_id,
            project_title,
        )

        org_github_object = Github(org_github_token)
        g_org = org_github_object.get_organization(target_organization)

        give_access_to_users_and_teams(
            org_repo, g_org, give_users_access, give_teams_access
        )

    return repo


def get_org_repo(repo: Repository, org_token: str):
    g = Github(org_token)
    return g.get_repo(repo.full_name)


# IMPORTANT: project creation via REST API is not supported anymore
# https://stackoverflow.com/questions/73268885/unable-to-create-project-in-repository-or-organisation-using-github-rest-api
# we use a non-standard way to access GitHub's GraphQL
def set_up_project_board(
    repo: Repository,
    org_github_token: str,
    organization: str,
    target_repo_name: str,
    template_project_id: str,
    project_title: str = "DEFAULT PROJECT",
):
    logger.info("Setting up project board...")
    if not project_title:
        project_title = "DEFAULT PROJECT"
    try:
        clone_project(
            repo,
            org_github_token,
            organization,
            target_repo_name,
            template_project_id,
            project_title,
        )
        print("Project board has been set up successfully!")
    except Exception as e:
        print(f"Error occurred while setting up project board: {str(e)}")
        print("Please set up project board manually.")
    return


def set_up_ci(repo: Repository, dir: str) -> Repository:
    logger.info("Setting up CI...")
    try:
        create_action(
            repo,
            GITHUB_WORKFLOW_ACTION_NAME,
            dir,
            REPORT_BRANCH_NAME,
            str(date.today()),
        )
    except Exception as e:
        logger.warning(f"Error occurred while setting up CI: {str(e)}")
        logger.warning(
            "Please set up CI manually using the report-generation.yml file."
        )
    return repo


def add_report_branch_data(
    repo: Repository,
    source_repo_name: str,
    target_repo_name: str,
    source_username: str,
    organization: str,
    repo_path: str,
    commit_hash: str,
):
    try:
        # Create the branch
        subprocess.run(
            f"git -C {repo_path} pull origin {REPORT_BRANCH_NAME} --rebase",
            shell=True,
            check=False,
        )
        subprocess.run(
            f"git -C {repo_path} checkout {REPORT_BRANCH_NAME}", shell=True, check=False
        )

        copy_template_folder_to(repo_path + "/" + REPORT_FOLDER)

        # I don't think we need this?
        # # Move workflow file to the correct location
        # os.makedirs(f"{repo_path}/.github/workflows", exist_ok=True)
        # try:
        #     source = os.path.join(
        #         repo_path, REPORT_FOLDER, ".github", "workflows", "main.yml"
        #     )
        #     destination = os.path.join(repo_path, ".github", "workflows", "main.yml")
        #     shutil.move(source, destination)
        # except Exception as e:
        #     print(f"Error moving file: {e}")

        update_summary_toml(
            repo_path,
            source_username,
            source_repo_name,
            organization,
            target_repo_name,
            commit_hash,
        )

        subprocess.run(f"git -C {repo_path} add .", shell=True)
        subprocess.run(
            f"git -C {repo_path}  commit -m 'install: {REPORT_FOLDER}'",
            shell=True,
            check=False,
        )

        # Push the changes back to the origin
        subprocess.run(
            f"git -C {repo_path} push origin {REPORT_BRANCH_NAME}",
            shell=True,
            check=False,
        )

        print(
            f"The {REPORT_FOLDER} has been added to {repo.name} on branch {REPORT_BRANCH_NAME}"
        )

    except GithubException as e:
        logger.error(f"Error adding subtree: {e}")
        repo.delete()
        exit()

    return repo


def update_summary_toml(
    repo_path: str,
    source_username: str,
    source_repo_name: str,
    organization: str,
    target_repo_name: str,
    commit_hash: str,
) -> None:
    toml_path = f"{repo_path}/{REPORT_FOLDER}/source/summary_information.toml"

    # Read the TOML file
    with open(toml_path, "rb") as f:  # Note: tomllib requires binary mode
        summary_data = tomllib.load(f)

    # Update the required fields
    summary_data["summary"]["project_github"] = (
        f"https://github.com/{source_username}/{source_repo_name}.git"
    )
    summary_data["summary"]["private_github"] = (
        f"https://github.com/{organization}/{target_repo_name}.git"
    )
    summary_data["summary"]["commit_hash"] = commit_hash

    # Write back to the file
    with open(toml_path, "wb") as f:  # Note: tomli_w requires binary mode
        tomli_w.dump(summary_data, f)


def copy_template_folder_to(destination_folder: str):
    try:
        pkg_path = resources.files("cyaudit")
        template_path = pkg_path / "report_template"
        dest = Path(destination_folder)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(template_path, dest, dirs_exist_ok=True)

    except Exception as e:
        print(f"Error copying template folder: {e}")


def create_report_branch(repo, commit_hash) -> Repository:
    logger.info("Creating report branch...")
    try:
        repo.create_git_ref(ref=f"refs/heads/{REPORT_BRANCH_NAME}", sha=commit_hash)
    except GithubException as e:
        if e.status == 422:
            logger.warning(f"Branch {REPORT_BRANCH_NAME} already exists. Skipping...")
        else:
            logger.error(f"Error creating branch: {e}")
            repo.delete()
            exit()
    return repo


def create_branches_for_auditors(repo, auditors_list, commit_hash) -> Repository:
    logger.info("Creating auditor branches...")
    for auditor in auditors_list:
        branch_name = f"audit/{auditor}"
        try:
            repo.create_git_ref(f"refs/heads/{branch_name}", commit_hash)
        except GithubException as e:
            if e.status == 422:
                logger.warning(f"Branch {branch_name} already exists. Skipping...")
                continue
            else:
                logger.error(f"Error creating branch: {e}")
                repo.delete()
                exit()
    return repo


def replace_labels_in_repo(repo) -> Repository:
    logger.info("Replacing labels...")
    repo = delete_default_labels(repo)
    repo = create_new_labels(repo)
    return repo


def create_new_labels(repo) -> Repository:
    logger.info("Creating new labels...")
    for data in SEVERITY_DATA:
        try:
            repo.create_label(**data)
        except Exception:
            logger.warning(f"Issue creating label with data: {data}. Skipping...")
    print("Finished creating new labels")
    return repo


def delete_default_labels(repo) -> Repository:
    logger.info("Deleting default labels...")
    for label_name in DEFAULT_LABELS:
        try:
            label = repo.get_label(label_name)
            logger.info(f"Deleting {label}...")
            label.delete()
        except Exception:
            logger.warn(f"Label {label} does not exist. Skipping...")
    logger.info("Finished deleting default labels")
    return repo


def create_audit_tag(repo, repo_path, commit_hash) -> Repository:
    logger.info("Creating audit tag...")

    try:
        tag = repo.create_git_tag(
            tag="cyfrin-audit",
            message="Cyfrin audit tag",
            object=commit_hash,
            type="commit",
        )

        # Now create a reference to this tag in the repository
        repo.create_git_ref(ref=f"refs/tags/{tag.tag}", sha=tag.sha)
    except GithubException as e:
        logger.error(f"Error creating audit tag: {e}")
        logger.info("Attempting to create tag manually...")

        try:
            # Create the tag at the specific commit hash
            subprocess.run(["git", "-C", repo_path, "tag", "cyfrin-audit", commit_hash])

            # Push the tag to the remote repository
            subprocess.run(["git", "-C", repo_path, "push", "origin", "cyfrin-audit"])
        except GithubException as e:
            logger.error(f"Error creating audit tag manually: {e}")
            repo.delete()
            exit()
    return repo


def try_clone_repo(
    target_organization: str,
    target_repo_name: str,
    source_repo_name: str,
    source_username: str,
    repo_path: str,
    commit_hash: str,
    personal_github_token: str,
    org_github_token: str | None = None,
) -> Repository:
    if org_github_token is None:
        org_github_token = personal_github_token
    org_github_object = Github(org_github_token)
    github_org = org_github_object.get_organization(target_organization)
    repo = None
    try:
        print(f"Checking whether {target_repo_name} already exists...")
        git_command = [
            "git",
            "ls-remote",
            "-h",
            f"https://{org_github_token}@github.com/{target_organization}/{target_repo_name}",
        ]

        result = subprocess.run(
            git_command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        if result.returncode == 0:
            logger.error(f"{target_organization}/{target_repo_name} already exists.")
            exit()
        elif result.returncode == 128:
            repo = create_and_clone_repo(
                github_org,
                target_organization,
                target_repo_name,
                source_repo_name,
                source_username,
                repo_path,
                commit_hash,
                personal_github_token,
                org_github_token=org_github_token,
            )
    except subprocess.CalledProcessError as e:
        if e.returncode == 128:
            repo = create_and_clone_repo(
                github_org,
                target_organization,
                target_repo_name,
                source_repo_name,
                source_username,
                repo_path,
                commit_hash,
                personal_github_token,
                org_github_token=org_github_token,
            )
        else:
            # Handle other errors or exceptions as needed
            logger.error(f"Error checking if repository exists: {e}")
            exit()

    if repo is None:
        logger.error("Error creating repo.")
        exit()
    return repo


def create_and_clone_repo(
    github_org: Organization,
    organization: str,
    target_repo_name: str,
    source_repo_name: str,
    source_username: str,
    repo_path: str,
    commit_hash: str,
    personal_github_token: str,
    org_github_token: str | None = None,
) -> Repository:
    if org_github_token is None:
        org_github_token = personal_github_token
    try:
        repo = github_org.create_repo(target_repo_name, private=True)
    except GithubException as e:
        logger.error(f"Error creating remote repository: {e}")
        exit()

    try:
        print(f"Cloning {source_repo_name}...")
        subprocess.run(
            [
                "git",
                "clone",
                f"https://{personal_github_token}@github.com/{source_username}/{source_repo_name}.git",
                repo_path,
            ],
            check=False,
        )

    except GithubException as e:
        logger.error(f"Error cloning repository: {e}")
        repo.delete()
        exit()

    try:
        subprocess.run(["git", "-C", repo_path, "fetch", "origin"], check=False)

        # Identify the branch containing the commit using `git branch --contains`
        completed_process = subprocess.run(
            ["git", "-C", repo_path, "branch", "-r", "--contains", commit_hash],
            text=True,
            capture_output=True,
            check=True,
        )

        filtered_branches = [
            b
            for b in completed_process.stdout.strip().split("\n")
            if "origin/HEAD ->" not in b
        ]
        branches = [b.split("/", 1)[1] for b in filtered_branches]

        if not branches:
            raise Exception(f"Commit {commit_hash} not found in any branch")

        if len(branches) > 1:
            # Prompt the user to choose the branch
            print("The commit is found on multiple branches:")
            for i, branch in enumerate(branches):
                print(f"{i+1}. {branch}")

            while True:
                try:
                    branch_index = int(
                        input("Enter the number of the branch to create the tag: ")
                    )
                    if branch_index < 1 or branch_index > len(branches):
                        raise ValueError("Invalid branch index")
                    branch = branches[branch_index - 1]
                    break
                except ValueError:
                    print("Invalid branch index. Please enter a valid index.")
        else:
            branch = branches[0]

        # Fetch the branch containing the commit hash
        subprocess.run(
            [
                "git",
                "-C",
                repo_path,
                "fetch",
                "origin",
                branch + ":refs/remotes/origin/" + branch,
            ],
            check=False,
        )

        # Checkout the branch containing the commit hash
        subprocess.run(["git", "-C", repo_path, "checkout", branch], check=False)

        # Update the origin remote
        subprocess.run(
            [
                "git",
                "-C",
                repo_path,
                "remote",
                "set-url",
                "origin",
                f"https://{org_github_token}@github.com/{organization}/{target_repo_name}.git",
            ],
            check=False,
        )

        # Push the branch to the remote audit repository as 'main'
        # subprocess.run(f"git -C {repo_path} push -u origin {branch}:{MAIN_BRANCH_NAME}")
        subprocess.run(
            [
                "git",
                "-C",
                repo_path,
                "push",
                "-u",
                "origin",
                f"{branch}:{MAIN_BRANCH_NAME}",
            ],
            check=False,
        )

    except Exception as e:
        logger.error(f"Error extracting branch of commit hash: {e}")
        repo.delete()
        exit()

    return repo


def prompt_for_missing(
    source_url,
    target_repo_name,
    target_organization,
    auditors,
    commit_hash,
    project_title,
    personal_github_token,
    org_github_token,
    template_project_id,
) -> Tuple[str, str, str, List[str], str, str]:
    """Prompt the user for any missing arguments.

    Args:
        args (Namespace): The parsed arguments.

    Returns:
        Tuple: A tuple containing the source URL, target repo name, target organization, auditors, and commit hash.
    """
    if not personal_github_token:
        personal_github_token = os.getenv("CYAUDIT_PERSONAL_GITHUB_TOKEN")

    if not org_github_token:
        org_github_token = os.getenv("CYAUDIT_ORG_GITHUB_TOKEN")

    prompt_counter = 1

    if not project_title:
        project_title = input(f"{prompt_counter}) Project title:\n")
        prompt_counter += 1

    if source_url is None:
        source_url = input(f"{prompt_counter}) Source repo url:\n")
        prompt_counter += 1

    if target_repo_name is None:
        target_repo_name = input(
            f"{prompt_counter})) Target repo name (leave blank to use source repo name):\n"
        )
        if target_repo_name == "":
            target_repo_name = None
        prompt_counter += 1

    if target_organization is None:
        target_organization = input(f"{prompt_counter})) Target organization:\n")
        prompt_counter += 1

    if auditors is None or len(auditors) == 0:
        auditors = input(
            f"{prompt_counter})) Enter the names of the auditors (separated by spaces):\n"
        )
        prompt_counter += 1

    if commit_hash is None:
        commit_hash = input(f"{prompt_counter})) Enter the commit hash to audit:\n")
        prompt_counter += 1

    if personal_github_token is None:
        personal_github_token = getpass(
            f"{prompt_counter})) Enter your Personal GitHub token: "
        )
        prompt_counter += 1

    if org_github_token is None:
        org_github_token = getpass(
            f"{prompt_counter})) Enter your Organization GitHub token (or, leave blank to use your personal GitHub token): "
        )
        prompt_counter += 1

    org_github_token = (
        org_github_token
        if (org_github_token != "" and org_github_token is not None)
        else personal_github_token
    )

    if template_project_id is None:
        template_project_id = input(
            f"{prompt_counter})) Enter the ID of the project template to use:\n"
        )
        prompt_counter += 1

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
    )


def add_issue_template_to_repo(repo) -> Repository:
    # Get the existing finding.md file, if it exists
    try:
        finding_file = repo.get_contents(".github/ISSUE_TEMPLATE/finding.md")
    except GithubException:
        finding_file = None

    # If finding.md already exists, leave it be. Otherwise, create the file.
    if finding_file is None:
        repo.create_file(
            ".github/ISSUE_TEMPLATE/finding.md", "finding.md", ISSUE_TEMPLATE
        )
    return repo


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--source-url", help="Source repository URL")
    parser.add_argument("--target-repo-name", help="Target repository name")
    args = parser.parse_args()
    main(args)
