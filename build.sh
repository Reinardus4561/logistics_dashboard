#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --noinput
python manage.py migrate

# Seed data and run ETL to populate DWH tables in the SQLite database
python manage.py run_etl --seed
