import os
from utils.config import config
from utils.database import init_database

def check_database():
    """Check if the database file exists and initialize it if it doesn't."""
    db_path = config.database_path
    print(f"Database path: {db_path}")
    
    # Check if the database file exists
    if os.path.exists(db_path):
        print(f"Database file exists at {db_path}")
        print(f"File size: {os.path.getsize(db_path) / 1024:.2f} KB")
    else:
        print(f"Database file does not exist at {db_path}")
        print("Initializing database...")
        init_database()
        
        if os.path.exists(db_path):
            print(f"Database initialized successfully at {db_path}")
            print(f"File size: {os.path.getsize(db_path) / 1024:.2f} KB")
        else:
            print(f"Failed to initialize database at {db_path}")

if __name__ == "__main__":
    check_database()
