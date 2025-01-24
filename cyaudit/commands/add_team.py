from argparse import Namespace

from github import Github

from cyaudit.config import give_access_to_users_and_teams, load_config


def main(args: Namespace) -> None:
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

    g = Github(org_github_token)
    org = g.get_organization(target_organization)
    repo = g.get_repo(target_organization + "/" + target_repo_name)
    users = []
    team_names = [args.team_name]
    give_access_to_users_and_teams(repo, org, users, team_names)
