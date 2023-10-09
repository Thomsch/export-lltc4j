#!/bin/bash
# Updates the commit list exported from the SmarkShark database by `export_lltc4j.py`
# to account for the changes in the projects on GitHub.
#
# Changes:
# - The wss4j project was renamed to ws-wss4j.
#

set -o errexit    # Exit immediately if a command exits with a non-zero status
set -o nounset    # Exit if script tries to use an uninitialized variable
set -o pipefail   # Produce a failure status if any command in the pipeline fails

if [ $# -ne 1 ] ; then
    echo 'usage: update_commit_list.sh <commits_file>'
    exit 1
fi

commit_list="$1"

# Check if the commit list file exists
if [ ! -f "$commit_list" ]; then
    echo "Input file does not exist"
    exit 1
fi

# Modify the file in place
sed -i -e 's@apache/wss4j.git@apache/ws-wss4j.git@g' "$commit_list"
