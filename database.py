import sqlite3

# Connect to the SQLite database
conn = sqlite3.connect('shares_data.db')
cursor = conn.cursor()

# Create the shares table with the new columns
cursor.execute('''
    CREATE TABLE IF NOT EXISTS shares (
        ticker TEXT PRIMARY KEY,
        isin TEXT,
        outstanding_shares INTEGER,
        last_updated DATE,
        details TEXT,
        transactions TEXT,
        actions TEXT
    )
''')

# Commit the changes and close the connection
conn.commit()
conn.close()