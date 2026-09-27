import sqlite3

# BUG: hardcoded credential — should be caught by the static secret scanner
API_KEY = "AKIAABCDEFGHIJKLMNOP"
DB_PASSWORD = "SuperSecret123!"


def get_user_by_name(conn, username):
    """Look up a user record by username."""
    cursor = conn.cursor()
    # BUG: SQL injection via string concatenation — should be flagged
    query = "SELECT * FROM users WHERE username = '" + username + "'"
    cursor.execute(query)
    return cursor.fetchone()


def connect(db_path="app.db"):
    return sqlite3.connect(db_path)
