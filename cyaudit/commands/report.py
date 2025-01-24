import os
import re
import shutil
import subprocess
from argparse import Namespace
from importlib.resources import files
from pathlib import Path

from cyaudit.logging import logger
from cyaudit.utils.create_report import (
    OUTPUT_PATH,
    SOURCE_PATH,
    SOURCE_REPORT,
    TEMPLATE_PATH,
    WORKING_PATH,
    calculate_period,
    edit_report_md,
    get_file_contents,
    get_severity_counts,
    get_summary_information,
    lint,
    replace_in_file_content,
    save_file_contents,
)

# TODO
# Tackle https://github.com/Cyfrin/report-generator-template/blob/63946de5f48dbed602bb054876f7384da917a421/scripts/convert.sh
# We have the generate_report function call a bunch of these bash scripts, we need to include them in the python package
# Maybe we just add the bash scripts into the `source` folder?


def main(args: Namespace) -> int:
    generate_report()
    return 0


def run_pandoc_conversion(source_dir: Path, working_dir: Path):
    """Run pandoc conversion for markdown files"""
    files_to_convert = [
        "lead_auditors.md",
        "assisting_auditors.md",
        "about_cyfrin.md",
        "disclaimer.md",
        "protocol_summary.md",
        "audit_scope.md",
        "executive_summary.md",
        "report.md",
        "additional_comments.md",
        "appendix.md",
    ]

    minted_script = files("cyaudit") / "utils" / "pandoc-minted.py"
    image_script = files("cyaudit") / "utils" / "pandoc-image.py"

    for md_file in files_to_convert:
        logger.info(f"Converting {md_file} to LaTeX")
        input_path = source_dir / md_file
        output_path = working_dir / md_file.replace(".md", ".tex")
        if input_path.exists():
            subprocess.run(
                [
                    "pandoc",
                    "--filter",
                    f"{minted_script}",
                    "--filter",
                    f"{image_script}",
                    "--from",
                    "gfm",
                    str(input_path),
                    "-o",
                    str(output_path),
                ],
                check=True,
            )


def generate_report():
    # Get static info from conf files
    summary_data = get_summary_information()
    severity_count_data = get_severity_counts()

    # Project name taken from summary_information.conf, inserted in Title section -> title.tex file
    REPLACE_TITLE = [
        ["__PLACEHOLDER__PROJECT_NAME", summary_data["project_name"]],
        ["__PLACEHOLDER__REPORT_VERSION", summary_data["report_version"]],
    ]

    pattern = r"/(?P<org_name>[^/]+)/([^/]+?)(?=/(?:src|branch)|\.git|$)"
    source_org, source_repo_name = re.search(
        pattern, summary_data["project_github"]
    ).groups()
    if summary_data["project_github_2"]:
        _, source_repo_name_2 = re.search(
            pattern, summary_data["project_github_2"]
        ).groups()
    else:
        source_repo_name_2 = ""

    if summary_data["project_github_3"]:
        _, source_repo_name_3 = re.search(
            pattern, summary_data["project_github_3"]
        ).groups()
    else:
        source_repo_name_3 = ""

    internal_org, internal_repo_name = re.search(
        pattern, summary_data["private_github"]
    ).groups()

    # Information from summary_information.conf, inserted in Summary section -> summary.tex file
    REPLACE_SUMMARY = [
        [
            "__PLACEHOLDER__REVIEW_LENGTH",
            str(calculate_period(summary_data["review_timeline"])),
        ],
        ["__PLACEHOLDER__TEAM_NAME", summary_data["team_name"]],
        ["__PLACEHOLDER__TEAM_WEBSITE", summary_data["team_website"]],
        ["__PLACEHOLDER__PROJECT_NAME", summary_data["project_name"]],
        ["__PLACEHOLDER__REPO_LINK_3", summary_data["project_github_3"]],
        ["__PLACEHOLDER__REPO_NAME_3", source_repo_name_3],
        [
            "__PLACEHOLDER__COMMIT_HASH_3_LINK",
            re.sub(r"(\.git)?$", "", summary_data["project_github_3"])
            + "/blob/"
            + summary_data["commit_hash_3"],
        ],
        ["__PLACEHOLDER__COMMIT_HASH_3", summary_data["commit_hash_3"]],
        ["__PLACEHOLDER__REPO_LINK_2", summary_data["project_github_2"]],
        ["__PLACEHOLDER__REPO_NAME_2", source_repo_name_2],
        [
            "__PLACEHOLDER__COMMIT_HASH_2_LINK",
            re.sub(r"(\.git)?$", "", summary_data["project_github_2"])
            + "/blob/"
            + summary_data["commit_hash_2"],
        ],
        ["__PLACEHOLDER__COMMIT_HASH_2", summary_data["commit_hash_2"]],
        ["__PLACEHOLDER__REPO_LINK", summary_data["project_github"]],
        ["__PLACEHOLDER__REPO_NAME", source_repo_name],
        [
            "__PLACEHOLDER__COMMIT_HASH_LINK",
            re.sub(r"(\.git)?$", "", summary_data["project_github"])
            + "/blob/"
            + summary_data["commit_hash"],
        ],
        ["__PLACEHOLDER__COMMIT_HASH", summary_data["commit_hash"]],
        [
            "__PLACEHOLDER__FIX_COMMIT_HASH_LINK",
            re.sub(r"(\.git)?$", "", summary_data["project_github"])
            + "/blob/"
            + summary_data["fix_commit_hash"]
            if summary_data["fix_commit_hash"]
            else "",
        ],
        ["__PLACEHOLDER__FIX_COMMIT_HASH", summary_data["fix_commit_hash"] or ""],
        [
            "__PLACEHOLDER__FIX_COMMIT_HASH_LINK_2",
            re.sub(r"(\.git)?$", "", summary_data["project_github_2"])
            + "/blob/"
            + summary_data["fix_commit_hash_2"]
            if summary_data["fix_commit_hash_2"]
            else "",
        ],
        ["__PLACEHOLDER__FIX_COMMIT_HASH_2", summary_data["fix_commit_hash_2"] or ""],
        [
            "__PLACEHOLDER__FIX_COMMIT_HASH_LINK_3",
            re.sub(r"(\.git)?$", "", summary_data["project_github_3"])
            + "/blob/"
            + summary_data["fix_commit_hash_3"]
            if summary_data["fix_commit_hash_3"]
            else "",
        ],
        ["__PLACEHOLDER__FIX_COMMIT_HASH_3", summary_data["fix_commit_hash_3"] or ""],
        ["__PLACEHOLDER__AUDIT_TIMELINE", summary_data["review_timeline"]],
        ["__PLACEHOLDER__AUDIT_METHODS", summary_data["review_methods"]],
    ]

    # Severities count taken from severity_count.conf, inserted in Total Issues section -> summary.tex file
    REPLACE_SEVERITIES = [
        ["__PLACEHOLDER__ISSUE_CRITICAL_COUNT", severity_count_data["critical"]],
        ["__PLACEHOLDER__ISSUE_HIGH_COUNT", severity_count_data["high"]],
        ["__PLACEHOLDER__ISSUE_MEDIUM_COUNT", severity_count_data["medium"]],
        ["__PLACEHOLDER__ISSUE_LOW_COUNT", severity_count_data["low"]],
        [
            "__PLACEHOLDER__ISSUE_INFORMATIONAL_COUNT",
            severity_count_data["informational"],
        ],
        [
            "__PLACEHOLDER__ISSUE_GAS_OPTIMIZATION_COUNT",
            severity_count_data["gas_optimization"],
        ],
        ["__PLACEHOLDER__ISSUE_TOTAL_COUNT", severity_count_data["total"]],
    ]

    # Lint the report.md
    print("Linting the report.md file ...")
    report = get_file_contents(SOURCE_REPORT)
    report = lint(
        report,
        summary_data["team_name"],
        source_org,
        source_repo_name,
        internal_org,
        internal_repo_name,
    )
    save_file_contents(SOURCE_REPORT, report)
    print("Done.\n")

    # Convert all .md to .tex and save to working dir
    print("Converting Markdown files to LaTeX ...")
    run_pandoc_conversion(
        Path.cwd() / Path(SOURCE_PATH), Path.cwd() / Path(WORKING_PATH)
    )
    process_tex_file(WORKING_PATH + "/report.tex")
    code_listings()
    print("Done.\n")

    # Process for title.tex: Get the file and replace placeholders.
    print("Replacing information in title.tex ...")
    title = get_file_contents(Path.cwd() / TEMPLATE_PATH / "title.tex")
    title = replace_in_file_content(title, REPLACE_TITLE)
    save_file_contents(Path.cwd() / WORKING_PATH / "title.tex", title)
    print("Done.\n")

    # Process for summary.tex: Get the file and replace placeholders.
    print("Replacing information in summary.tex ...")
    summary = get_file_contents(Path.cwd() / TEMPLATE_PATH / "summary.tex")
    summary = replace_in_file_content(summary, REPLACE_SUMMARY)
    summary = replace_in_file_content(summary, REPLACE_SEVERITIES)
    save_file_contents(Path.cwd() / WORKING_PATH / "summary.tex", summary)
    print("Done.\n")

    print("Copying over other files...")
    files_to_copy = [
        "main.tex",
        "risk_classification.tex",
        "post_report.tex",
        "pre_report.tex",
        "risk_classification.tex",
    ]
    for file in files_to_copy:
        src = Path.cwd() / TEMPLATE_PATH / file
        dst = Path.cwd() / WORKING_PATH / file
        if src.exists():
            shutil.copy2(src, dst)
        else:
            print(f"Warning: Source file {src} not found")

    src_dir = Path.cwd() / TEMPLATE_PATH / "img"
    dst_dir = Path.cwd() / WORKING_PATH / "img"
    if src_dir.exists():
        shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)

    print("Done.\n")

    # Generate PDF in output folder
    print("Generating report PDF file ...")
    compile_latex_report()
    # Edit the report markdown for Solodit, after everything else is complete
    edit_report_md()
    print("\nAll tasks completed. Report should be in the 'output' folder.")
    print("\nIf not, please check texput.log for errors.")


def process_tex_file(filepath: str = "./working/report.tex") -> None:
    """
    Process a TEX file to perform various text replacements.

    Args:
        filepath (str): Path to the TEX file to process. Defaults to "./working/report.tex"
    """
    try:
        # Read the content of the file
        with open(filepath, "r", encoding="utf-8") as file:
            content = file.read()

        # Perform all the replacements
        replacements = [
            ("textbackslash clearpage", "clearpage"),
            ("textbackslash{}clearpage", "clearpage"),
            (r"\\subsubsection", r"\\Needspace{6cm}\\subsubsection"),
            (r"\\subsection", r"\\Needspace{8cm}\\subsection"),
        ]

        for old, new in replacements:
            content = content.replace(old, new)

        with open(filepath, "w", encoding="utf-8") as file:
            file.write(content)

        print(f"Successfully processed {filepath}")

    except FileNotFoundError:
        print(f"Error: File {filepath} not found")
    except Exception as e:
        print(f"An error occurred: {str(e)}")


def code_listings():
    N = 40

    # Open the report file
    report = get_file_contents(WORKING_PATH + "/report.tex")

    begins = []
    ends = []

    # Find the beginnings and endings of code listings
    for i in range(len(report)):
        if report[i].find("\\begin{minted}") >= 0:
            begins.append(i)
        if report[i].find("\\end{minted}") >= 0:
            ends.append(i)

    # There should be the same amount of elements in both lists
    assert len(begins) == len(ends)

    # If a code listing takes more than N lines, allow it to break pages
    for i in range(len(begins)):
        code_length = ends[i] - begins[i]
        if code_length >= N:
            report[begins[i]] = report[begins[i]].replace(
                "\\begin{minted}[]", "\\begin{minted}[samepage=false]"
            )

    # Save the report file
    save_file_contents(WORKING_PATH + "/report.tex", report)


def compile_latex_report():
    """
    Compiles LaTeX report and copies the output to the correct location.
    Equivalent to the bash script that runs pdflatex twice and copies the output.
    """
    cwd = Path.cwd()

    # Change to working directory
    os.chdir(cwd / WORKING_PATH)
    try:
        # Run pdflatex twice
        for _ in range(2):
            result = subprocess.run(
                ["pdflatex", "-shell-escape", "-interaction=nonstopmode", "main.tex"],
                capture_output=True,
                text=True,
            )

            # Check if the compilation was successful
            if result.returncode != 0:
                print("LaTeX compilation failed:")
                print(result.stderr)
                return False

        # Copy the output file
        shutil.copy("main.pdf", Path.cwd() / OUTPUT_PATH / "report.pdf")
        print("Successfully compiled and copied report")
    finally:
        os.chdir(cwd)
    return True
