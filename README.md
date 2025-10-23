# Seasonal Medicine Predictor

Minimal full-stack app to track past seasonal medicine usage and predict future seasonal requirements.

Stack
- Backend: Flask + SQLAlchemy + pandas
- DB: SQLite (file: data.db)
- Frontend: static HTML + Chart.js (via CDN)

Run
1. Create a Python virtualenv and install requirements:

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt
` .\venv310\Scripts\python -u app.py``

2. Run the app:

```powershell
$env:FLASK_APP = 'app'; flask run
```

API
- POST /api/upload - upload CSV of historical records (see sample)
- GET /api/prediction?season=Winter - returns predicted required quantities per medicine

Notes
- This is a minimal prototype. For production, add authentication, input validation, and deployment configuration.
