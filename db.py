import sqlite3
from pathlib import Path

DB = Path(__file__).parent / 'shop.sqlite3'

def connect():
    con = sqlite3.connect(DB, timeout=15)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    return con

def init():
    with connect() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS products(
          id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT NOT NULL,
          name TEXT NOT NULL, price INTEGER NOT NULL CHECK(price>=0),
          description TEXT DEFAULT '', image TEXT DEFAULT '', active INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS cards(
          id INTEGER PRIMARY KEY AUTOINCREMENT, bank TEXT NOT NULL,
          number TEXT NOT NULL, holder TEXT NOT NULL, active INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS orders(
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
          total INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
          card_id INTEGER, receipt TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS order_items(
          order_id INTEGER NOT NULL, product_id INTEGER NOT NULL,
          name TEXT NOT NULL, price INTEGER NOT NULL, qty INTEGER NOT NULL,
          FOREIGN KEY(order_id) REFERENCES orders(id)
        );
        ''')
