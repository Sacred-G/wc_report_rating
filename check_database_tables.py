import sqlite3
import os
import pandas as pd
import streamlit as st
from utils.config import config
from utils.database import init_database

def check_database_tables():
    """Check the database tables and their contents."""
    # Initialize database if needed
    if not os.path.exists(config.database_path):
        print(f"Database file not found at {config.database_path}. Initializing database...")
        init_database()
        print("Database initialized.")
    
    # Connect to the database
    conn = sqlite3.connect(config.database_path)
    cursor = conn.cursor()
    
    # Get list of tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print(f"\n===== DATABASE TABLES =====\n")
    print(f"Database path: {config.database_path}")
    print(f"Found {len(tables)} tables:")
    
    # Check each table
    for table in tables:
        table_name = table[0]
        print(f"\n----- Table: {table_name} -----")
        
        # Get column names
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        print(f"Columns: {', '.join(col[1] for col in columns)}")
        
        # Get row count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        row_count = cursor.fetchone()[0]
        print(f"Row count: {row_count}")
        
        # Show sample data (first 5 rows)
        if row_count > 0:
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
            rows = cursor.fetchall()
            print(f"Sample data (first 5 rows):")
            for row in rows:
                print(f"  {row}")
    
    # Close connection
    conn.close()
    print("\n===== DATABASE CHECK COMPLETE =====\n")

def streamlit_check_database():
    """Streamlit app to check database tables."""
    st.set_page_config(page_title="Database Tables Check", page_icon="📊", layout="wide")
    st.title("Database Tables Check")
    st.write("This app checks the database tables and their contents.")
    
    # Initialize database if needed
    if not os.path.exists(config.database_path):
        st.warning(f"Database file not found at {config.database_path}. Initializing database...")
        init_database()
        st.success("Database initialized.")
    
    # Display database path
    st.subheader("Database Configuration")
    st.write(f"Database Path: `{config.database_path}`")
    
    # Connect to the database
    conn = sqlite3.connect(config.database_path)
    
    # Get list of tables
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    st.write(f"Found {len(tables)} tables:")
    
    # Create tabs for each table
    tabs = st.tabs([table[0] for table in tables])
    
    # Display each table in a tab
    for i, table_name in enumerate([table[0] for table in tables]):
        with tabs[i]:
            # Get column names
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            st.write(f"**Columns:** {', '.join(col[1] for col in columns)}")
            
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            st.write(f"**Row count:** {row_count}")
            
            # Show sample data
            if row_count > 0:
                # Load data into a pandas DataFrame
                df = pd.read_sql_query(f"SELECT * FROM {table_name} LIMIT 100", conn)
                st.write("**Sample data (up to 100 rows):**")
                st.dataframe(df)
                
                # Add download button
                csv = df.to_csv(index=False)
                st.download_button(
                    label=f"Download {table_name} data as CSV",
                    data=csv,
                    file_name=f"{table_name}.csv",
                    mime="text/csv"
                )
    
    # Close connection
    conn.close()
    
    st.success("Database check complete!")
    st.info("""
    The tables shown above are used in the rating calculation process:
    
    - **occupations**: Contains occupation titles and their group numbers
    - **variants** and **variants_2**: Map body parts and impairment codes to variants
    - **occupational_adjustments**: Contains adjustment factors for different occupation groups
    - **age_adjustment**: Contains age adjustment factors
    - **history**: Stores history of previous calculations
    
    These tables are accessed by the database functions during the rating calculation process.
    """)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--streamlit":
        # Run Streamlit app
        streamlit_check_database()
    else:
        # Run command-line version
        check_database_tables()
