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


def export_commit_hashes():
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


def export_ground_truth():
    """
    Print the commits in the LLTC4J dataset on stdout.
    The format is the following:
    - project_name: Name of the project.
    - vcs_url: URL of the VCS
    - commit_hash: Hash of the commit.
    - parent_hash: Hash of the parent commit.
    """
    project_ids = []
    for project in Project.objects(name__in=PROJECTS):
        project_ids.append(project.id)

    for vcs_system in VCSSystem.objects(
        project_id__in=project_ids, repository_type="git"
    ):
        for commit in Commit.objects(vcs_system_id=vcs_system.id):
            if (
                commit.labels is not None
                and "validated_bugfix" in commit.labels
                and commit.labels["validated_bugfix"]
                and len(commit.parents) == 1
            ):
                print(commit.revision_hash)

                for fa in FileAction.objects(commit_id=commit.id):
                    new_file = File.objects(id=fa.file_id).get()

                    if fa.old_file_id:
                        old_file = File.objects(id=fa.old_file_id).get()
                    else:
                        old_file = new_file

                    print(f"Old File: {new_file.path}")
                    print(f"New File: {old_file.path}")
                    print(f"Line deleted: {fa.lines_deleted}")
                    print(f"Line added: {fa.lines_added}")

                    print(f"--- {old_file.path}")
                    print(f"+++ {new_file.path}")

                    for hunk in Hunk.objects(file_action_id=fa.id):
                        print(
                            f"@@ -{hunk.old_start},{hunk.old_lines} +{hunk.new_start},{hunk.new_lines} @@"
                        )

                        for i, line in enumerate(hunk.content.splitlines()):
                            print(f"[{i}]{line}")  # Just a string representing the hunk

                        print(f"Verified{hunk.lines_verified}")


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
    commits_parser.set_defaults(func=export_ground_truth)

    args = main_parser.parse_args()

    connect_to_db()
    args.func()


if __name__ == "__main__":
    main()
