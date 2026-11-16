"""Render: a report object -> an HTML page -> a PDF printed by headless Chromium."""

from datetime import date
from html import escape
from pathlib import Path

from playwright.sync_api import sync_playwright

from db import connect
from report_data import get_report_data

STARS = {1: "★☆☆☆☆", 2: "★★☆☆☆", 3: "★★★☆☆", 4: "★★★★☆", 5: "★★★★★"}

CSS = """
* { box-sizing: border-box; }
body { font-family: "Helvetica Neue", Arial, sans-serif; color: #1f2937; font-size: 11px; margin: 0; }
h1 { font-size: 22px; margin: 0 0 2px; color: #0f766e; }
h2 { font-size: 14px; margin: 22px 0 8px; color: #0f766e; }
.sub { color: #6b7280; margin: 0 0 16px; }
.totals { display: flex; gap: 12px; }
.card { flex: 1; border: 1px solid #d1d5db; border-radius: 8px; padding: 10px 14px; background: #f0fdfa; }
.card .label { color: #6b7280; font-size: 10px; text-transform: uppercase; letter-spacing: .05em; }
.card .value { font-size: 24px; font-weight: 700; color: #134e4a; }
table { width: 100%; border-collapse: collapse; }
th, td { text-align: left; padding: 5px 6px; border-bottom: 1px solid #e5e7eb; vertical-align: top; }
th { background: #134e4a; color: white; font-weight: 600; }
td.num, th.num { text-align: right; white-space: nowrap; }
tbody tr:nth-child(even) td { background: #f9fafb; }
/* the page-break fix: never slice a row; repeat the header (thead) on every page */
tr { break-inside: avoid; page-break-inside: avoid; }
thead { display: table-header-group; }
.stars { color: #b45309; letter-spacing: 1px; }
"""


FOOTER = """
<div style="width:100%; font-size:8px; color:#6b7280; padding:0 14mm; display:flex; justify-content:space-between;
            font-family: Helvetica, Arial, sans-serif;">
  <span>Bookstore report · generated <span class="date"></span></span>
  <span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span>
</div>
"""


def all_books(min_rating: int = 1) -> list[dict]:
    with connect() as conn:
        return [
            dict(r)
            for r in conn.execute(
                "SELECT title, price, rating FROM books WHERE rating >= ? ORDER BY title", (min_rating,)
            )
        ]


def build_html(data: dict, books: list[dict], today: date | None = None) -> str:
    today = today or date.today()
    top = "".join(
        f"<tr><td>{i}</td><td>{escape(b['title'])}</td><td class='num'>£{b['price']:.2f}</td>"
        f"<td class='stars'>{STARS[b['rating']]}</td></tr>"
        for i, b in enumerate(data["top_5_expensive"], 1)
    )
    ratings = "".join(
        f"<tr><td class='stars'>{STARS[r['rating']]}</td><td class='num'>{r['books']}</td>"
        f"<td class='num'>£{r['avg_price']:.2f}</td></tr>"
        for r in data["books_per_rating"]
    )
    rows = "".join(
        f"<tr><td class='num'>{i}</td><td>{escape(b['title'])}</td><td class='num'>£{b['price']:.2f}</td>"
        f"<td class='stars'>{STARS[b['rating']]}</td></tr>"
        for i, b in enumerate(books, 1)
    )
    min_rating = data.get("min_rating", 1)
    scope = f" · only books rated {min_rating}★ or more" if min_rating > 1 else ""
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Bookstore report {today}</title><style>{CSS}</style></head>
<body>
  <h1>Bookstore report</h1>
  <p class="sub">{today:%d %B %Y} · data: the first 3 catalogue pages of books.toscrape.com{scope}</p>
  <div class="totals">
    <div class="card"><div class="label">Books</div><div class="value">{data['total_books']}</div></div>
    <div class="card"><div class="label">Average price</div><div class="value">£{data['average_price']:.2f}</div></div>
  </div>
  <h2>Top 5 most expensive</h2>
  <table><thead><tr><th>#</th><th>Title</th><th class="num">Price</th><th>Rating</th></tr></thead>
  <tbody>{top}</tbody></table>
  <h2>Books per star rating</h2>
  <table><thead><tr><th>Rating</th><th class="num">Books</th><th class="num">Avg price</th></tr></thead>
  <tbody>{ratings}</tbody></table>
  <h2>All books</h2>
  <table><thead><tr><th class="num">#</th><th>Title</th><th class="num">Price</th><th>Rating</th></tr></thead>
  <tbody>{rows}</tbody></table>
</body></html>"""


def render_pdf(html: str, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.set_content(html, wait_until="load")
            page.pdf(
                path=str(path),
                format="A4",
                print_background=True,
                margin={"top": "18mm", "bottom": "20mm", "left": "14mm", "right": "14mm"},
                display_header_footer=True,
                header_template="<span></span>",
                footer_template=FOOTER,
            )
        finally:
            browser.close()
    return path


if __name__ == "__main__":
    out = render_pdf(build_html(get_report_data(), all_books()), Path("reports/test.pdf"))
    print(f"wrote {out}")
