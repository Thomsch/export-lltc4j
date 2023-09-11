"""
Regression tests for the export script.
"""

import subprocess


def test_no_arguments():
    """
    Tests that export script doesn't take any parameters and finishes correctly.
    """

    # Run the script with no arguments and capture the output
    result = subprocess.run(
        ["python", "export_lltc4j_utb.py"], capture_output=True, text=True
    )

    # Check that the exit code is 0, indicating success
    assert result.returncode == 0

    # Check that the output contains "All done"
    assert "All done" in result.stdout
