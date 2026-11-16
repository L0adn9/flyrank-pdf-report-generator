# PDF report generator

Query → render → store → serve: SQL aggregation over a small SQLite database, rendered to a PDF
with headless Chromium (Playwright), generated and handed out by link from a FastAPI API.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
uvicorn app:app --port 8000
```
