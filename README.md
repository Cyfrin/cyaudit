> ![NOTE]
> This repo is a wooorrkkkkk in progress.

# cyaudit

A tool to help you setup a repo for audit. 

```console
usage: CyAudit CLI [-h] [-d] [-q] {setup,source,report,add-team,clone,init} ...

Setup, manage, and generate reports for smart contract audits.

positional arguments:
  {setup,source,report,add-team,clone,init}
    setup               Setup a new audit project
    source              Edit the source folder for report generation
    report              Generate the report.
    add-team            Add a team.
    clone               Clones an audit repo already setup.
    init                Create a cyaudit.toml config file.

options:
  -h, --help            show this help message and exit
  -d, --debug           Run in debug mode
  -q, --quiet           Suppress all output except errors
```

# Quickstart - tutorial

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/)
2. Install `cyaudit`

```bash
uv tool install cyaudit
```

3. Create a new audit project

```bash
mkdir my-audit
cd my-audit
cyaudit init
```

This will create a `cyaudit.toml` file in your current directory. Fill out the form, (if you don't the CLI will prompt you in the next step). Here is an example `cyaudit.toml` file:

```toml
[cyaudit]
template_project_id = "5" # The template project id
source_url = "https://github.com/Cyfrin/4-puppy-raffle-audit"
target_repo_name = "audit-puppy-raffle"
target_organization = "cyfrin"
auditors = [
    "patrick",
]
commit_hash = "15c50ec22382bb1f3106aba660e7c590df18dcac"
project_title = "puppy raffle"
give_users_access = "" # This is the list of users that will be given access to the repo
give_teams_access = [
    "Auditors",
] # This is the list of teams that will be given access to the repo
```

4. Setup your [github access tokens](#github-token-permissions)

Ideally, you use two fine grained tokens. Set the `CYAUDIT_PERSONAL_GITHUB_TOKEN` and `CYAUDIT_ORG_GITHUB_TOKEN` environment variables. You may also wait for the CLI to prompt you in the next step.

5. Run the setup command

This will:

- Create a new repo at the `target_organization` with the `target_repo_name`
- Add the issue template
- Replace labels
- Create branches for auditors
- Create the report branch
- Add report branch data
- Setup CI
- Add teams

```bash
cyaudit setup
```

6. Clone the repo

```bash
cyaudit clone
```

This will keep your `cyaudit.toml` in tact. 

7. Do your audit

Go to the github, and make an issue!

8. Generate the source files

```console
cyaudit source
```

9. Edit `summary_information.toml` 

```toml
[summary]
project_name = "my project"
report_version = 1.0
team_name = "my_team"
team_website = "hi.com"
client_name = "asdfsa"
client_website = "asdfas"
private_github = "https://github.com/cyfrin/my-goose.git"
project_github = "https://github.com/Cyfrin/4-puppy-raffle-audit"
commit_hash = "15c50ec22382bb1f3106aba660e7c590df18dcac"
fix_commit_hash = ""
project_github_2 = ""
commit_hash_2 = ""
fix_commit_hash_2 = ""
project_github_3 = ""
commit_hash_3 = ""
fix_commit_hash_3 = ""
review_timeline = "01-01-2021 - 01-02-2021"
review_methods = ""
```

10. Generate the report

```console
cyaudit report
```

# Global config

You can setup a file at:

```console
~/.cyaudit/global_cyaudit.toml
```

And when you run `cyaudit init` it will use the global config as a default.

# GitHub Token Permissions

Ideally, you use 2 fine grained tokens, one for your personal and one for the org.

Use `CYAUDIT_PERSONAL_GITHUB_TOKEN` and `CYAUDIT_ORG_GITHUB_TOKEN` environment variables to set your tokens. If you use a classic token, you can just use `CYAUDIT_PERSONAL_GITHUB_TOKEN`.

## Personal Access Token

(I'm not 100% sure)

Permissions:
- Actions
- Administration
- Commit statuses
- Contents
- Workflows

## Org token 

(I'm not 100% sure)

Permissions:
- Actions
- Administration
- Contents
- Workflows
- Issue Types
- Projects
- Members

## Classic Tokens

Classic tokens give too much power, so it's better to use the fine grained tokens.