import sqlite3

DB_NAME = "tutoring.db"

def setup_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Create inquiries table cleanly with no hard-coded mock rows
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inquiries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parent_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            branch TEXT NOT NULL,
            child_age INTEGER NOT NULL,
            question TEXT NOT NULL,
            category TEXT NOT NULL,
            draft_reply TEXT NOT NULL,
            needs_human INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    setup_database()