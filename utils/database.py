import os
import csv
import sqlite3
from typing import Dict, Any, List, Optional, Tuple
from utils.config import config

def init_database():
    """Initialize SQLite database with tables and import data from CSV files"""
    conn = sqlite3.connect(config.database_path)
    cursor = conn.cursor()
    
    # Create tables
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS occupational_adjustments (
            id INTEGER PRIMARY KEY,
            rating_percent REAL,
            c REAL,
            d REAL,
            e REAL,
            f REAL,
            g REAL,
            h REAL,
            i REAL,
            j REAL
        );

        CREATE TABLE IF NOT EXISTS occupations (
            id INTEGER PRIMARY KEY,
            group_number INTEGER,
            occupation_title TEXT,
            industry TEXT
        );

        CREATE TABLE IF NOT EXISTS variants (
            id INTEGER PRIMARY KEY,
            body_part TEXT,
            impairment_code TEXT,
            group_110 TEXT,
            group_111 TEXT,
            group_112 TEXT,
            group_120 TEXT,
            group_210 TEXT,
            group_211 TEXT,
            group_212 TEXT,
            group_213 TEXT,
            group_214 TEXT,
            group_220 TEXT,
            group_221 TEXT,
            group_230 TEXT,
            group_240 TEXT,
            group_250 TEXT,
            group_251 TEXT,
            group_290 TEXT
        );

        CREATE TABLE IF NOT EXISTS variants_2 (
            id INTEGER PRIMARY KEY,
            body_part TEXT,
            impairment_code TEXT,
            group_310 TEXT,
            group_311 TEXT,
            group_320 TEXT,
            group_321 TEXT,
            group_322 TEXT,
            group_330 TEXT,
            group_331 TEXT,
            group_332 TEXT,
            group_340 TEXT,
            group_341 TEXT,
            group_350 TEXT,
            group_351 TEXT,
            group_360 TEXT,
            group_370 TEXT,
            group_380 TEXT,
            group_390 TEXT,
            group_420 TEXT,
            group_430 TEXT,
            group_460 TEXT,
            group_470 TEXT,
            group_480 TEXT,
            group_481 TEXT,
            group_482 TEXT,
            group_490 TEXT,
            group_491 TEXT,
            group_492 TEXT,
            group_493 TEXT,
            group_560 TEXT,
            group_590 TEXT
        );

        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            file_name TEXT,
            result_summary TEXT,
            final_pd_percent REAL,
            occupation TEXT,
            age INTEGER
        );

        CREATE TABLE IF NOT EXISTS age_adjustment (
            id INTEGER PRIMARY KEY,
            wpi_percent REAL,
            "21_and_under" REAL,
            "22_to_26" REAL,
            "27_to_31" REAL,
            "32_to_36" REAL,
            "37_to_41" REAL,
            "42_to_46" REAL,
            "47_to_51" REAL,
            "52_to_56" REAL,
            "57_to_61" REAL,
            "62_and_over" REAL
        );
    """)

    # Import data from CSV files if tables are empty
    def import_csv(table_name: str, csv_path: str) -> None:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        if cursor.fetchone()[0] == 0:  # Only import if table is empty
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    placeholders = ','.join(['?' for _ in row])
                    columns = ','.join(row.keys())
                    cursor.execute(
                        f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})",
                        list(row.values())
                    )

    # Import data from CSV files
    csv_files = {
        'occupational_adjustments': os.path.join(config.get("paths", "sql_dir"), 'occupational_adjustments_rows.csv'),
        'occupations': os.path.join(config.get("paths", "sql_dir"), 'occupations_rows.csv'),
        'variants': os.path.join(config.get("paths", "sql_dir"), 'variants_rows.csv'),
        'variants_2': os.path.join(config.get("paths", "sql_dir"), 'variants_2_rows.csv'),
        'age_adjustment': os.path.join(config.get("paths", "sql_dir"), 'age_adjustment_rows.csv')
    }

    for table, csv_path in csv_files.items():
        if os.path.exists(csv_path):
            import_csv(table, csv_path)

    conn.commit()
    conn.close()

def get_occupation_group(occupation: str) -> int:
    """Get occupation group number from database"""
    print(f"DATABASE: Looking up occupation group for '{occupation}'")
    # Check if the occupation is already in the format of a group number + variant
    # For example, "380H" should return 380
    if occupation and len(occupation) >= 3:
        # Check if the format is like "XXXL" where XXX is a number and L is a letter
        if occupation[:-1].isdigit() and occupation[-1].isalpha():
            return int(occupation[:-1])
    
    # Handle special cases first
    occupation_lower = occupation.lower()
    if 'stocker' in occupation_lower or 'sorter' in occupation_lower:
        return 360  # Same as packer group
    
    # Try to find in database
    conn = sqlite3.connect(config.database_path)
    cursor = conn.cursor()
    
    # Convert occupation to lowercase for case-insensitive matching
    occupation_lower = occupation.lower()
    
    # Split occupation into words and search for each word
    words = occupation_lower.split()
    
    # Try exact match first
    cursor.execute("SELECT group_number FROM occupations WHERE LOWER(occupation_title) LIKE ?", ('%' + occupation_lower + '%',))
    result = cursor.fetchone()
    
    if not result:
        # Try matching individual words
        for word in words:
            if len(word) > 2:  # Only search for words longer than 2 characters
                cursor.execute("SELECT group_number FROM occupations WHERE LOWER(occupation_title) LIKE ?", ('%' + word + '%',))
                result = cursor.fetchone()
                if result:
                    break
    
    conn.close()
    
    if not result:
        raise ValueError(f"Occupation '{occupation}' not found in 'occupations' table. Please check the occupation title or use a more general term.")
    return result[0]

def get_variant_for_impairment(group_num: int, impairment_code: str) -> Dict[str, Any]:
    """Get variant information with flexible impairment code matching."""
    print(f"DATABASE: Looking up variant for group {group_num} and impairment '{impairment_code}'")
    conn = sqlite3.connect(config.database_path)
    cursor = conn.cursor()
    table_name = "variants_2" if group_num >= 310 else "variants"
    
    # Map specific codes to general body parts for lookup
    code_to_body_part = {
        "SPINE-DRE-ROM": "SPINE",
        "PERIPH-SPINE": "SPINE",
        "PERIPH-UE": "ARM",
        "PERIPH-LE": "LEG",
        "ARM-AMPUT": "ARM",
        "ARM-GRIP/PINCH": "ARM",
        "SHOULDER-ROM": "SHOULDER",
        "ELBOW-ROM": "ELBOW",
        "WRIST-ROM": "WRIST",
        "LEG-AMPUT": "LEG"
    }
    
    # Convert specific codes to general body parts
    lookup_code = code_to_body_part.get(impairment_code, impairment_code)
    
    # Try to find a match
    cursor.execute(f"SELECT * FROM {table_name} WHERE body_part = ?", (lookup_code,))
    result = cursor.fetchone()
    
    if not result:
        # If no match found, try a more generic approach
        if any(term in lookup_code.lower() for term in ["arm", "hand", "wrist", "elbow", "shoulder"]):
            cursor.execute(f"SELECT * FROM {table_name} WHERE body_part = ?", ("ARM",))
            result = cursor.fetchone()
        elif any(term in lookup_code.lower() for term in ["leg", "knee", "ankle", "foot"]):
            cursor.execute(f"SELECT * FROM {table_name} WHERE body_part = ?", ("LEG",))
            result = cursor.fetchone()
    
    conn.close()
    
    if not result:
        # Return a default variant if no match found
        return {"variant_label": "G"}
    
    column_names = [description[0] for description in cursor.description]
    variant_data = dict(zip(column_names, result))
    
    # Find the variant for the specific group number
    group_key = f"group_{group_num}"
    variant_label = variant_data.get(group_key)
    if not variant_label:
        # Try to find a match with a more generic approach
        if any(term in lookup_code.lower() for term in ["arm", "hand", "wrist", "elbow", "shoulder"]):
            cursor.execute(f"SELECT * FROM {table_name} WHERE body_part = ?", ("ARM",))
            result = cursor.fetchone()
            if result:
                variant_data = dict(zip(column_names, result))
                variant_label = variant_data.get(group_key)
        elif any(term in lookup_code.lower() for term in ["leg", "knee", "ankle", "foot"]):
            cursor.execute(f"SELECT * FROM {table_name} WHERE body_part = ?", ("LEG",))
            result = cursor.fetchone()
            if result:
                variant_data = dict(zip(column_names, result))
                variant_label = variant_data.get(group_key)
    
    if not variant_label:
        raise ValueError(f"No variant found for impairment code {impairment_code} and group {group_num}")
        
    return {"variant_label": variant_label.upper()}

def get_occupational_adjusted_wpi(group_num: int, variant_label: str, base_wpi: float) -> float:
    """Get occupational adjusted WPI value from the table."""
    print(f"DATABASE: Getting occupational adjustment for group {group_num}, variant {variant_label}, WPI {base_wpi}")
    conn = sqlite3.connect(config.database_path)
    cursor = conn.cursor()
    
    # Find the closest rating_percent that's less than or equal to our adjusted WPI
    cursor.execute("SELECT * FROM occupational_adjustments WHERE rating_percent <= ? ORDER BY rating_percent DESC LIMIT 1", (base_wpi,))
    result = cursor.fetchone()
    
    if not result:
        # If no match found, use the lowest rating
        cursor.execute("SELECT * FROM occupational_adjustments ORDER BY rating_percent ASC LIMIT 1")
        result = cursor.fetchone()
        if not result:
            conn.close()
            raise ValueError(f"No occupational adjustment found for WPI {base_wpi} and variant {variant_label}")
    
    column_names = [description[0].lower() for description in cursor.description]
    
    # Convert variant label to column name (c, d, e, f, g, h, i, j)
    variant_label = variant_label.lower()
    if variant_label not in column_names:
        raise ValueError(f"Invalid variant label: {variant_label}")
    adjustment_column = variant_label
    
    try:
        column_index = column_names.index(adjustment_column)
        # Get the actual value from the table - this IS the adjusted WPI, not a multiplier
        adjusted_wpi = float(result[column_index])
        conn.close()
        return adjusted_wpi
    except (ValueError, IndexError):
        conn.close()
        return base_wpi

def get_age_adjusted_wpi(age: int, raw_wpi: float) -> float:
    """Get age adjusted WPI value from the table."""
    print(f"DATABASE: Getting age adjustment for age {age}, WPI {raw_wpi}")
    conn = sqlite3.connect(config.database_path)
    cursor = conn.cursor()
    
    # Find the closest wpi_percent that's greater than or equal to our raw_wpi
    cursor.execute("SELECT * FROM age_adjustment WHERE wpi_percent <= ? ORDER BY wpi_percent DESC LIMIT 1", (raw_wpi,))
    result = cursor.fetchone()
    
    if not result:
        # If no match found, use the lowest WPI
        cursor.execute("SELECT * FROM age_adjustment ORDER BY wpi_percent ASC LIMIT 1")
        result = cursor.fetchone()
        if not result:
            conn.close()
            raise ValueError("No data found in age adjustment table.")
    
    column_names = [description[0] for description in cursor.description]
    age_ranges = {
        (0, 22): "21_and_under",
        (22, 27): "22_to_26",
        (27, 32): "27_to_31",
        (32, 37): "32_to_36",
        (37, 42): "37_to_41",
        (42, 47): "42_to_46",
        (47, 52): "47_to_51",
        (52, 57): "52_to_56",
        (57, 62): "57_to_61",
        (62, 150): "62_and_over"
    }
    
    age_column = next((col for (start, end), col in age_ranges.items() if start <= age < end), None)
    if not age_column:
        conn.close()
        raise ValueError(f"No age bracket found for age {age}")
    
    try:
        # Get the actual value from the table - this IS the adjusted WPI
        age_adjusted_wpi = float(result[column_names.index(age_column)])
        conn.close()
        return age_adjusted_wpi
    except (ValueError, IndexError) as e:
        conn.close()
        raise ValueError(f"Error applying age adjustment: {str(e)}")
