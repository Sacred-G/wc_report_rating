import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd
from utils.config import config

def main():
    """View processing history"""
    st.set_page_config(page_title="Processing History", page_icon="📋")
    
    st.sidebar.title("Navigation")
    st.sidebar.info("View your report processing history here.")
    
    st.title("📋 Processing History")
    st.caption("View and manage your previous report processing results")
    
    conn = None
    try:
        # Connect to database
        conn = sqlite3.connect(config.database_path)
        
        # Get history records
        query = """
        SELECT 
            timestamp,
            file_name,
            result_summary,
            final_pd_percent,
            occupation,
            age
        FROM history 
        ORDER BY timestamp DESC
        """
        
        df = pd.read_sql_query(query, conn)
        
        if df.empty:
            st.info("No processing history found. Process some reports to see them here!")
        else:
            # Format timestamp
            df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
            
            # Display records in expandable containers
            for _, row in df.iterrows():
                with st.expander(f"📄 {row['file_name']} - {row['timestamp']}", expanded=False):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**File Name:**", row['file_name'])
                        st.write("**Processed On:**", row['timestamp'])
                        st.write("**Final PD %:**", f"{row['final_pd_percent']:.1f}%" if pd.notna(row['final_pd_percent']) else "N/A")
                    
                    with col2:
                        st.write("**Occupation:**", row['occupation'] if pd.notna(row['occupation']) else "N/A")
                        st.write("**Age:**", int(row['age']) if pd.notna(row['age']) else "N/A")
                    
                    st.write("**Summary:**")
                    st.write(row['result_summary'] if pd.notna(row['result_summary']) else "No summary available")
        
            # Add clear history button
            if st.button("Clear History"):
                conn.execute("DELETE FROM history")
                conn.commit()
                st.success("History cleared successfully!")
                st.rerun()
            
    except sqlite3.Error as e:
        st.error(f"Database error: {str(e)}")
    except Exception as e:
        st.error(f"Error accessing history: {str(e)}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    main()
