import os
import streamlit as st
import sqlite3
import logging
import traceback
from datetime import datetime
from dotenv import load_dotenv
from utils.database import init_database
from utils.auth import check_password
from utils.ui import (
    setup_page,
    render_upload_section,
    render_manual_inputs,
    render_display_mode_selector,
    render_results
)
from utils.styling import get_card_css
from utils.report_processor import process_medical_reports
from utils.config import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs', 'app.log'), mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

def main():
    """Main application entry point."""
    try:
        # Set up page config first
        st.set_page_config(
            page_title="WC Rating Assistant",
            page_icon="📋",
            layout="wide",
            initial_sidebar_state="expanded",
            menu_items={
                'About': 'Workers Compensation Rating Calculator',
                'Get Help': None,
                'Report a bug': None
            }
        )
        
        # Check password before proceeding
        if not check_password():
            st.stop()
        
        # Setup remaining page elements
        st.markdown(get_card_css(), unsafe_allow_html=True)
        st.title("PDRS Workers' Comp Rating Assistant")
        
        # Ensure logs directory exists
        os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs'), exist_ok=True)
        
        # Initialize database if needed
        db_path = os.environ.get('DATABASE_PATH', 'data/local.db')
        if not os.path.exists(os.path.dirname(db_path)):
            try:
                os.makedirs(os.path.dirname(db_path), exist_ok=True)
                init_database()
                logger.info("Database initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize database: {str(e)}")
                st.error(f"Database initialization error: {str(e)}")

        # Render upload section
        mode, uploaded_files, combine_reports = render_upload_section()

        # Get manual inputs
        manual_data = render_manual_inputs()
        
        # Get display mode preference
        display_mode = render_display_mode_selector()
        
        # Add clear button with confirmation
        if st.button("Clear Results"):
            clear_results()
        
        # Display results if they exist in session state
        display_existing_results(combine_reports, display_mode)
        
        # Process reports if files are uploaded
        if uploaded_files:
            if st.button("Process Reports"):
                process_uploaded_reports(uploaded_files, manual_data, mode, combine_reports)

    except Exception as e:
        logger.error(f"Unhandled exception in main: {str(e)}", exc_info=True)
        st.error(f"An unexpected error occurred: {str(e)}")
        st.error("Please try refreshing the page or contact support if the issue persists.")
        
        # Add technical details in an expander for debugging
        with st.expander("Technical Details", expanded=False):
            st.code(traceback.format_exc())

def clear_results():
    """Clear all results from session state with confirmation."""
    if 'results' in st.session_state or 'combined_result' in st.session_state:
        if 'results' in st.session_state:
            del st.session_state['results']
        if 'combined_result' in st.session_state:
            del st.session_state['combined_result']
        st.success("Results cleared successfully")
        st.rerun()
    else:
        st.info("No results to clear")

def display_existing_results(combine_reports, display_mode):
    """Display existing results from session state."""
    if combine_reports and 'combined_result' in st.session_state:
        st.subheader("Combined Results")
        render_results(st.session_state.combined_result, display_mode)
    elif not combine_reports and 'results' in st.session_state:
        for i, result in enumerate(st.session_state.results):
            with st.expander(f"Report {i + 1} Results", expanded=True):
                render_results(result, display_mode)

def process_uploaded_reports(uploaded_files, manual_data, mode, combine_reports):
    """Process uploaded reports and save results."""
    try:
        with st.spinner("Processing..."):
            # Log processing start
            file_names = ", ".join(f.name for f in uploaded_files)
            logger.info(f"Processing files: {file_names}")
            
            # Reset global variables in report_processor to ensure fresh processing
            import utils.report_processor
            utils.report_processor._assistant = None
            utils.report_processor._vector_store = None
            
            # Also reset in process_report if it's being used
            import process_report
            process_report._assistant = None
            process_report._vector_store = None
            
            # Process all files together
            st.info(f"Processing {len(uploaded_files)} file(s)...")
            
            # Add progress bar
            progress_bar = st.progress(0)
            
            # Process reports
            result = process_medical_reports(
                uploaded_files,
                manual_data,
                "detailed" if mode == "Detailed Summary" else "default",
                progress_callback=lambda p: progress_bar.progress(p)
            )
            
            # Store result
            if combine_reports:
                st.session_state.combined_result = result
                logger.info("Combined result stored in session state")
            else:
                st.session_state.results = [result]
                logger.info("Individual result stored in session state")
            
            # Save to history
            save_to_history(result, uploaded_files, manual_data)
            
            # Complete progress
            progress_bar.progress(100)
            st.success("Processing Complete!")
            
            # Add timestamp
            st.info(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            st.rerun()
                
    except Exception as e:
        logger.error(f"Error processing reports: {str(e)}", exc_info=True)
        st.error(f"Error processing reports: {str(e)}")
        
        # Add technical details in an expander for debugging
        with st.expander("Technical Details", expanded=False):
            st.code(traceback.format_exc())

def save_to_history(result, uploaded_files, manual_data):
    """Save processing results to history database."""
    try:
        conn = sqlite3.connect(os.environ.get('DATABASE_PATH', 'data/local.db'))
        
        # Extract relevant data
        summary = result if isinstance(result, str) else str(result)
        final_pd = result.get('no_apportionment', {}).get('final_pd_percent', None) if isinstance(result, dict) else None
        occupation = manual_data.get('occupation', None)
        age = manual_data.get('age', None)
        
        # Save combined result to history
        file_names = ", ".join(f.name for f in uploaded_files)
        conn.execute("""
            INSERT INTO history 
            (file_name, result_summary, final_pd_percent, occupation, age)
            VALUES (?, ?, ?, ?, ?)
        """, (file_names, summary, final_pd, occupation, age))
        conn.commit()
        logger.info(f"Results saved to history for files: {file_names}")
    except Exception as e:
        logger.error(f"Error saving to history: {str(e)}", exc_info=True)
        st.warning(f"Could not save to history: {str(e)}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    main()
