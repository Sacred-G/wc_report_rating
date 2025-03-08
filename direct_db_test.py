import os
import sqlite3
from utils.config import config
from utils.database import (
    init_database,
    get_occupation_group,
    get_variant_for_impairment,
    get_occupational_adjusted_wpi,
    get_age_adjusted_wpi
)

def direct_db_test():
    """Directly test database functions with explicit print statements."""
    print("Starting direct database test...")
    
    # Get database path
    db_path = config.database_path
    print(f"Database path: {db_path}")
    
    # Check if database exists
    if not os.path.exists(db_path):
        print(f"Database file does not exist. Initializing...")
        init_database()
        print("Database initialized.")
    else:
        print(f"Database file exists. Size: {os.path.getsize(db_path) / 1024:.2f} KB")
    
    # Connect to database and check tables
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"Database contains {len(tables)} tables:")
        for table in tables:
            print(f"  - {table[0]}")
        
        # Check if tables have data
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
            count = cursor.fetchone()[0]
            print(f"  Table {table[0]} has {count} rows")
        
        conn.close()
        print("Database connection closed.")
    except Exception as e:
        print(f"Error connecting to database: {str(e)}")
    
    # Test database functions
    print("\nTesting database functions...")
    
    try:
        # Test get_occupation_group
        occupation = "Carpenter"
        print(f"\nTesting get_occupation_group with occupation '{occupation}'")
        group_number = get_occupation_group(occupation)
        print(f"Result: Group number = {group_number}")
        
        # Test get_variant_for_impairment
        impairment_code = "SPINE"
        print(f"\nTesting get_variant_for_impairment with group {group_number} and impairment '{impairment_code}'")
        variant_info = get_variant_for_impairment(group_number, impairment_code)
        print(f"Result: Variant = {variant_info}")
        
        # Test get_occupational_adjusted_wpi
        base_wpi = 15.0
        variant_label = variant_info.get('variant_label', 'G')
        print(f"\nTesting get_occupational_adjusted_wpi with group {group_number}, variant {variant_label}, and WPI {base_wpi}")
        occupant_adjusted_wpi = get_occupational_adjusted_wpi(group_number, variant_label, base_wpi)
        print(f"Result: Occupational adjusted WPI = {occupant_adjusted_wpi}")
        
        # Test get_age_adjusted_wpi
        age = 45
        print(f"\nTesting get_age_adjusted_wpi with age {age} and WPI {occupant_adjusted_wpi}")
        age_adjusted_wpi = get_age_adjusted_wpi(age, occupant_adjusted_wpi)
        print(f"Result: Age adjusted WPI = {age_adjusted_wpi}")
        
        print("\nAll database functions tested successfully!")
    except Exception as e:
        print(f"Error testing database functions: {str(e)}")
    
    print("\nDirect database test complete.")

if __name__ == "__main__":
    direct_db_test()
