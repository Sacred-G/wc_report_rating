import streamlit as st

def about():
    """About page"""
    st.title("About QME Report Processor")
    st.write("""
    This application helps process QME (Qualified Medical Evaluator) reports by:
    - Extracting WPI ratings and calculating adjustments
    - Generating detailed medical summaries with references
    - Processing dental ratings from separate reports
    - Applying age and occupational adjustments
    - Combining multiple ratings using the CVC method
    
    ### Features
    - Automatic text extraction from PDF reports
    - Intelligent data parsing using OpenAI
    - Accurate rating calculations
    - Detailed summaries with page/line references
    - Support for dental ratings
    - History tracking
    - CSV data management
    
    ### Version
    Current Version: 1.0.0
    
    ### Support
    For support or feature requests, please contact support@qmeprocessor.com
    """)
