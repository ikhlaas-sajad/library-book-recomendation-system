"""
import_books.py
--------------
Run this ONCE to create the SQLite database and populate it from books.csv.

Usage:
    python import_books.py
"""

import csv
import sqlite3
import os

DB_PATH = "library.db"
CSV_PATH = "books.csv"


def create_database(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS books (
            id        INTEGER PRIMARY KEY,
            title     TEXT    NOT NULL,
            author    TEXT    NOT NULL,
            genre     TEXT    NOT NULL,
            year      INTEGER NOT NULL,
            rating    REAL    NOT NULL,
            pages     INTEGER NOT NULL,
            description TEXT NOT NULL,
            image_url TEXT    DEFAULT '',
            language  TEXT    DEFAULT 'English',
            purpose   TEXT    DEFAULT '',
            length    TEXT    DEFAULT '',
            moods     TEXT    DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS user_ratings (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id     INTEGER NOT NULL,
            rating      INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (book_id) REFERENCES books(id)
        );

        CREATE INDEX IF NOT EXISTS idx_books_genre  ON books(genre);
        CREATE INDEX IF NOT EXISTS idx_books_rating ON books(rating);
        CREATE INDEX IF NOT EXISTS idx_books_year   ON books(year);
    """)

    # Ensure the optional image_url column exists on older databases.
    cursor.execute("PRAGMA table_info(books)")
    columns = [row[1] for row in cursor.fetchall()]
    if "image_url" not in columns:
        cursor.execute("ALTER TABLE books ADD COLUMN image_url TEXT DEFAULT ''")
    if "language" not in columns:
        cursor.execute("ALTER TABLE books ADD COLUMN language TEXT DEFAULT 'English'")
    if "purpose" not in columns:
        cursor.execute("ALTER TABLE books ADD COLUMN purpose TEXT DEFAULT ''")
    if "length" not in columns:
        cursor.execute("ALTER TABLE books ADD COLUMN length TEXT DEFAULT ''")
    if "moods" not in columns:
        cursor.execute("ALTER TABLE books ADD COLUMN moods TEXT DEFAULT ''")

    conn.commit()
    print("✓ Schema created.")


def import_csv(conn: sqlite3.Connection, csv_path: str) -> None:
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    cursor = conn.cursor()
    cursor.execute("DELETE FROM books")          # idempotent re-import

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = []

        for row in reader:
            image_url = (row.get("image_url") or "").strip()
            language = (row.get("language") or "English").strip() or "English"
            purpose = (row.get("purpose") or "").strip()
            length_input = (row.get("length") or "").strip()
            pages = int(row["pages"])
            if not length_input:
                if pages <= 200:
                    length_input = "Short"
                elif pages <= 400:
                    length_input = "Medium"
                else:
                    length_input = "Long"
            moods = ",".join([m.strip() for m in (row.get("moods") or "").split(",") if m.strip()])

            rows.append(
                (
                    int(row["id"]),
                    row["title"].strip(),
                    row["author"].strip(),
                    row["genre"].strip(),
                    int(row["year"]),
                    float(row["rating"]),
                    pages,
                    row["description"].strip(),
                    image_url,
                    language,
                    purpose,
                    length_input,
                    moods,
                )
            )

    cursor.executemany(
        "INSERT INTO books (id, title, author, genre, year, rating, pages, description, image_url, language, purpose, length, moods) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    print(f"✓ Imported {len(rows)} books from '{csv_path}'.")


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        create_database(conn)
        import_csv(conn, CSV_PATH)
        print(f"✓ Database ready at '{DB_PATH}'.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
