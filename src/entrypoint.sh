cd /src/API
celery -A API worker --loglevel=info &
python API.py
