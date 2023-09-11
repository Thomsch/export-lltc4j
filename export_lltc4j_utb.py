#!/usr/bin/env python3

"""
This script exports the VCS url, commit hash, and labelled lines from the LLTC4J
dataset[1]. LLTC4J stands for Line-Labelled Tangled Commits for Java.

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
import sys


def main():
    """
    Implement the logic of the script. See the module docstring.
    """
    args = sys.argv[1:]

    if len(args) > 0:
        print(f"usage: python3 {sys.argv[0]}")
        sys.exit(1)

    print("All done")


if __name__ == "__main__":
    main()
