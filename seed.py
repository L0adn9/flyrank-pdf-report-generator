"""Fill report.db with the 60 books scraped in A9 (The polite scraper) - data/books.json.

Safe to run twice: it deletes every row first, so there is always exactly one clean copy.
Run: python seed.py
"""

import json

from db import ROOT, connect

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT    NOT NULL,
    price  REAL    NOT NULL,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    url    TEXT    NOT NULL UNIQUE
)
"""


def seed() -> int:
    books = json.loads((ROOT / "data" / "books.json").read_text(encoding="utf-8"))
    with connect() as conn:  # one transaction: all rows or none
        conn.execute(SCHEMA)
        conn.execute("DELETE FROM books")
        conn.executemany(
            "INSERT INTO books (title, price, rating, url) VALUES (?, ?, ?, ?)",
            [(b["title"], b["price_gbp"], b["rating"], b["product_url"]) for b in books],
        )
        return conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]


if __name__ == "__main__":
    print(f"books: {seed()}")
