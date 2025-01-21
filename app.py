import os
import streamlit as st
import sqlite3
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

def main():
    """Main application entry point."""
    # Set up page config first
    st.set_page_config(
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
    
    # Initialize database if needed
    if not os.path.exists(os.path.dirname(os.environ.get('DATABASE_PATH', 'data/local.db'))):
        os.makedirs(os.path.dirname(os.environ.get('DATABASE_PATH', 'data/local.db')), exist_ok=True)
        init_database()

    # Render upload section
    mode, uploaded_files, combine_reports = render_upload_section()

    # Get manual inputs
    manual_data = render_manual_inputs()
    
    # Get display mode preference
    display_mode = render_display_mode_selector()
    
    # Add clear button
    if st.button("Clear Results"):
        if 'results' in st.session_state:
            del st.session_state['results']
        if 'combined_result' in st.session_state:
            del st.session_state['combined_result']
        st.rerun()
    
    # Display results if they exist in session state
    if combine_reports and 'combined_result' in st.session_state:
        st.subheader("Combined Results")
        render_results(st.session_state.combined_result, display_mode)
    elif not combine_reports and 'results' in st.session_state:
        for i, result in enumerate(st.session_state.results):
            with st.expander(f"Report {i + 1} Results", expanded=True):
                render_results(result, display_mode)
    
    # Process reports if files are uploaded
    if uploaded_files:
        if st.button("Process Reports"):
            try:
                with st.spinner("Processing..."):
                    # Process all files together
                    st.info("Processing files...")
                    result = process_medical_reports(
                        uploaded_files,
                        manual_data,
                        "detailed" if mode == "Detailed Summary" else "default"
                    )
                    
                    # Store result
                    if combine_reports:
                        st.session_state.combined_result = result
                    else:
                        st.session_state.results = [result]
                    
                    # Save to history
                    conn = sqlite3.connect(os.environ.get('DATABASE_PATH', 'data/local.db'))
                    try:
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
                    except Exception as e:
                        st.error(f"Error saving to history: {str(e)}")
                    finally:
                        conn.close()
                    
                    st.success("Processing Complete!")
                    st.rerun()
                    
            except Exception as e:
                st.error(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
