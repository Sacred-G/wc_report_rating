import sqlite3

def check_tables():
    conn = sqlite3.connect('data/local.db')
    cursor = conn.cursor()
    
    # Get list of tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print("Tables in database:")
    for table in tables:
        table_name = table[0]
        print(f"\nTable: {table_name}")
        
        # Get row count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"Row count: {count}")
        
        # Get sample data
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 1")
        sample = cursor.fetchone()
        if sample:
            # Get column names
            columns = [description[0] for description in cursor.description]
            print("Sample row:")
            for col, val in zip(columns, sample):
                print(f"  {col}: {val}")
    
    conn.close()

if __name__ == "__main__":
    check_tables()
