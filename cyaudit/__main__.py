import argparse
import tomllib
from importlib import import_module, metadata
from pathlib import Path
from typing import Tuple

from cyaudit.logging import logger, set_log_level

CYAUDIT_CLI_VERSION_STRING = "CyAudit CLI v{}"


def main(argv: list) -> int:
    """Run the CyAudit CLI with the given arguments.

    Args:
        argv (list): List of arguments to run the CLI with.
    """
    if "--version" in argv or "version" in argv:
        print(get_version())
        return 0

    main_parser, sub_parsers = generate_main_parser_and_sub_parsers()

    # ------------------------------------------------------------------
    #                         PARSING STARTS
    # ------------------------------------------------------------------
    if len(argv) == 0 or (len(argv) == 1 and (argv[0] == "-h" or argv[0] == "--help")):
        main_parser.print_help()
        return 0

    args = main_parser.parse_args(argv)
    set_log_level(quiet=args.quiet, debug=args.debug)

    if args.command:
        logger.info(f"Running {args.command} command...")
        import_module(f"cyaudit.commands.{args.command}").main(args)
    else:
        main_parser.print_help()
    return 0


def generate_main_parser_and_sub_parsers() -> (
    Tuple[argparse.ArgumentParser, argparse.Action]
):
    parent_parser = create_parent_parser()
    main_parser = argparse.ArgumentParser(
        prog="CyAudit CLI",
        description="Setup, manage, and generate reports for smart contract audits.",
        formatter_class=argparse.RawTextHelpFormatter,
        parents=[parent_parser],
    )
    sub_parsers = main_parser.add_subparsers(dest="command")

    # ------------------------------------------------------------------
    #                              SETUP
    # ------------------------------------------------------------------
    setup_parser = sub_parsers.add_parser(
        "setup",
        help="Setup a new audit project",
        description="This will clone a repo and set it up in the organization that you choose.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    setup_parser.add_argument(
        "--source-url",
        "-s",
        help="The URL of the repo that was are conducting an audit on.",
        type=str,
    )
    setup_parser.add_argument(
        "--target-repo-name",
        "-t",
        help="The name of the repo that you will use for this audit.",
        type=str,
    )
    setup_parser.add_argument(
        "--auditors",
        "-a",
        help="Space-separated list of auditor names",
        nargs="+",
        type=str,
    )
    setup_parser.add_argument(
        "--target-organization",
        "-o",
        help="The organization to create the repo in.",
        type=str,
    )
    setup_parser.add_argument(
        "--commit-hash", "-c", help="The commit hash to checkout in the repo.", type=str
    )

    token_group = setup_parser.add_mutually_exclusive_group()
    token_group.add_argument(
        "--github-token", help="The GitHub token to use for authentication.", type=str
    )
    token_group.add_argument(
        "--personal-github-token",
        "-p",
        help="The personal GitHub token to use for authentication.",
        type=str,
    )
    setup_parser.add_argument(
        "--organization-github-token",
        "-g",
        help="The organization GitHub token to use for authentication.",
        type=str,
    )

    setup_parser.add_argument(
        "--project-title",
        help="The title of the project that you are auditing.",
        type=str,
    )

    # ------------------------------------------------------------------
    #                              CONFIG
    # ------------------------------------------------------------------

    return main_parser, sub_parsers


def create_parent_parser():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-d", "--debug", action="store_true", help="Run in debug mode")
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="Suppress all output except errors"
    )
    return parser


def get_version() -> str:
    version = metadata.version("cyaudit")
    # Attempt to parse from `pyproject.toml` if not found
    if not version:
        with open(
            Path(__file__).resolve().parent.parent.joinpath("pyproject.toml"), "rb"
        ) as f:
            cyaudit_cli_data = tomllib.load(f)
        version = cyaudit_cli_data["project"]["version"]
    return CYAUDIT_CLI_VERSION_STRING.format(version)
