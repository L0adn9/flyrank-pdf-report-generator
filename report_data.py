"""Boring SQL is 80% of reporting: 60 rows in, four sections out."""

import json

from db import connect

QUERIES = {
    "total_books": "SELECT COUNT(*) AS n FROM books",
    "average_price": "SELECT ROUND(AVG(price), 2) AS avg FROM books",
    "top_5_expensive": """
        SELECT title, price, rating
        FROM books
        ORDER BY price DESC, title
        LIMIT 5
    """,
    "books_per_rating": """
        SELECT rating, COUNT(*) AS books, ROUND(AVG(price), 2) AS avg_price
        FROM books
        GROUP BY rating
        ORDER BY rating DESC
    """,
}


def get_report_data() -> dict:
    with connect() as conn:
        return {
            "total_books": conn.execute(QUERIES["total_books"]).fetchone()["n"],
            "average_price": conn.execute(QUERIES["average_price"]).fetchone()["avg"],
            "top_5_expensive": [dict(r) for r in conn.execute(QUERIES["top_5_expensive"])],
            "books_per_rating": [dict(r) for r in conn.execute(QUERIES["books_per_rating"])],
        }


if __name__ == "__main__":
    print(json.dumps(get_report_data(), indent=2, ensure_ascii=False))
