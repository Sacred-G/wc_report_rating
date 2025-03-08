import streamlit as st
import pandas as pd
from datetime import datetime
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import the database functions and rating calculator
from utils.database import (
    init_database,
    get_occupation_group,
    get_variant_for_impairment,
    get_occupational_adjusted_wpi,
    get_age_adjusted_wpi
)
from rating_calculator import calculate_rating
from utils.config import config

def main():
    st.set_page_config(page_title="Database Usage Verification", page_icon="🔍", layout="wide")
    st.title("Database Usage Verification")
    st.write("This app demonstrates that the database is being used during the rating calculation process.")
    
    # Initialize database
    if 'db_initialized' not in st.session_state:
        try:
            init_database()
            st.session_state.db_initialized = True
            st.success("Database initialized successfully.")
        except Exception as e:
            st.error(f"Error initializing database: {str(e)}")
    
    # Display database path
    st.subheader("Database Configuration")
    st.write(f"Database Path: `{config.database_path}`")
    
    # Check if database file exists
    if os.path.exists(config.database_path):
        st.success(f"Database file exists at the specified path.")
        # Get database file size
        db_size = os.path.getsize(config.database_path) / (1024 * 1024)  # Convert to MB
        st.write(f"Database Size: {db_size:.2f} MB")
    else:
        st.error(f"Database file does not exist at the specified path.")
    
    # Create two columns
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Rating Calculator")
        
        # Input fields
        occupation = st.text_input("Occupation", value="Carpenter")
        bodypart = st.text_input("Body Part", value="SPINE")
        
        # Date picker for injury date
        injury_date = st.date_input("Date of Injury", value=datetime.now())
        age_injury = injury_date.strftime("%Y-%m-%d")
        
        # Numeric inputs
        wpi = st.number_input("WPI (%)", min_value=0.0, max_value=100.0, value=10.0, step=0.5)
        pain = st.number_input("Pain Add-on", min_value=0.0, max_value=3.0, value=1.0, step=0.5)
        
        # Calculate button
        if st.button("Calculate Rating"):
            # Create a placeholder for database logs
            log_placeholder = st.empty()
            
            # Capture print statements
            import io
            import sys
            old_stdout = sys.stdout
            new_stdout = io.StringIO()
            sys.stdout = new_stdout
            
            try:
                # Calculate rating
                result = calculate_rating(
                    occupation=occupation,
                    bodypart=bodypart,
                    age_injury=age_injury,
                    wpi=wpi,
                    pain=pain
                )
                
                # Get captured output
                sys.stdout = old_stdout
                logs = new_stdout.getvalue()
                
                # Display logs
                log_placeholder.code(logs, language="")
                
                # Store result in session state
                st.session_state.result = result
                
                # Display success message
                if result['status'] == 'success':
                    st.success(f"Rating calculation successful! Final Rating: {result['final_value']}%")
                else:
                    st.error(f"Error: {result['message']}")
                
            except Exception as e:
                sys.stdout = old_stdout
                st.error(f"Error calculating rating: {str(e)}")
    
    with col2:
        st.subheader("Results")
        
        # Display results if available
        if 'result' in st.session_state and st.session_state.result['status'] == 'success':
            result = st.session_state.result
            
            # Display final rating
            st.metric("Final Rating", f"{result['final_value']}%")
            
            # Display details
            st.write("### Calculation Details")
            for detail in result['details']:
                with st.expander(f"Body Part: {detail['body_part']}"):
                    st.write(f"Group Number: {detail['group_number']}")
                    st.write(f"Variant: {detail['variant']}")
                    st.write(f"Base Value: {detail['base_value']}")
                    st.write(f"Adjusted Value: {detail['adjusted_value']}")
                    st.write(f"Occupational Adjusted WPI: {detail['occupant_adjusted_wpi']}")
                    st.write(f"Age: {detail['age']}")
                    st.write(f"Final Value: {detail['final_value']}")
            
            # Display database verification
            st.write("### Database Usage Verification")
            st.info("""
            The logs in the left column show that the database is being used during the rating calculation process.
            Look for lines starting with "DATABASE:" which indicate database function calls.
            
            The following database functions are called during the rating calculation:
            1. `get_occupation_group` - Looks up the occupation group number
            2. `get_variant_for_impairment` - Determines the variant label for the impairment
            3. `get_occupational_adjusted_wpi` - Applies occupational adjustments
            4. `get_age_adjusted_wpi` - Applies age adjustments
            """)

if __name__ == "__main__":
    main()
