from tests.conftest import create_test_repo


def test_repo_creation(test_repo):
    """Test basic repository operations"""
    assert test_repo.private is True

    # Create a file
    test_repo.create_file(
        "README.md",
        "Initial commit",
        "# Test Repository\nThis is a temporary test repository.",
    )

    contents = test_repo.get_contents("README.md")
    assert "Test Repository" in contents.decoded_content.decode()


def test_org_team_management(github, org, team):
    """Test team creation and management"""
    # Create a repo and give the team access
    repo = create_test_repo(github, org=org)
    team.add_to_repos(repo)

    # Verify team has access
    team_repos = list(team.get_repos())
    assert repo in team_repos
