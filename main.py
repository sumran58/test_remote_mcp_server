import os
import tempfile
from typing import Optional

import aiosqlite
from fastmcp import FastMCP

# Use a temp directory that's guaranteed writable in the cloud sandbox
TEMP_DIR = tempfile.gettempdir()
DB_PATH = os.path.join(TEMP_DIR, "expenses.db")

mcp = FastMCP("ExpenseTracker")


async def init_db():
    async with aiosqlite.connect(DB_PATH) as c:
        await c.execute("PRAGMA journal_mode=WAL")
        await c.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT DEFAULT '',
                note TEXT DEFAULT ''
            )
            """
        )
        await c.commit()


@mcp.tool()
async def add_expense(
    date: str,
    amount: float,
    category: str,
    subcategory: str = "",
    note: str = "",
):
    """Add a new expense entry to the database."""
    try:
        await init_db()
        async with aiosqlite.connect(DB_PATH) as c:
            cur = await c.execute(
                "INSERT INTO expenses(date, amount, category, subcategory, note) VALUES (?, ?, ?, ?, ?)",
                (date, amount, category, subcategory, note),
            )
            await c.commit()
            return {
                "status": "success",
                "id": cur.lastrowid,
                "message": "Expense added successfully",
            }
    except Exception as e:
        return {"status": "error", "message": f"Database error: {str(e)}"}


@mcp.tool()
async def list_expenses(start_date: str, end_date: str):
    """List expense entries within an inclusive date range."""
    try:
        await init_db()
        async with aiosqlite.connect(DB_PATH) as c:
            cur = await c.execute(
                """SELECT id, date, amount, category, subcategory, note
                   FROM expenses
                   WHERE date BETWEEN ? AND ?
                   ORDER BY date DESC, id DESC""",
                (start_date, end_date),
            )
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in await cur.fetchall()]
    except Exception as e:
        return {"status": "error", "message": f"Error listing expenses: {str(e)}"}


@mcp.tool()
async def summarize(start_date: str, end_date: str, category: Optional[str] = None):
    """Summarize expenses by category within an inclusive date range."""
    try:
        await init_db()
        async with aiosqlite.connect(DB_PATH) as c:
            query = """SELECT category, SUM(amount) AS total_amount, COUNT(*) AS count
                       FROM expenses
                       WHERE date BETWEEN ? AND ?"""
            params = [start_date, end_date]
            if category:
                query += " AND category = ?"
                params.append(category)
            query += " GROUP BY category ORDER BY total_amount DESC"
            cur = await c.execute(query, params)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in await cur.fetchall()]
    except Exception as e:
        return {"status": "error", "message": f"Error summarizing expenses: {str(e)}"}


if __name__ == "__main__":
    mcp.run()