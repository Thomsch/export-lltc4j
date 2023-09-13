"""
Regression tests for the export script.
"""

from mongoengine import connect

from export_lltc4j_utb import print_commits


def test_no_arguments(capsys):
    """
    Tests that export script doesn't take any parameters and finishes correctly.
    """

    connect("mongoenginetest", host="mongomock://localhost", alias="default")

    print_commits()

    captured = capsys.readouterr()

    assert "project_name,vcs_url,commit_hash,parent_hash" in captured.out
