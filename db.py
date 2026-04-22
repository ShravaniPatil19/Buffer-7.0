import mysql.connector
from datetime import datetime

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "1926",
    "database": "navsafe"
}


def get_connection():
    return mysql.connector.connect(**DB_CONFIG)


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # USERS TABLE
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(100) UNIQUE NOT NULL,
        password VARCHAR(255) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ROUTE HISTORY TABLE
    cur.execute("""
    CREATE TABLE IF NOT EXISTS routes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(100) NOT NULL,
        start_location VARCHAR(255) NOT NULL,
        end_location VARCHAR(255) NOT NULL,
        shortest_distance DOUBLE,
        safest_distance DOUBLE,
        safety_score DOUBLE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    cur.close()
    conn.close()


def register_user(username, password):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("INSERT INTO users(username, password) VALUES (%s, %s)", (username, password))
        conn.commit()
        return True
    except:
        return False
    finally:
        cur.close()
        conn.close()


def validate_user(username, password):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, password))
    user = cur.fetchone()

    cur.close()
    conn.close()

    return user is not None


def save_route(username, start, end, shortest_distance, safest_distance, safety_score):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO routes(username, start_location, end_location, shortest_distance, safest_distance, safety_score, created_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (username, start, end, shortest_distance, safest_distance, safety_score,
          datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    conn.commit()
    cur.close()
    conn.close()


def get_route_history(username, limit=5):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT start_location, end_location, shortest_distance, safest_distance, safety_score, created_at
    FROM routes
    WHERE username=%s
    ORDER BY id DESC
    LIMIT %s
    """, (username, limit))

    rows = cur.fetchall()

    cur.close()
    conn.close()
    return rows