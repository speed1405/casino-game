import sqlite3
import os

DATABASE_FILE = 'casino.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()

    # Create Users Table
    # Stores username, balance, and last_daily_claim timestamp
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            balance INTEGER DEFAULT 1000,
            last_daily_claim TIMESTAMP
        )
    ''')

    # Create Withdrawals Table
    # Stores BTC withdrawal requests for manual approval
    c.execute('''
        CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount_ingame INTEGER NOT NULL,
            btc_address TEXT NOT NULL,
            btc_amount REAL NOT NULL,
            status TEXT DEFAULT 'Pending',
            request_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    conn.commit()
    conn.close()
    print("Database initialized.")

if __name__ == '__main__':
    init_db()
