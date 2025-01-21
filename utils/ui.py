import streamlit as st
from typing import Dict, Any, List, Union
from utils.styling import (
    get_card_css,
    render_styled_card,
    render_impairments_card,
    render_combinations_card,
    render_detailed_summary_card,
    render_final_calculations_card
)

def setup_page():
    """Setup the main page configuration and styling."""
    st.markdown(get_card_css(), unsafe_allow_html=True)
    st.title("PDRS Workers' Comp Rating Assistant")

def render_upload_section():
    """Render the file upload section with mode selection."""
    st.subheader("Upload Medical Report")
    
    mode = st.radio(
        "Select Analysis Mode",
        ["Standard Rating", "Detailed Summary"],
        help="Standard Rating: Basic rating calculation\nDetailed Summary: Comprehensive analysis with detailed findings"
    )
    
    uploaded_files = st.file_uploader("Choose files", type=["pdf", "docx", "doc", "txt"], accept_multiple_files=True)
    
    combine_reports = False
    if uploaded_files and len(uploaded_files) > 1:
        combine_reports = st.checkbox("Combine reports for single patient", 
            help="Check this if all reports are for the same patient and should be combined into one calculation")
    
    return mode, uploaded_files, combine_reports

def render_manual_inputs():
    """Render manual input options."""
    manual_inputs = st.expander("Manual Input Options")
    with manual_inputs:
        manual_age = st.number_input("Age at Time of Injury", min_value=0, max_value=100, value=0)
        manual_occupation = st.text_input("Occupation")
    
    return {
        "age": manual_age if manual_age > 0 else None,
        "occupation": manual_occupation if manual_occupation.strip() else None
    }

def render_display_mode_selector():
    """Render display mode selection."""
    return st.radio(
        "Display Mode",
        ["Standard", "Styled Cards"],
        horizontal=True
    )

def render_results(result: Union[str, Dict[str, Any]], display_mode: str):
    """Render the processing results."""
    # If result is a string (detailed mode), display it directly
    if isinstance(result, str):
        st.markdown("### Detailed Summary")
        st.markdown(result)
        return
        
    # For rating calculations, process the details
    if 'no_apportionment' in result:
        details = result['no_apportionment'].get('formatted_impairments', [])
    
    # Categorize impairments
    upper_extremities = [d for d in details if d['impairment_code'].startswith('16')]
    lower_extremities = [d for d in details if d['impairment_code'].startswith('17')]
    spine = [d for d in details if d['impairment_code'].startswith('15')]
    other = [d for d in details if not any(d['impairment_code'].startswith(x) for x in ['15', '16', '17'])]
    
    # Create two columns for display
    col1, col2 = st.columns(2)
    
    with col1:
        if display_mode == "Styled Cards":
            st.markdown(render_styled_card(
                "No Apportionment",
                render_impairments_card(details, with_apportionment=False),
                "no_apportionment"
            ), unsafe_allow_html=True)
            
            st.markdown(render_styled_card(
                "Combinations and Calculations",
                render_combinations_card(upper_extremities, lower_extremities, spine, other, result),
                "combinations"
            ), unsafe_allow_html=True)
        else:
            st.text("NO APPORTIONMENT     100%\n")
            st.text(render_impairments_card(details, with_apportionment=False))
            st.text(render_combinations_card(upper_extremities, lower_extremities, spine, other, result))
        
    with col2:
        if display_mode == "Styled Cards":
            st.markdown(render_styled_card(
                "With Apportionment",
                render_impairments_card(details, with_apportionment=True),
                "apportionment"
            ), unsafe_allow_html=True)
            
            # Calculate apportioned result
            apportioned_result = result.get('with_apportionment', {})
            
            st.markdown(render_styled_card(
                "Apportioned Combinations",
                render_combinations_card(upper_extremities, lower_extremities, spine, other, apportioned_result),
                "apportioned_combinations"
            ), unsafe_allow_html=True)
        else:
            st.text("WITH APPORTIONMENT 90% and 80% CS LS\n")
            st.text(render_impairments_card(details, with_apportionment=True))
            
            apportioned_result = result.get('with_apportionment', {})
            st.text(render_combinations_card(upper_extremities, lower_extremities, spine, other, apportioned_result))
    
    # Display detailed summary if available
    if 'detailed_summary' in result:
        if display_mode == "Styled Cards":
            st.markdown(render_detailed_summary_card(result['detailed_summary']), unsafe_allow_html=True)
        else:
            st.write("\n### Detailed Analysis")
            st.write("#### Medical History")
            st.write(result['detailed_summary']['medical_history'])
            st.write("#### Injury Mechanism")
            st.write(result['detailed_summary']['injury_mechanism'])
            st.write("#### Treatment History")
            st.write(result['detailed_summary']['treatment_history'])
            st.write("#### Work Restrictions")
            st.write(result['detailed_summary']['work_restrictions'])
            st.write("#### Future Medical Needs")
            st.write(result['detailed_summary']['future_medical'])
            st.write("#### Apportionment")
            st.write(result['detailed_summary']['apportionment'])
            if result['detailed_summary'].get('additional_findings'):
                st.write("#### Additional Findings")
                st.write(result['detailed_summary']['additional_findings'])
    
    # Display final calculations
    if display_mode == "Styled Cards":
        st.markdown(render_final_calculations_card(result), unsafe_allow_html=True)
    else:
        st.write("\n#### Final Calculations")
        no_apport = result.get('no_apportionment', {})
        st.write(f"Combined Rating: {round(no_apport.get('final_pd_percent', 0))}%")
        st.write(f"Total Weeks of PD: {round(no_apport.get('weeks', 0), 2)}")
        st.write(f"Age on DOI: {result.get('age', 'N/A')}")
        st.write(f"PD Weekly Rate: ${no_apport.get('pd_weekly_rate', 290.00)}")
        st.write(f"Total PD Payout: ${round(no_apport.get('total_pd_dollars', 0), 2)}")
