from fastmcp import FastMCP
import os
import aiosqlite  # Changed: sqlite3 → aiosqlite
import tempfile
# Use temporary directory which should be writable
TEMP_DIR = tempfile.gettempdir()
DB_PATH = os.path.join(TEMP_DIR, "expenses.db")
CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "categories.json")

print(f"Database path: {DB_PATH}")

mcp = FastMCP("ExpenseTracker")

def init_db():  # Keep as sync for initialization
    try:
        # Use synchronous sqlite3 just for initialization
        import sqlite3
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
            # Test write access
            c.execute("INSERT OR IGNORE INTO expenses(date, amount, category) VALUES ('2000-01-01', 0, 'test')")
            c.execute("DELETE FROM expenses WHERE category = 'test'")
            print("Database initialized successfully with write access")
    except Exception as e:
        print(f"Database initialization error: {e}")
        raise

# Initialize database synchronously at module load
init_db()

from typing import Optional

@mcp.tool()
async def add_expense(
    date: str,
    amount: float,
    category: str,
    subcategory: str = "",
    note: str = ""
):
    """Add a new expense entry to the database."""
    try:
        async with aiosqlite.connect(DB_PATH) as c:
            cur = await c.execute(
                "INSERT INTO expenses(date, amount, category, subcategory, note) VALUES (?,?,?,?,?)",
                (date, amount, category, subcategory, note)
            )
            expense_id = cur.lastrowid
            await c.commit()

            return {
                "status": "success",
                "id": expense_id,
                "message": "Expense added successfully"
            }

    except Exception as e:
        if "readonly" in str(e).lower():
            return {
                "status": "error",
                "message": "Database is in read-only mode. Check file permissions."
            }

        return {
            "status": "error",
            "message": f"Database error: {str(e)}"
        }


@mcp.tool()
async def list_expenses(
    start_date: str,
    end_date: str
):
    """List expense entries within an inclusive date range."""
    try:
        async with aiosqlite.connect(DB_PATH) as c:
            cur = await c.execute(
                """
                SELECT id, date, amount, category, subcategory, note
                FROM expenses
                WHERE date BETWEEN ? AND ?
                ORDER BY date DESC, id DESC
                """,
                (start_date, end_date)
            )

            cols = [d[0] for d in cur.description]

            return [
                dict(zip(cols, r))
                for r in await cur.fetchall()
            ]

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error listing expenses: {str(e)}"
        }


@mcp.tool()
async def summarize(
    start_date: str,
    end_date: str,
    category: Optional[str] = None
):
    """Summarize expenses by category within an inclusive date range."""
    try:
        async with aiosqlite.connect(DB_PATH) as c:
            query = """
                SELECT category,
                       SUM(amount) AS total_amount,
                       COUNT(*) AS count
                FROM expenses
                WHERE date BETWEEN ? AND ?
            """

            params = [start_date, end_date]

            if category:
                query += " AND category = ?"
                params.append(category)

            query += " GROUP BY category ORDER BY total_amount DESC"

            cur = await c.execute(query, params)

            cols = [d[0] for d in cur.description]

            return [
                dict(zip(cols, r))
                for r in await cur.fetchall()
            ]

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error summarizing expenses: {str(e)}"
        }

# Start the server
if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
    # mcp.run()