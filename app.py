import threading
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from db import ROOT, connect
from render import all_books, build_html, render_pdf
from report_data import get_report_data

REPORTS_DIR = ROOT / "reports"

app = FastAPI(title="PDF report generator", version="1.0")

# Serialises "check for today's report, else generate": without it two simultaneous
# clicks could both see "no report yet" and both render.
generate_lock = threading.Lock()


class ReportRequest(BaseModel):
    force: bool = False


def init_reports_table() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                path       TEXT,
                created_at TEXT NOT NULL
            )
            """
        )


init_reports_table()


def report_json(row) -> dict:
    return {
        "id": row["id"],
        "created_at": row["created_at"],
        "file": f"/reports/{row['id']}/file",
    }


def not_found(report_id: int) -> JSONResponse:
    return JSONResponse(status_code=404, content={"error": f"Report {report_id} not found"})


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/reports", status_code=201)
def create_report(body: ReportRequest | None = None):
    """Idempotent per day: a report already generated today is returned (200) instead of
    rendering another file. {"force": true} skips the check and makes a fresh one (201)."""
    force = body.force if body else False
    with generate_lock:
        if not force:
            with connect() as conn:
                existing = conn.execute(
                    """
                    SELECT * FROM reports
                    WHERE path IS NOT NULL AND date(created_at) = date('now')
                    ORDER BY id DESC LIMIT 1
                    """
                ).fetchone()
            if existing is not None:
                return JSONResponse(status_code=200, content=report_json(existing))
        return generate_report()


def generate_report() -> dict:
    """The whole pipeline inside the request: query -> render -> store -> link."""
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with connect() as conn:
        report_id = conn.execute(
            "INSERT INTO reports (created_at) VALUES (?)", (created_at,)
        ).lastrowid
    path = REPORTS_DIR / f"{report_id}.pdf"
    try:
        render_pdf(build_html(get_report_data(), all_books()), path)
    except Exception:
        # no half-made reports: drop the row if rendering failed
        with connect() as conn:
            conn.execute("DELETE FROM reports WHERE id = ?", (report_id,))
        raise
    with connect() as conn:
        conn.execute("UPDATE reports SET path = ? WHERE id = ?", (str(path.relative_to(ROOT)), report_id))
        row = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
    return report_json(row)


@app.get("/reports/{report_id}")
def get_report(report_id: int):
    with connect() as conn:
        row = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
    if row is None:
        return not_found(report_id)
    return report_json(row)


@app.get("/reports/{report_id}/file")
def get_report_file(report_id: int):
    """The only endpoint that moves the bytes - everything else hands out the link."""
    with connect() as conn:
        row = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
    if row is None or not row["path"] or not (ROOT / row["path"]).exists():
        return not_found(report_id)
    return FileResponse(ROOT / row["path"], media_type="application/pdf", filename=f"report-{report_id}.pdf")
