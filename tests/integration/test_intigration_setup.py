import pytest

from cyaudit.commands.setup import setup_repo
from tests.conftest import (
    AUDITORS_LIST,
    COMMIT_HASH,
    ORG,
    ORG_GITHUB_TOKEN,
    PERSONAL_GITHUB_TOKEN,
    SOURCE_GITHUB_URL,
    TARGET_REPO_NAME,
    delete_repo,
)

TEMPLATE_PROJECT_ID = 1


@pytest.fixture(scope="module")
def setup_repo_fixture(request):
    repo = setup_repo(
        SOURCE_GITHUB_URL,
        TARGET_REPO_NAME,
        ORG,
        AUDITORS_LIST,
        COMMIT_HASH,
        PERSONAL_GITHUB_TOKEN,
        org_github_token=ORG_GITHUB_TOKEN,
        template_project_id=TEMPLATE_PROJECT_ID,
        give_teams_access=["test-team"],
    )

    def cleanup():
        delete_repo(repo)

    request.addfinalizer(cleanup)
    return repo


def test_setup_repo(setup_repo_fixture):
    assert setup_repo_fixture.name == TARGET_REPO_NAME
    assert setup_repo_fixture.private is True
    assert setup_repo_fixture.organization.login == ORG
    commits = [commit.sha for commit in setup_repo_fixture.get_commits()]
    assert COMMIT_HASH in commits
    assert setup_repo_fixture.default_branch == "main"
    # TODO: Make this test more robust
