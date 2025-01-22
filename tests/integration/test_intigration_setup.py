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


@pytest.fixture(scope="module")
def setup_repo_fixture():
    repo = setup_repo(
        SOURCE_GITHUB_URL,
        TARGET_REPO_NAME,
        ORG,
        AUDITORS_LIST,
        COMMIT_HASH,
        PERSONAL_GITHUB_TOKEN,
        ORG_GITHUB_TOKEN,
    )
    yield repo
    delete_repo(repo)


def test_setup_repo(setup_repo_fixture):
    assert setup_repo_fixture.name == TARGET_REPO_NAME
    assert setup_repo_fixture.private is True
    assert setup_repo_fixture.organization.login == ORG
    commits = [commit.sha for commit in setup_repo_fixture.get_commits()]
    assert COMMIT_HASH in commits
    assert setup_repo_fixture.default_branch == "main"
