import sqlite3
import os

# Check where the database is (sometimes it's in an 'instance' folder)
db_path = 'database.db'
if not os.path.exists(db_path) and os.path.exists('instance/database.db'):
    db_path = 'instance/database.db'

print(f"Connecting to database at: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Add the missing 'ticker_text' column
    try:
        cursor.execute("ALTER TABLE notice ADD COLUMN ticker_text TEXT")
        print("✅ Added 'ticker_text' column.")
    except sqlite3.OperationalError:
        print("ℹ️ 'ticker_text' column already exists.")

    # 2. Add the missing 'qr_code_path' column (likely missing too)
    try:
        cursor.execute("ALTER TABLE notice ADD COLUMN qr_code_path TEXT")
        print("✅ Added 'qr_code_path' column.")
    except sqlite3.OperationalError:
        print("ℹ️ 'qr_code_path' column already exists.")

    # 3. Create the SystemState table if missing
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_state (
                id INTEGER PRIMARY KEY,
                last_updated DATETIME
            )
        """)
        print("✅ Checked/Created 'system_state' table.")
    except Exception as e:
        print(f"Error checking system_state: {e}")

    conn.commit()
    conn.close()
    print("\nSUCCESS: Database updated. You can now run app.py")

except Exception as e:
    print(f"\nCRITICAL ERROR: Could not connect to database. Make sure 'database.db' exists.\nError: {e}")