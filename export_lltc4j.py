#!/usr/bin/env python3

"""
This script exports the LLTC4J dataset from the SmartSHARK database to the disk as CSV files[1].
LLTC4J stands for Line-Labelled Tangled Commits for Java.

The following artifacts are exported:
    - lltc4j-commits.csv contains the list of bug-fixing commits and the url of
      the git repository.
    - The ground truth for each commit in lltc4j-commits.csv. The ground truth
      is a CSV file labelling each changed line in the commit with a group. Only
      lines changing the code are included.

The commit exported have the following properties:
    - The commit is labelled as a bugfix by developers and researchers.
    - The commit has only one parent. This is to avoid ambiguity where we don't know which parent was diffed against to manually label the lines.
    - The commit contains at least one code change. Documentation, tests, and whitespace related changes are ignored.

References:
1. Herbold, Steffen, et al. "A fine-grained data set and analysis of tangling in bug fixing commits." Empirical Software Engineering 27.6 (2022): 125.

Arguments:
    --outdir. Required argument to specify where to put the export results.
    --projects. Optional argument to specify which projects to export. By default, all projects are exported.
    --number. Optional argument to specify how many commits to export. By default, all commits are exported.
"""

import argparse
import os
import sys
from typing import List

from mongoengine import connect
from pycoshark.mongomodels import (
    Project,
    VCSSystem,
    Commit,
    FileAction,
    Hunk,
    File,
)
from pycoshark.utils import create_mongodb_uri_string
from tqdm import tqdm
import pandas as pd

PROJECTS = [
    "ant-ivy",
    "archiva",
    "commons-bcel",
    "commons-beanutils",
    "commons-codec",
    "commons-collections",
    "commons-compress",
    "commons-configuration",
    "commons-dbcp",
    "commons-digester",
    "commons-io",
    "commons-jcs",
    "commons-lang",
    "commons-math",
    "commons-net",
    "commons-scxml",
    "commons-validator",
    "commons-vfs",
    "deltaspike",
    "eagle",
    "giraph",
    "gora",
    "jspwiki",
    "opennlp",
    "parquet-mr",
    "santuario-java",
    "systemml",
    "wss4j",
]

LINE_LABELS = [
    "test",
    "refactoring",
    "unrelated",
    "bugfix",
    "documentation",
    "None",
    "test_doc_whitespace",
    "whitespace",
    "no_bugfix",
]
LINE_LABELS_CODE_FIX = ["bugfix"]
LINE_LABELS_CODE_NO_FIX = ["refactoring", "unrelated", "no_bugfix"]
LINE_LABELS_CODE = LINE_LABELS_CODE_FIX + LINE_LABELS_CODE_NO_FIX


def connect_to_db():
    """
    Connect to the SmartSHARK database or throws an error.
    """
    credentials = {
        "db_user": "",
        "db_password": "",
        "db_hostname": "localhost",
        "db_port": 27017,
        "db_authentication_database": "",
        "db_ssl_enabled": False,
    }
    uri = create_mongodb_uri_string(**credentials)
    connect("smartshark_2_2", host=uri, alias="default")

    # Fail early in case the database doesn't exists. mongodb doesn't provide
    # an API to test if the connection is established directly.
    if Project.objects(name="giraph").get():
        print("Connected to database", file=sys.stderr)
    else:
        raise Exception(
            "Connection to database failed. Please check your credentials in the script and that the mongod is running."
        )


def label_lines(hunks: List[Hunk]) -> pd.DataFrame:
    """
    Groups line changes into two groups for the given hunks. Only lines representing
    changes in the code are included. Line changes for tests, documentation, and whitespace are ignored.

    Arguments:
    - hunks: The hunks containing the lines to label

    Returns:
    A DataFrame with the following columns:
    - source_line_number: The line number of in the old file.
    - target_line_number: The line number of in the new file.
    - label: The label of the line, either "bugfix" or "nonbugfix".
    """
    ground_truth = []

    for hunk in hunks:
        hunk_content_by_line = hunk.content.splitlines()

        for label, offset_line_numbers in hunk.lines_verified.items():
            if label not in LINE_LABELS_CODE:
                continue

            for i in offset_line_numbers:
                source_line_number = None
                target_line_number = None

                if hunk_content_by_line[i].startswith("-"):
                    source_line_number = hunk.old_start + i
                elif hunk_content_by_line[i].startswith("+"):
                    target_line_number = hunk.new_start + i - hunk.old_lines
                else:
                    # Context line. Nothing to do.
                    continue

                if label in LINE_LABELS_CODE_FIX:
                    group = "bugfix"
                elif label in LINE_LABELS_CODE_NO_FIX:
                    group = "nonbugfix"
                else:
                    group = label

                ground_truth.append((source_line_number, target_line_number, group))
    return pd.DataFrame(ground_truth, columns=["source", "target", "group"]).astype(
        {"source": "Int64", "target": "Int64"}, copy=False
    )


def export_ground_truth_for_commit(commit) -> pd.DataFrame:
    """
    Exports the ground truth for a commit.
    Only considerr
    Filters out non-java files and Java test files.
    file, source, target, group
    Returns a dataframe or None if there were no relevant changes in the commit.
    """
    if (
        commit.labels is not None
        and "validated_bugfix" in commit.labels
        and commit.labels["validated_bugfix"]
        and len(commit.parents) == 1
    ):
        file_frames = []
        for fa in FileAction.objects(commit_id=commit.id):
            file = None

            if fa.old_file_id:
                file = File.objects(id=fa.old_file_id).get()

            if not file or fa.mode == "R":
                # If the file was renamed, prefer the new file instead of the old file.
                # This behaviour is consistent with the unidiff library we use
                # in our evaluation framework.
                file = File.objects(id=fa.file_id).get()

            if (
                not file.path.endswith(".java")
                or file.path.endswith("Test.java")
                or "src/test" in file.path
            ):
                continue

            hunks_df = label_lines(Hunk.objects(file_action_id=fa.id))
            hunks_df["file"] = file.path
            file_frames.append(hunks_df)
        if len(file_frames) == 0:
            return None
        return pd.concat(file_frames)
    return None


def export_lltc4j(out_dir: str, projects: List[str], number: int):
    """
    Exports the LLTC4J dataset from its database to the disk as CSV files.
    The following artifacts are exported:
    - lltc4j-commits.csv contains the list of bug-fixing commits and the url of
      the git repository.
    - The ground truth for each commit in lltc4j-commits.csv. The ground truth
      is a CSV file labelling each changed line in the commit with a group. Only
      lines changeding the code are included.

    lltc4j-commits.csv is written at the root of the directory specified by the --outdir argument.

    The ground truth for each commit is stored in a file named truth.csv located in a directory named after the project and the commit
    hash at the root of the directory specified by the --outdir argument.

    The format of the lltc4j-commits.csv is the following:
    - vcs_url: URL of the VCS
    - commit_hash: Hash of the commit.
    - parent_hash: Hash of the parent commit.

    The format of the truth.csv file is the following:
    - file: The path of the file.
    - source: The line number of the line in the old file or None.
    - target: The line number of the line in the new file or None.
    - group: The label of the line.

    Arguments:
    - outdir: Root directory where to store the exported files.
    - projects: List of projects to include.
    - number: Number of commits to include.
    """

    early_exit = False
    exported_commits_counter = 0
    commits_hashes = []

    for project in Project.objects(name__in=projects):
        print(f"Processing project {project.name}", file=sys.stderr)
        vcs_system = VCSSystem.objects(project_id=project.id).get()
        for commit in tqdm(Commit.objects(vcs_system_id=vcs_system.id), desc="Commits"):
            # Early exit if we have processed enough commits.
            if number is not None and exported_commits_counter >= number:
                early_exit = True
                break

            ground_truth_commit_frame = export_ground_truth_for_commit(commit)
            if (
                ground_truth_commit_frame is not None
                and len(ground_truth_commit_frame) > 0
            ):
                # Reorder columns to be compatible with the rest of the pipeline.
                ground_truth_commit_frame = ground_truth_commit_frame.reindex(
                    columns=["file", "source", "target", "group"]
                )

                # Create directory for the commit to store results if it doesn't exist yet.
                commit_dir = os.path.join(
                    out_dir, f"{project.name}_{commit.revision_hash[:6]}"
                )
                os.makedirs(commit_dir, exist_ok=True)

                # Export ground truth to CSV file.
                ground_truth_file = os.path.join(commit_dir, "truth.csv")
                ground_truth_commit_frame.to_csv(ground_truth_file, index=False)

                commits_hashes.append(
                    (vcs_system.url, commit.revision_hash, commit.parents[0])
                )
                exported_commits_counter += 1

        if early_exit:
            break

    commits_hashes_df = pd.DataFrame(
        commits_hashes, columns=["vcs_url", "commit_hash", "parent_hash"]
    )
    commit_hashes_file = os.path.join(out_dir, "lltc4j-commits.csv")
    commits_hashes_df.to_csv(commit_hashes_file, index=False)

    print(f"Processed {exported_commits_counter} commits.", file=sys.stderr)


def main():
    """
    Implement the logic of the script. See the module docstring.
    """
    main_parser = argparse.ArgumentParser(
        prog="export_lltc4j_utb.py",
        description="Exports the commit hashes and ground truth from the manually validated bug-fixes from the LLTC4J dataset",
    )

    main_parser.add_argument(
        "-o",
        "--outdir",
        help="The output directory storing the commit list and the ground truth CSVs.",
        metavar="PATH",
        required=True,
    )

    main_parser.add_argument(
        "-p",
        "--projects",
        help="The projects to export. By default, all projects are exported.",
        metavar="PROJECT",
        nargs="+",
        default=PROJECTS,
    )

    main_parser.add_argument(
        "-n",
        "--number",
        help="The number of commits to export. By default, all commits are exported.",
        metavar="NUMBER",
        type=int,
        default=None,
    )

    args = main_parser.parse_args()

    out_dir = os.path.realpath(args.outdir)
    if not os.path.exists(args.outdir):
        raise ValueError(f"Directory {out_dir} does not exist.")

    connect_to_db()
    export_lltc4j(out_dir, args.projects, args.number)


if __name__ == "__main__":
    main()
