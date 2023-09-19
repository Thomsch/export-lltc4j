#!/usr/bin/env python3

"""
This script exports the VCS url, commit hash, and labelled lines from the LLTC4J
dataset[1]. LLTC4J stands for Line-Labelled Tangled Commits for Java.

The commit exported have the following properties:
- The commit is labelled as a bugfix by developers and researchers.
- The commit has only one parent. This is to avoid ambiguity where we don't know which parent was diffed against to manually label the lines.

References:
1. Herbold, Steffen, et al. "A fine-grained data set and analysis of tangling in bug fixing commits." Empirical Software Engineering 27.6 (2022): 125.

Command Line Args:
- None

Output:
The VCS url, commit hash and labelled lines are outputed on stdout with the folowing
CSV format:
- vcs_url: URL of the VCS
- commit_hash: Hash of the commit.
- ground_truth: The manual labelling for this commit.
"""
import argparse
import os
import sys
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
    "Ant-ivy",
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
LINE_LABELS_CODE = ["bugfix", "refactoring", "unrelated", "no_bugfix"]
LINE_LABELS_CODE_FIX = ["bugfix"]
LINE_LABELS_CODE_NO_FIX = ["refactoring", "unrelated", "no_bugfix"]


def connect_to_db():
    """
    Connect to the smartshark database or throws an error.
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

    if Project.objects(name="giraph").get():
        print("Connected to database", file=sys.stderr)
    else:
        raise Exception(
            "Connection to database failed. Please check your credentials in the script and that the mongod is running."
        )


def export_commit_hashes(args: argparse.Namespace):
    """
    Print the commits in the LLTC4J dataset on stdout.
    The format is the following:
    - project_name: Name of the project.
    - vcs_url: URL of the VCS
    - commit_hash: Hash of the commit.
    - parent_hash: Hash of the parent commit.
    """
    print("project_name,vcs_url,commit_hash,parent_hash")

    project_ids = []

    for project in Project.objects(name__in=PROJECTS):
        project_ids.append(project.id)

    for vcs_system in VCSSystem.objects(
        project_id__in=project_ids, repository_type="git"
    ):
        project = Project.objects(id=vcs_system.project_id).get()
        for commit in Commit.objects(vcs_system_id=vcs_system.id):
            if (
                commit.labels is not None
                and "validated_bugfix" in commit.labels
                and commit.labels["validated_bugfix"]
                and len(commit.parents) == 1
            ):
                print(
                    f"{project.name},{vcs_system.url},{commit.revision_hash},{commit.parents[0]}"
                )


def export_ground_truth_for_hunks(hunks) -> pd.DataFrame:
    """
    Exports the ground truth for a file in CSV format.

    Arguments:
    - hunks: The hunks of the file.

    Returns: A list of the ground truth for each line in the file. The format is the following:
    [{
        source_line_number: The line number of in the old file.
        target_line_number: The line number of in the new file.
        label: The label of the line.
    }, ...]
    """
    ground_truth = []

    for hunk in hunks:
        hunk_content_by_line = hunk.content.splitlines()

        for label, offset_line_numbers in hunk.lines_verified.items():
            if (label not in LINE_LABELS_CODE):
                continue

            for i in offset_line_numbers:
                source_line_number = None
                target_line_number = None

                if hunk_content_by_line[i].startswith("-"):
                    source_line_number = hunk.old_start + i
                elif hunk_content_by_line[i].startswith("+"):
                    target_line_number = hunk.new_start + i
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
    return pd.DataFrame(ground_truth, columns=["source", "target", "group"]).astype({"source": "Int64", "target": "Int64"}, copy=False)


def export_ground_truth_for_commit(commit):
    """
    Exports the ground truth for a commit.
    file, source, target, group 
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

            if not file.path.endswith(".java") or file.path.endswith("Test.java") or "src/test" in file.path:
                continue

            hunks_df = export_ground_truth_for_hunks(Hunk.objects(file_action_id=fa.id))
            hunks_df["file"] = file.path
            file_frames.append(hunks_df)
        if len(file_frames) == 0:
            return None
        return pd.concat(file_frames)


def export_ground_truth(args: argparse.Namespace):
    """
    Exports the ground truth from the LLTC4J dataset into CSV files. Results are
    written in the directory specified by the --outdir argument. The ground truth
    for each commit is store in a directory named after the project and the commit
    hash. The ground truth is stored in a file named truth.csv.

    The format of the truth.csv file is the following:
    - file: The path of the file.
    - source: The line number of the line in the old file or None.
    - target: The line number of the line in the new file or None.
    - group: The label of the line.

    Arguments:
    - args: The command line arguments. 
            * The --outdir argument is required. 
            * The --projects argument is optional. By default, all projects are exported.
            * The --number argument is optional. By default, all commits are exported.
    """

    out_dir = os.path.realpath(args.outdir)
    if not os.path.exists(args.outdir):
        raise ValueError(f"Directory {out_dir} does not exist.")

    early_exit = False
    counter = 0
    for project in Project.objects(name__in=args.projects):
        print(f"Processing project {project.name}", file=sys.stderr)
        vcs_system = VCSSystem.objects(project_id=project.id).get()
        for commit in tqdm(Commit.objects(vcs_system_id=vcs_system.id), desc='Commits'):
            # Early exit if we have processed enough commits.
            if args.number is not None and counter >= args.number:
                early_exit = True
                break

            ground_truth_commit_frame = export_ground_truth_for_commit(commit)
            if ground_truth_commit_frame is not None and len(ground_truth_commit_frame) > 0:
                commit_dir = os.path.join(out_dir, f"{project.name}_{commit.revision_hash[:6]}")
                os.makedirs(commit_dir, exist_ok=True)

                ground_truth_file = os.path.join(commit_dir, "truth.csv")

                # Reorder columns to be compatible with the rest of the pipeline.
                ground_truth_commit_frame = ground_truth_commit_frame.reindex(columns=['file', 'source', 'target', 'group'])
                ground_truth_commit_frame.to_csv(ground_truth_file, index=False)

                counter += 1
        
        if early_exit:
            break
    print(f"Processed {counter} commits.", file=sys.stderr)

def main():
    """
    Implement the logic of the script. See the module docstring.
    """
    main_parser = argparse.ArgumentParser(prog="export_lltc4j_utb.py")
    subparsers = main_parser.add_subparsers(
        title="subcommands",
        help="LLTC4J dataset export commands",
        required=True,
        dest="subcommand",
    )

    commits_parser = subparsers.add_parser(
        "commits-hashes",
        help="Exports the commit hashes of the manually validated bug-fixes from the LLTC4J dataset",
    )
    commits_parser.set_defaults(func=export_commit_hashes)

    commits_parser = subparsers.add_parser(
        "ground-truth",
        help="Exports the ground truth of the manually validated bug-fixes from the LLTC4J dataset",
    )
    commits_parser.add_argument(
        "-o",
        "--outdir",
        help="The output directory where to write the ground truth CSV files.",
        metavar="PATH",
        required=True,
    )
    commits_parser.add_argument(
        "-p",
        "--projects",
        help="The projects to export. By default, all projects are exported.",
        metavar="PROJECT",
        nargs="+",
        default=PROJECTS,
    )
    commits_parser.add_argument(
        "-n",
        "--number",
        help="The number of commits to export. By default, all commits are exported.",
        metavar="NUMBER",
        type=int,
        default=None,
    )
    commits_parser.set_defaults(func=export_ground_truth)

    args = main_parser.parse_args()

    connect_to_db()
    args.func(args)


if __name__ == "__main__":
    main()
