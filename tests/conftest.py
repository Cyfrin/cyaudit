import os
from datetime import datetime

import pytest
from dotenv import load_dotenv
from github import Github
from github.Organization import Organization
from github.Repository import Repository

load_dotenv()

ORG = os.getenv("CYAUDIT_TEST_ORG")
TEAM = os.getenv("CYAUDIT_TEST_TEAM")
SOURCE_GITHUB_URL = "https://github.com/patrick-streaming/client-puppy-raffle-test"
TARGET_REPO_NAME = "audit-repo-name"
AUDITORS_LIST = ["blue-froge-mang"]
ORG_GITHUB_TOKEN = os.getenv("CYAUDIT_ORG_GITHUB_TOKEN")
PERSONAL_GITHUB_TOKEN = os.getenv("CYAUDIT_PERSONAL_GITHUB_TOKEN")
COMMIT_HASH = "069cf56ec051216ccab79b550fba5e2a188ade9c"


# ------------------------------------------------------------------
#                         HELPER FUNCTIONS
# ------------------------------------------------------------------
def get_github_client() -> Github:
    """Initialize and return a GitHub client"""
    token = os.environ.get("CYAUDIT_GITHUB_TOKEN")
    if not token:
        raise ValueError("CYAUDIT_GITHUB_TOKEN environment variable is required")
    return Github(token)


def create_test_repo(
    gh: Github, prefix: str = "test-repo", org: Organization = None
) -> Repository:
    """Create a temporary test repository"""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    repo_name = f"{prefix}-{timestamp}"

    if org:
        return org.create_repo(
            repo_name,
            private=True,
            description="Temporary repository for integration testing",
        )
    else:
        return gh.get_user().create_repo(
            repo_name,
            private=True,
            description="Temporary repository for integration testing",
        )


def delete_repo(repo: Repository) -> None:
    """Delete a test repository"""
    try:
        repo.delete()
    except Exception as e:
        print(f"Failed to delete repository {repo.name}: {e}")


def delete_org(org: Organization) -> None:
    """Delete a test organization"""
    try:
        org.delete()
    except Exception as e:
        print(f"Failed to delete organization {org.login}: {e}")


# ------------------------------------------------------------------
#                          SESSION SCOPE
# ------------------------------------------------------------------
@pytest.fixture(scope="session")
def github():
    """Fixture that provides a GitHub client"""
    return get_github_client()


@pytest.fixture(scope="session")
def org(github):
    return github.get_organization(ORG)


@pytest.fixture(scope="session")
def repo(github):
    """Fixture that provides an organization with a repository"""
    repo = create_test_repo(github, org=org)
    yield org, repo
    delete_repo(repo)


@pytest.fixture(scope="session")
def team(org):
    """Fixture that provides the  github.Team.Team object"""
    team = org.get_team_by_slug(TEAM)
    return team


# ------------------------------------------------------------------
#                          FUNCTION SCOPE
# ------------------------------------------------------------------
