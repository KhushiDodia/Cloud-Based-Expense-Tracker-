# Expense Tracker (Flask + SQLite)

## Run on Windows
```
cd /d E:\expense-tracker
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000

## Deploy to the cloud (Render)
1. Push this folder to GitHub.
2. Render > New > Web Service > pick the repo.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Add environment variable `SECRET_KEY` (any long random string).

Note: SQLite on Render's free tier is wiped on redeploy. For permanent data, switch to PostgreSQL or attach a persistent disk and set `DB_PATH`.
