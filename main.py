from fastmcp import FastMCP
import os
import aiosqlite
import tempfile
import sqlite3
from typing import Optional

TEMP_DIR = tempfile.gettempdir()
DB_PATH = os.path.join(TEMP_DIR, "expenses.db")

mcp = FastMCP("ExpenseTracker")

def init_db():
    with sqlite3.connect(DB_PATH) as c:
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("""
            CREATE TABLE IF NOT EXISTS expenses(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT DEFAULT '',
                note TEXT DEFAULT ''
            )
        """)
        c.commit()

# Don't crash if init fails during build - init on first tool call instead
try:
    init_db()
except:
    pass

@mcp.tool()
async def add_expense(date: str, amount: float, category: str, subcategory: str = "", note: str = ""):
    init_db()
    async with aiosqlite.connect(DB_PATH) as c:
        cur = await c.execute(
            "INSERT INTO expenses(date, amount, category, subcategory, note) VALUES (?,?,?,?,?)",
            (date, amount, category, subcategory, note)
        )
        await c.commit()
        return {"status": "success", "id": cur.lastrowid}

@mcp.tool()
async def list_expenses(start_date: str, end_date: str):
    init_db()
    async with aiosqlite.connect(DB_PATH) as c:
        cur = await c.execute(
            "SELECT id, date, amount, category, subcategory, note FROM expenses WHERE date BETWEEN? AND? ORDER BY date DESC",
            (start_date, end_date)
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in await cur.fetchall()]

@mcp.tool()
async def summarize(start_date: str, end_date: str, category: Optional[str] = None):
    init_db()
    async with aiosqlite.connect(DB_PATH) as c:
        query = "SELECT category, SUM(amount) AS total_amount, COUNT(*) AS count FROM expenses WHERE date BETWEEN? AND?"
        params = [start_date, end_date]
        if category:
            query += " AND category =?"
            params.append(category)
        query += " GROUP BY category ORDER BY total_amount DESC"
        cur = await c.execute(query, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in await cur.fetchall()]