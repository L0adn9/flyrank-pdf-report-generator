"""Boring SQL is 80% of reporting: 60 rows in, four sections out."""

import json

from db import connect

# Every query takes the same filter: rating >= ? (1 = all books).
QUERIES = {
    "total_books": "SELECT COUNT(*) AS n FROM books WHERE rating >= ?",
    "average_price": "SELECT ROUND(AVG(price), 2) AS avg FROM books WHERE rating >= ?",
    "top_5_expensive": """
        SELECT title, price, rating
        FROM books
        WHERE rating >= ?
        ORDER BY price DESC, title
        LIMIT 5
    """,
    "books_per_rating": """
        SELECT rating, COUNT(*) AS books, ROUND(AVG(price), 2) AS avg_price
        FROM books
        WHERE rating >= ?
        GROUP BY rating
        ORDER BY rating DESC
    """,
}


def get_report_data(min_rating: int = 1) -> dict:
    p = (min_rating,)
    with connect() as conn:
        return {
            "min_rating": min_rating,
            "total_books": conn.execute(QUERIES["total_books"], p).fetchone()["n"],
            "average_price": conn.execute(QUERIES["average_price"], p).fetchone()["avg"] or 0.0,
            "top_5_expensive": [dict(r) for r in conn.execute(QUERIES["top_5_expensive"], p)],
            "books_per_rating": [dict(r) for r in conn.execute(QUERIES["books_per_rating"], p)],
        }


if __name__ == "__main__":
    print(json.dumps(get_report_data(), indent=2, ensure_ascii=False))
