import sqlite3
import pandas as pd
import os

def create_database():
    # Connect to SQLite database (creates it if it doesn't exist)
    db_path = 'data/local.db'
    conn = sqlite3.connect(db_path)
    
    # Read and execute the schema
    with open('data/sql/create_sqlite_schema.sql', 'r') as f:
        schema = f.read()
        conn.executescript(schema)
    
    # Import occupational adjustments
    df_adj = pd.read_csv('data/sql/occupational_adjustments_rows.csv')
    df_adj.to_sql('occupational_adjustments', conn, if_exists='replace', index=True, index_label='id')
    
    # Import occupations
    df_occ = pd.read_csv('data/sql/occupations_rows.csv')
    df_occ.to_sql('occupations', conn, if_exists='replace', index=True, index_label='id')
    
    # Import variants (first part)
    df_var1 = pd.read_csv('data/sql/variants_rows.csv')
    # Convert column names to lowercase for consistency
    df_var1.columns = [col.lower() for col in df_var1.columns]
    df_var1.to_sql('variants', conn, if_exists='replace', index=True, index_label='id')
    
    # Import variants_2 (second part)
    df_var2 = pd.read_csv('data/sql/variants_2_rows.csv')
    # Convert column names to lowercase for consistency
    df_var2.columns = [col.lower() for col in df_var2.columns]
    df_var2.to_sql('variants_2', conn, if_exists='replace', index=True, index_label='id')
    
    # Import age adjustment data
    df_age = pd.read_csv('data/sql/age_adjustment_temp.csv')
    df_age.to_sql('age_adjustment', conn, if_exists='replace', index=True, index_label='id')
    
    conn.commit()
    conn.close()
    
    print("Database created successfully!")

if __name__ == "__main__":
    create_database()
