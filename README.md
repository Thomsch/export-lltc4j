# Line-Labelled Tangled Commits for Java exporter
This project exports the Line-Labelled Tangled Commits for Java (LLTC4J) dataset to the untangling tool evaluation framework.

The size of the database where the LLTC4J dataset is 250GB on the "small" version which makes working with this dataset on personal laptop prohibitive. This script exports only the necessary data to evluate the untangling tool.

This script exports the list of commit hashes that have been manually validated to fix a bug (1) and have their changed lines labelled manually (2).

## Installation

### Preparation of the Database

First, you need to prepare a local database for analysis. 

- Download a release of the SmartSHARK MongoDB. [You can find a list of releases on the website of the database's authors](https://smartshark.github.io/dbreleases/). We recommend to always use the latest release. 
- Then, you must prepare the MongoDB instance where you want to host the data. A guide on how to setup a fresh MognoDB can be found [here](https://docs.mongodb.com/manual/installation/#install-mongodb).
- Run [mongorestore](https://docs.mongodb.com/database-tools/mongorestore/) to load the data into your local database.

For example, on Ubuntu 18.04 you can achieve all this as follows for release 2.1 of the database. *This requires about 650 GB of free disk space!*

```
wget -O smartshark_2_1.agz http://141.5.100.155/smartshark_2_1.agz
# download the following archive for the small version without code clones and code metrics, which only requires about 90 GB of free disk space
# wget -O smartshark_2_1.agz http://141.5.100.155/smartshark_2_1_small.agz
wget -qO - https://www.mongodb.org/static/pgp/server-4.0.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu bionic/mongodb-org/4.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-4.0.list
sudo apt-get update
sudo apt-get install -y mongodb-org
sudo systemctl daemon-reload
sudo systemctl start mongod
mongorestore --gzip --archive=smartshark_1_0.agz
```

### Preparing the python environment
We recommend using a virtual environment.

```
sudo apt-get install python3-venv build-essential python3-dev
git clone https://github.com/Thomsch/export_lltc4j
cd export_lltc4j/
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage
To run the exporter, run the following:

```
python3 export_lltc4j_utb.py > lltc4j_commits.csv
```