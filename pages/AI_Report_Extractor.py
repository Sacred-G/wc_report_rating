import streamlit as st
import pandas as pd
from datetime import datetime
import os
import json
from ai_report_extractor import (
    extract_and_structure_report,
    format_for_rating_calculator
)
from rating_calculator import calculate_rating
from utils.ui import render_results
from utils.styling import get_card_css
from utils.database import init_database

# Custom CSS for better readability
def get_custom_css():
    return """
    <style>
    .impairment-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
        border-left: 5px solid #4e8cff;
    }
    .impairment-title {
        font-size: 18px;
        font-weight: bold;
        margin-bottom: 10px;
        color: #333;
    }
    .impairment-detail {
        margin-bottom: 5px;
        display: flex;
    }
    .detail-label {
        font-weight: bold;
        min-width: 200px;
        color: #555;
    }
    .detail-value {
        color: #000;
    }
    .section-header {
        background-color: #4e8cff;
        color: white;
        padding: 10px 15px;
        border-radius: 5px;
        margin: 20px 0 15px 0;
        font-size: 18px;
    }
    .info-box {
        background-color: #e8f4f8;
        border-radius: 5px;
        padding: 15px;
        margin-bottom: 20px;
        border-left: 5px solid #4e8cff;
    }
    .calculation-result {
        font-size: 24px;
        font-weight: bold;
        color: #333;
        margin: 15px 0;
    }
    .json-preview {
        background-color: #f5f5f5;
        border-radius: 5px;
        padding: 10px;
        font-family: monospace;
        white-space: pre-wrap;
        max-height: 300px;
        overflow-y: auto;
    }
    </style>
    """

# Initialize database
if 'db_initialized' not in st.session_state:
    try:
        init_database()
        st.session_state.db_initialized = True
    except Exception as e:
        st.error(f"Error initializing database: {str(e)}")

def main():
    st.set_page_config(page_title="AI Report Extractor", page_icon="🧠", layout="wide")
    st.markdown(get_card_css(), unsafe_allow_html=True)
    st.markdown(get_custom_css(), unsafe_allow_html=True)
    
    st.title("AI Report Extractor")
    
    # Info box with description
    st.markdown("""
    <div class="info-box">
        <h3>How It Works</h3>
        <p>This tool uses AI to extract information from medical reports and calculate ratings using the database.</p>
        <ol>
            <li><strong>Extract Information:</strong> AI analyzes the report to extract patient information, occupation, and impairments</li>
            <li><strong>Verify with Database:</strong> The extracted information is verified using the database to calculate accurate ratings</li>
            <li><strong>Calculate Rating:</strong> The verified information is used to calculate the final rating</li>
        </ol>
    </div>
    """, unsafe_allow_html=True)
    
    # Create two columns for layout
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # File upload section
        st.markdown('<div class="section-header">Upload Medical Reports</div>', unsafe_allow_html=True)
        uploaded_files = st.file_uploader("Select PDF files", type=["pdf"], accept_multiple_files=True)
        
        if uploaded_files:
            st.write(f"Uploaded {len(uploaded_files)} file(s):")
            for i, file in enumerate(uploaded_files):
                st.write(f"{i+1}. **{file.name}**")
            
            # File selection
            if len(uploaded_files) > 1:
                selected_file_index = st.selectbox(
                    "Select file to process",
                    range(len(uploaded_files)),
                    format_func=lambda i: uploaded_files[i].name
                )
                selected_file = uploaded_files[selected_file_index]
                st.info(f"Selected file: **{selected_file.name}**")
            else:
                selected_file = uploaded_files[0]
            
            # Progress bar
            progress_container = st.empty()
            progress_bar = progress_container.progress(0)
            
            def update_progress(progress):
                progress_bar.progress(progress/100)
            
            # Process options
            process_option = st.radio(
                "Processing options",
                ["Process selected file", "Process all files and combine results"],
                index=0
            )
            
            # Process button
            if st.button("Process with AI", type="primary"):
                try:
                    if process_option == "Process selected file":
                        # Process single file
                        with st.spinner(f"Extracting information from {selected_file.name}..."):
                            # Extract and structure the report
                            verified_data = extract_and_structure_report(selected_file, update_progress)
                            
                            # Format for rating calculator
                            formatted_data = format_for_rating_calculator(verified_data)
                            
                            # Store in session state
                            st.session_state.verified_data = verified_data
                            st.session_state.formatted_data = formatted_data
                            
                            # Calculate rating
                            result = calculate_rating(
                                occupation=formatted_data["occupation"],
                                bodypart=formatted_data["bodypart"],
                                age_injury=formatted_data["age_injury"],
                                wpi=formatted_data["wpi"],
                                pain=formatted_data["pain"]
                            )
                            
                            # Store result in session state
                            st.session_state.calculation_result = {
                                "no_apportionment": {
                                    "final_pd_percent": result["final_value"],
                                    "formatted_impairments": formatted_data["bodypart"]
                                },
                                "age": verified_data.get("patient_age", 45),
                                "occupation": formatted_data["occupation"],
                                "group_number": verified_data.get("occupation_group")
                            }
                            
                            st.success(f"Processing complete for {selected_file.name}!")
                            st.rerun()
                    else:
                        # Process all files
                        all_impairments = []
                        occupation = None
                        age = None
                        date_of_injury = None
                        
                        for i, file in enumerate(uploaded_files):
                            with st.spinner(f"Processing file {i+1}/{len(uploaded_files)}: {file.name}"):
                                # Extract and structure the report
                                verified_data = extract_and_structure_report(file, update_progress)
                                
                                # Store the first occupation and age we find
                                if not occupation and "occupation" in verified_data:
                                    occupation = verified_data["occupation"]
                                if not age and "patient_age" in verified_data:
                                    age = verified_data["patient_age"]
                                if not date_of_injury and "date_of_injury" in verified_data:
                                    date_of_injury = verified_data["date_of_injury"]
                                
                                # Add impairments to the list
                                if "impairments" in verified_data:
                                    all_impairments.extend(verified_data["impairments"])
                        
                        # Create combined verified data
                        combined_data = {
                            "patient_age": age or 45,
                            "occupation": occupation or "Unknown",
                            "date_of_injury": date_of_injury or datetime.now().strftime("%Y-%m-%d"),
                            "impairments": all_impairments
                        }
                        
                        # Get occupation group if available
                        if occupation:
                            try:
                                group_number = get_occupation_group(occupation)
                                combined_data["occupation_group"] = group_number
                            except Exception:
                                pass
                        
                        # Format for rating calculator
                        formatted_data = format_for_rating_calculator(combined_data)
                        
                        # Store in session state
                        st.session_state.verified_data = combined_data
                        st.session_state.formatted_data = formatted_data
                        
                        # Calculate rating
                        result = calculate_rating(
                            occupation=formatted_data["occupation"],
                            bodypart=formatted_data["bodypart"],
                            age_injury=formatted_data["age_injury"],
                            wpi=formatted_data["wpi"],
                            pain=formatted_data["pain"]
                        )
                        
                        # Store result in session state
                        st.session_state.calculation_result = {
                            "no_apportionment": {
                                "final_pd_percent": result["final_value"],
                                "formatted_impairments": formatted_data["bodypart"]
                            },
                            "age": combined_data.get("patient_age", 45),
                            "occupation": formatted_data["occupation"],
                            "group_number": combined_data.get("occupation_group")
                        }
                        
                        st.success(f"Processing complete for all {len(uploaded_files)} files!")
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"Error processing report: {str(e)}")
    
    with col2:
        # Display results
        if 'verified_data' in st.session_state:
            st.markdown('<div class="section-header">Extracted Information</div>', unsafe_allow_html=True)
            
            # Patient and injury information
            st.markdown("""
            <div class="impairment-card">
                <div class="impairment-title">Patient & Injury Details</div>
                <div class="impairment-detail">
                    <div class="detail-label">Patient Age:</div>
                    <div class="detail-value">{}</div>
                </div>
                <div class="impairment-detail">
                    <div class="detail-label">Occupation:</div>
                    <div class="detail-value">{}</div>
                </div>
                <div class="impairment-detail">
                    <div class="detail-label">Occupation Group:</div>
                    <div class="detail-value">{}</div>
                </div>
                <div class="impairment-detail">
                    <div class="detail-label">Date of Injury:</div>
                    <div class="detail-value">{}</div>
                </div>
            </div>
            """.format(
                st.session_state.verified_data.get("patient_age", "Not found"),
                st.session_state.verified_data.get("occupation", "Not found"),
                st.session_state.verified_data.get("occupation_group", "Not found"),
                st.session_state.verified_data.get("date_of_injury", "Not found")
            ), unsafe_allow_html=True)
            
            # Impairments
            st.markdown('<div class="section-header">Impairments</div>', unsafe_allow_html=True)
            
            if "impairments" in st.session_state.verified_data and st.session_state.verified_data["impairments"]:
                for i, imp in enumerate(st.session_state.verified_data["impairments"]):
                    body_part = imp.get("body_part", "Unknown")
                    impairment_code = imp.get("impairment_code", "Unknown")
                    wpi = imp.get("wpi", 0)
                    pain_addon = imp.get("pain_addon", 0)
                    apportionment = imp.get("apportionment", 0)
                    variant = imp.get("variant", "Unknown")
                    adjusted_wpi = imp.get("adjusted_wpi", 0)
                    occupant_adjusted_wpi = imp.get("occupant_adjusted_wpi", 0)
                    age_adjusted_wpi = imp.get("age_adjusted_wpi", 0)
                    final_wpi = imp.get("final_wpi", 0)
                    
                    st.markdown(f"""
                    <div class="impairment-card">
                        <div class="impairment-title">Impairment {i+1}: {body_part}</div>
                        <div class="impairment-detail">
                            <div class="detail-label">Body Part:</div>
                            <div class="detail-value">{body_part}</div>
                        </div>
                        <div class="impairment-detail">
                            <div class="detail-label">Impairment Code:</div>
                            <div class="detail-value">{impairment_code}</div>
                        </div>
                        <div class="impairment-detail">
                            <div class="detail-label">WPI:</div>
                            <div class="detail-value">{wpi}%</div>
                        </div>
                        <div class="impairment-detail">
                            <div class="detail-label">Pain Add-on:</div>
                            <div class="detail-value">{pain_addon}</div>
                        </div>
                        <div class="impairment-detail">
                            <div class="detail-label">Apportionment:</div>
                            <div class="detail-value">{apportionment}%</div>
                        </div>
                        <div class="impairment-detail">
                            <div class="detail-label">Variant:</div>
                            <div class="detail-value">{variant}</div>
                        </div>
                        <div class="impairment-detail">
                            <div class="detail-label">Adjusted WPI (1.4x):</div>
                            <div class="detail-value">{adjusted_wpi:.1f}%</div>
                        </div>
                        <div class="impairment-detail">
                            <div class="detail-label">Occupational Adjusted WPI:</div>
                            <div class="detail-value">{occupant_adjusted_wpi:.1f}%</div>
                        </div>
                        <div class="impairment-detail">
                            <div class="detail-label">Age Adjusted WPI:</div>
                            <div class="detail-value">{age_adjusted_wpi:.1f}%</div>
                        </div>
                        <div class="impairment-detail">
                            <div class="detail-label">Final WPI (with apportionment):</div>
                            <div class="detail-value">{final_wpi:.1f}%</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No impairments found.")
    
    # Display calculation results
    if 'calculation_result' in st.session_state:
        st.markdown('<div class="section-header">Calculation Results</div>', unsafe_allow_html=True)
        
        # Display the final rating in a more prominent way
        final_rating = st.session_state.calculation_result["no_apportionment"]["final_pd_percent"]
        st.markdown(f"""
        <div class="impairment-card">
            <div class="calculation-result">Final Rating: {final_rating}%</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Use the existing render_results function
        render_results(st.session_state.calculation_result, "Styled Cards")
        
        # Add button to use in PDF Calculator
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Use in PDF Calculator", type="primary"):
                # Store impairments in session state for the calculator
                if 'formatted_data' in st.session_state and 'bodypart' in st.session_state.formatted_data:
                    st.session_state.impairments = st.session_state.formatted_data["bodypart"]
                    st.success("Data imported to PDF Calculator!")
                    st.info("Go to the PDF Calculator page to see the imported data.")
        
        # Add button to view raw JSON data
        with col2:
            if st.button("View Raw Data"):
                st.session_state.show_raw_data = not st.session_state.get("show_raw_data", False)
        
        # Show raw JSON data if requested
        if st.session_state.get("show_raw_data", False):
            st.markdown('<div class="section-header">Raw JSON Data</div>', unsafe_allow_html=True)
            st.markdown('<div class="json-preview">' + 
                        json.dumps(st.session_state.formatted_data, indent=2) + 
                        '</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
