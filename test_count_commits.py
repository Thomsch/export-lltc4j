"""
Regression tests for the count script.
"""

import pytest
import pandas as pd
from count_commits import get_change_type


def test_get_change_type_empty():
    """
    Test get_change_type() with an empty dataframe.
    """
    df = pd.DataFrame(columns=["file","source", "target", "group"])
    assert get_change_type(df) == "empty"


def test_get_change_type_bugfix():
    """
    Test get_change_type() with a dataframe with only bugfix changes.
    """
    df = pd.DataFrame(
        [
            ("file1", 7, None, "bugfix"),
            ("file1", 42, None, "bugfix"),
        ],
        columns=["file","source", "target", "group"],
    ).astype({"source": "Int64", "target": "Int64"})
    assert get_change_type(df) == "bugfix"

def test_get_change_type_nonbugfix():
    """
    Test get_change_type() with a dataframe with only nonbugfix changes.
    """
    df = pd.DataFrame(
        [
            ("file1", None, 7, "nonbugfix"),
            ("file1", None, 42, "nonbugfix"),
        ],
        columns=["file","source", "target", "group"],
    ).astype({"source": "Int64", "target": "Int64"})
    assert get_change_type(df) == "nonbugfix"

def test_get_change_type_mixed():
    """
    Test get_change_type() with a dataframe with mixed changes.
    """
    df = pd.DataFrame(
        [
            ("file1", 7, None, "bugfix"),
            ("file1", None, 42, "nonbugfix"),
        ],
        columns=["file","source", "target", "group"],
    ).astype({"source": "Int64", "target": "Int64"})
    assert get_change_type(df) == "mixed"


def test_get_change_type_unknown():
    """
    Test get_change_type() with a dataframe with unknown changes.
    """
    df = pd.DataFrame(
        [
            ("file1", 7, None, "bugfix"),
            ("file1", None, 42, "nonbugfix"),
            ("file1", 7, None, "unknown"),
            ("file1", None, 42, "unknown"),
        ],
        columns=["file","source", "target", "group"],
    ).astype({"source": "Int64", "target": "Int64"})

    with pytest.raises(ValueError):
        assert get_change_type(df)