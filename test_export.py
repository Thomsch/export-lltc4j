"""
Regression tests for the export script.
"""

from mongoengine import connect
import mongomock

from export_lltc4j_utb import export_commit_hashes

@mongomock.patch(servers=(('localhost', 27017),))
def test_no_arguments(capsys):
    """
    Tests that export script doesn't take any parameters and finishes correctly.
    """

    connect("mongoenginetest", host="mongomock://localhost", alias="default")

    export_commit_hashes()

    captured = capsys.readouterr()

    assert "project_name,vcs_url,commit_hash,parent_hash" in captured.out
