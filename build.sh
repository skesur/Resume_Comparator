#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

# Pre-download SentenceTransformer model to prevent Gunicorn request timeout
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

python manage.py collectstatic --no-input
python manage.py migrate

