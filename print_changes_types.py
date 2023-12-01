#!/usr/bin/env python3

"""
This script prints on the standard output the manual labels associated with the commits in the LLTC4J dataset[1].
It also print each line of the commit with the label associated with it.

References:
1. Herbold, Steffen, et al. "A fine-grained data set and analysis of tangling in bug fixing commits." Empirical Software Engineering 27.6 (2022): 125.
"""

import argparse
from typing import List

from pycoshark.mongomodels import (
    Project,
    VCSSystem,
    Commit,
    FileAction,
    Hunk,
    File,
)

from export_lltc4j import connect_to_db

import csv

def print_changes_types(commit_hash: str):
    for commit in Commit.objects(revision_hash=commit_hash):
        labels = set()
        for fa in FileAction.objects(commit_id=commit.id):
            for hunk in Hunk.objects(file_action_id=fa.id):
                hunk_content_by_line = hunk.content.splitlines()
                labelled_lines = {} # dict indexed by line content.
                 
                # Add the labels of the lines in the hunk to the set of labels
                labels.update(list(hunk.lines_verified.keys()))

                for label, line_offsets in hunk.lines_verified.items():
                    for line_offset in line_offsets:
                        labelled_lines[hunk_content_by_line[line_offset]] = label

                for line, label in labelled_lines.items():
                    print(f"{label} -> {line}")
            
        print(labels)
def main():
    """
    Implement the logic of the script. See the module docstring.
    """

    main_parser = argparse.ArgumentParser(
        prog="list_tangled_commits.py",
        description="List all commits in the LLTC4J dataset that are tangled.",
    )

    main_parser.add_argument(
        "commits_csv",
        help="File containing the commits",
    )

    args = main_parser.parse_args()

    with open(args.commits_csv) as csvfile:
        connect_to_db()
        csv_reader = csv.DictReader(csvfile)

        for row in csv_reader:
            print(f"Project {row['vcs_url'].rsplit('/', 1)[-1]} Commit {row['commit_hash']}")
            commit_hash = row['commit_hash']
            print_changes_types(commit_hash)
            print()


if __name__ == "__main__":
    main()
