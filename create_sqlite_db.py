import sqlite3
import pandas as pd
import os

def create_database():
    # Connect to SQLite database (creates it if it doesn't exist)
    db_path = 'wcpython/data/local.db'
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    
    # Create tables
    conn.executescript("""
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
    
    # Import occupational adjustments
    df_adj = pd.read_csv('wcpython/data/sql/occupational_adjustments_rows.csv')
    df_adj.to_sql('occupational_adjustments', conn, if_exists='replace', index=True, index_label='id')
    
    # Import occupations
    df_occ = pd.read_csv('wcpython/data/sql/occupations_rows.csv')
    df_occ.to_sql('occupations', conn, if_exists='replace', index=True, index_label='id')
    
    # Import variants (first part)
    df_var1 = pd.read_csv('wcpython/data/sql/variants_rows.csv')
    # Convert column names to lowercase for consistency
    df_var1.columns = [col.lower() for col in df_var1.columns]
    df_var1.to_sql('variants', conn, if_exists='replace', index=True, index_label='id')
    
    # Import variants_2 (second part)
    df_var2 = pd.read_csv('wcpython/data/sql/variants_2_rows.csv')
    # Convert column names to lowercase for consistency
    df_var2.columns = [col.lower() for col in df_var2.columns]
    df_var2.to_sql('variants_2', conn, if_exists='replace', index=True, index_label='id')
    
    # Import age adjustment data
    df_age = pd.read_csv('wcpython/data/sql/age_adjustment_rows.csv')
    df_age.to_sql('age_adjustment', conn, if_exists='replace', index=True, index_label='id')
    
    conn.commit()
    conn.close()
    
    print("Database created successfully!")

if __name__ == "__main__":
    create_database()
