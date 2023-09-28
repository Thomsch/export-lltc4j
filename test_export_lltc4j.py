"""
Regression tests for the export script.
"""


from typing import Dict, List

from pycoshark.mongomodels import Hunk
import pandas as pd

from export_lltc4j import label_lines


def make_hunk(
    old_start: int,
    new_start: int,
    lines_verified: Dict[str, List[int]],
    content: List[str],
):
    """
    Helper function to generate a hunk.

    Arguments:
    - old_start: old line number where the hunk start.
    - new_start: new line number where the hunk start.
    - lines_verified: dictionnary of labels for each line. The lines are indexed from 0.
    - content: lines in the diff. Must start with "- " or "+ ".
    """
    deleted_lines = 0
    added_lines = 0
    for line in content:
        if line.startswith("-"):
            deleted_lines += 1
        elif line.startswith("+"):
            added_lines += 1
        else:
            raise ValueError(
                f"Found invalid start of line for {line}. Expected '-' or '+'"
            )

    return Hunk(
        new_start=new_start,
        new_lines=added_lines,
        old_start=old_start,
        old_lines=deleted_lines,
        content="\n".join(content),
        lines_verified=lines_verified,
    )


def test_label_lines_column_dataframe():
    """
    Tests that #label_lines() returns a dataframe with the expected columns
    """
    expected_df = pd.DataFrame(columns=["source", "target", "group"]).astype(
        {"source": "Int64", "target": "Int64"}
    )
    df = label_lines([])
    pd.testing.assert_frame_equal(expected_df, df)


def test_label_lines_modified_line():
    """
    Test that a modified line is exported as two rows in the dataframe.
    """
    hunk = make_hunk(
        old_start=42,
        new_start=42,
        content=["- A", "+ B"],
        lines_verified={"bugfix": [0, 1]},
    )

    expected_df = pd.DataFrame(
        [(42, None, "bugfix"), (None, 42, "bugfix")],
        columns=["source", "target", "group"],
    ).astype({"source": "Int64", "target": "Int64"})

    df = label_lines([hunk])
    pd.testing.assert_frame_equal(expected_df, df)


def test_label_lines_disjoint_labels():
    """
    Tests that lines with different labels are exported with the correct source
    and target line numbers.
    """
    hunk = make_hunk(
        old_start=42,
        new_start=42,
        content=["- A", "- B", "+ AA", "+ BB", "+ CC"],
        lines_verified={"bugfix": [0, 2, 4], "no_bugfix": [1, 3]},
    )

    expected_df = pd.DataFrame(
        [
            (42, None, "bugfix"),
            (None, 42, "bugfix"),
            (None, 44, "bugfix"),
            (43, None, "nonbugfix"),
            (None, 43, "nonbugfix"),
        ],
        columns=["source", "target", "group"],
    ).astype({"source": "Int64", "target": "Int64"})

    df = label_lines([hunk])
    pd.testing.assert_frame_equal(expected_df, df, check_like=True)


def test_label_lines_multiple_hunks():
    """
    Tests that line changed in the hunks are returned in the same dataframe.
    """
    hunk1 = make_hunk(
        old_start=7,
        new_start=7,
        content=["- A1"],
        lines_verified={"bugfix": [0]},
    )

    hunk2 = make_hunk(
        old_start=42,
        new_start=41,
        content=["- A2"],
        lines_verified={"bugfix": [0]},
    )

    expected_df = pd.DataFrame(
        [
            (7, None, "bugfix"),
            (42, None, "bugfix"),
        ],
        columns=["source", "target", "group"],
    ).astype({"source": "Int64", "target": "Int64"})

    df = label_lines([hunk1, hunk2])
    pd.testing.assert_frame_equal(expected_df, df, check_like=True)


def test_label_lines_inter_hunk_start_change():
    """
    Tests that changes in the start of a hunk due to previous hunk changes
    updates the values accordingly.
    """
    hunk1 = make_hunk(
        old_start=7,
        new_start=7,
        content=["- A1"],
        lines_verified={"bugfix": [0]},
    )

    hunk2 = make_hunk(
        old_start=42,
        new_start=41,
        content=["+ A2"],
        lines_verified={"bugfix": [0]},
    )

    expected_df = pd.DataFrame(
        [
            (7, None, "bugfix"),
            (None, 41, "bugfix"),
        ],
        columns=["source", "target", "group"],
    ).astype({"source": "Int64", "target": "Int64"})

    df = label_lines([hunk1, hunk2])
    pd.testing.assert_frame_equal(expected_df, df, check_like=True)


def test_label_lines_exclude_non_code_changes():
    """
    Tests that lines changed for non code reasons are ignored.
    """
    hunk = make_hunk(
        old_start=0,
        new_start=0,
        content=["+ 0", "+ 1", "+ 2", "+ 3", "+ 4", "+ 5", "+ 6", "+ 7", "+ 8", "+ 9"],
        lines_verified={
            "test": [0],
            "refactoring": [1],
            "unrelated": [2],
            "bugfix": [3],
            "documentation": [4],
            "None": [5],
            "test_doc_whitespace": [6],
            "whitespace": [7],
            "no_bugfix": [8],
            "unkown_label": [9],  # An unkown label should not raise an error.
        },
    )

    expected_df = pd.DataFrame(
        [
            (None, 1, "nonbugfix"),
            (None, 2, "nonbugfix"),
            (None, 3, "bugfix"),
            (None, 8, "nonbugfix"),
        ],
        columns=["source", "target", "group"],
    ).astype({"source": "Int64", "target": "Int64"})

    df = label_lines([hunk])
    pd.testing.assert_frame_equal(expected_df, df, check_like=True)
