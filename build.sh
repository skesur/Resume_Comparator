#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

# Pre-download SentenceTransformer model only if explicitly enabled (Paid Tiers)
if [ "$ENABLE_TRANSFORMERS" = "true" ]; then
    python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
fi

python manage.py collectstatic --no-input
python manage.py migrate

