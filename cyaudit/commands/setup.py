from argparse import Namespace
from typing import Tuple, List
from urllib.parse import urlparse
import tempfile
from github import Github, Repository, Organization, GithubException
import subprocess
from cyaudit.logging import logger

MAIN_BRANCH_NAME = "main"


def main(args: Namespace) -> int:
    (source_url, target_repo_name, target_organization, auditors) = prompt_for_missing(
        args
    )
    setup_repo(source_url, target_repo_name, target_organization, auditors)
    return 0


# TODO: Finish this repo, and run some integration tests on it with setup and tear down
# of git repos on a brand new test org.
def setup_repo(
    source_url: str,
    target_repo_name: str,
    target_organization: str,
    auditors: List[str],
) -> None:
    clean_url = source_url.replace(".git", "")
    parsed = urlparse(clean_url)
    path_parts = parsed.path.strip("/").split("/")
    source_username = path_parts[-2]
    source_repo_name = path_parts[-1]

    with tempfile.TemporaryDirectory() as temp_dir:
        repo = try_clone_repo(
            github_token,
            target_organization,
            target_repo_name,
            source_repo_name,
            source_username,
            temp_dir,
            commit_hash,
        )


def try_clone_repo(
    github_token: str,
    organization: str,
    target_repo_name: str,
    source_repo_name: str,
    source_username: str,
    repo_path: str,
    commit_hash: str,
) -> Repository:
    github_object = Github(github_token)
    github_org = github_object.get_organization(organization)
    repo = None
    try:
        print(f"Checking whether {target_repo_name} already exists...")
        git_command = [
            "git",
            "ls-remote",
            "-h",
            f"https://{github_token}@github.com/{organization}/{target_repo_name}",
        ]

        result = subprocess.run(
            git_command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        if result.returncode == 0:
            logger.error(f"{organization}/{target_repo_name} already exists.")
            exit()
        elif result.returncode == 128:
            repo = create_and_clone_repo(
                github_token,
                github_org,
                organization,
                target_repo_name,
                source_repo_name,
                source_username,
                repo_path,
                commit_hash,
            )
    except subprocess.CalledProcessError as e:
        if e.returncode == 128:
            repo = create_and_clone_repo(
                github_token,
                github_org,
                organization,
                target_repo_name,
                source_repo_name,
                source_username,
                repo_path,
                commit_hash,
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
    github_token: str,
    github_org: Organization,
    organization: str,
    target_repo_name: str,
    source_repo_name: str,
    source_username: str,
    repo_path: str,
    commit_hash: str,
) -> Repository:
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
                f"https://{github_token}@github.com/{source_username}/{source_repo_name}.git",
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
                f"https://{github_token}@github.com/{organization}/{target_repo_name}.git",
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


def prompt_for_missing(args: Namespace) -> Tuple[str, str, List[str]]:
    """Prompt the user for any missing arguments.

    Args:
        args (Namespace): The parsed arguments.

    Returns:
        Tuple[str, str, List[str]]: The source repository URL, target repository name, and auditors.
    """
    source_url = args.source_url
    target_repo_name = args.target_repo_name
    auditors = args.auditors

    if source_url is None:
        source_url = input("1) Source repo url:\n")

    if target_repo_name is None:
        target_repo_name = input(
            "2) Target repo name (leave blank to use source repo name):\n"
        )
        if target_repo_name == "":
            target_repo_name = None

    if auditors is None:
        auditors = input("3) Enter the names of the auditors (separated by spaces):\n")

    return source_url, target_repo_name


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--source-url", help="Source repository URL")
    parser.add_argument("--target-repo-name", help="Target repository name")
    args = parser.parse_args()
    main(args)
