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
from utils.latex_utils import clean_latex_expression, render_latex

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
        # Clean any LaTeX expressions in the result
        cleaned_result = clean_latex_expression(result)
        st.markdown(cleaned_result)
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
            # Create a container for the card
            no_apport_container = st.container()
            with no_apport_container:
                st.markdown("<h3>No Apportionment</h3>", unsafe_allow_html=True)
                st.markdown("<div class='card-content'>", unsafe_allow_html=True)
                st.text(render_impairments_card(details, with_apportionment=False))
                st.markdown("</div>", unsafe_allow_html=True)
                col1a, col1b = st.columns(2)
                with col1a:
                    st.button("Copy", key="copy_no_apport")
                with col1b:
                    st.button("Download", key="download_no_apport")
            
            # Create a container for combinations
            combinations_container = st.container()
            with combinations_container:
                st.markdown("<h3>Combinations and Calculations</h3>", unsafe_allow_html=True)
                st.markdown("<div class='card-content'>", unsafe_allow_html=True)
                st.text(render_combinations_card(upper_extremities, lower_extremities, spine, other, result))
                st.markdown("</div>", unsafe_allow_html=True)
                col1c, col1d = st.columns(2)
                with col1c:
                    st.button("Copy", key="copy_combinations")
                with col1d:
                    st.button("Download", key="download_combinations")
        else:
            st.text("NO APPORTIONMENT     100%\n")
            st.text(render_impairments_card(details, with_apportionment=False))
            st.text(render_combinations_card(upper_extremities, lower_extremities, spine, other, result))
        
    with col2:
        if display_mode == "Styled Cards":
            # Create a container for apportionment
            apport_container = st.container()
            with apport_container:
                st.markdown("<h3>With Apportionment</h3>", unsafe_allow_html=True)
                st.markdown("<div class='card-content'>", unsafe_allow_html=True)
                st.text(render_impairments_card(details, with_apportionment=True))
                st.markdown("</div>", unsafe_allow_html=True)
                col2a, col2b = st.columns(2)
                with col2a:
                    st.button("Copy", key="copy_apport")
                with col2b:
                    st.button("Download", key="download_apport")
            
            # Calculate apportioned result
            apportioned_result = result.get('with_apportionment', {})
            
            # Create a container for apportioned combinations
            apport_comb_container = st.container()
            with apport_comb_container:
                st.markdown("<h3>Apportioned Combinations</h3>", unsafe_allow_html=True)
                st.markdown("<div class='card-content'>", unsafe_allow_html=True)
                st.text(render_combinations_card(upper_extremities, lower_extremities, spine, other, apportioned_result))
                st.markdown("</div>", unsafe_allow_html=True)
                col2c, col2d = st.columns(2)
                with col2c:
                    st.button("Copy", key="copy_apport_comb")
                with col2d:
                    st.button("Download", key="download_apport_comb")
        else:
            st.text("WITH APPORTIONMENT 90% and 80% CS LS\n")
            st.text(render_impairments_card(details, with_apportionment=True))
            
            apportioned_result = result.get('with_apportionment', {})
            st.text(render_combinations_card(upper_extremities, lower_extremities, spine, other, apportioned_result))
    
    # Display detailed summary if available
    if 'detailed_summary' in result:
        if display_mode == "Styled Cards":
            # Clean any LaTeX expressions in the detailed summary
            if isinstance(result['detailed_summary'], dict):
                for key in result['detailed_summary']:
                    if isinstance(result['detailed_summary'][key], str):
                        result['detailed_summary'][key] = clean_latex_expression(result['detailed_summary'][key])
            
            # Create a container for detailed summary
            detailed_container = st.container()
            with detailed_container:
                st.markdown("<h3>Detailed Analysis</h3>", unsafe_allow_html=True)
                st.markdown("<div class='card-content'>", unsafe_allow_html=True)
                st.markdown(f"<h4>Medical History</h4>{result['detailed_summary']['medical_history']}", unsafe_allow_html=True)
                st.markdown(f"<h4>Injury Mechanism</h4>{result['detailed_summary']['injury_mechanism']}", unsafe_allow_html=True)
                st.markdown(f"<h4>Treatment History</h4>{result['detailed_summary']['treatment_history']}", unsafe_allow_html=True)
                st.markdown(f"<h4>Work Restrictions</h4>{result['detailed_summary']['work_restrictions']}", unsafe_allow_html=True)
                st.markdown(f"<h4>Future Medical Needs</h4>{result['detailed_summary']['future_medical']}", unsafe_allow_html=True)
                st.markdown(f"<h4>Apportionment</h4>{result['detailed_summary']['apportionment']}", unsafe_allow_html=True)
                if result['detailed_summary'].get('additional_findings'):
                    st.markdown(f"<h4>Additional Findings</h4>{result['detailed_summary']['additional_findings']}", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
                col3a, col3b = st.columns(2)
                with col3a:
                    st.button("Copy", key="copy_detailed")
                with col3b:
                    st.button("Download", key="download_detailed")
        else:
            st.write("\n### Detailed Analysis")
            st.write("#### Medical History")
            st.write(clean_latex_expression(result['detailed_summary']['medical_history']))
            st.write("#### Injury Mechanism")
            st.write(clean_latex_expression(result['detailed_summary']['injury_mechanism']))
            st.write("#### Treatment History")
            st.write(clean_latex_expression(result['detailed_summary']['treatment_history']))
            st.write("#### Work Restrictions")
            st.write(clean_latex_expression(result['detailed_summary']['work_restrictions']))
            st.write("#### Future Medical Needs")
            st.write(clean_latex_expression(result['detailed_summary']['future_medical']))
            st.write("#### Apportionment")
            st.write(clean_latex_expression(result['detailed_summary']['apportionment']))
            if result['detailed_summary'].get('additional_findings'):
                st.write("#### Additional Findings")
                st.write(clean_latex_expression(result['detailed_summary']['additional_findings']))
    
    # Display final calculations
    if display_mode == "Styled Cards":
        # Create a container for final calculations
        final_container = st.container()
        with final_container:
            st.markdown("<h3>Final Calculations</h3>", unsafe_allow_html=True)
            st.markdown("<div class='card-content'>", unsafe_allow_html=True)
            no_apport = result.get('no_apportionment', {})
            st.markdown(f"Combined Rating: {round(no_apport.get('final_pd_percent', 0))}%", unsafe_allow_html=True)
            st.markdown(f"Total Weeks of PD: {round(no_apport.get('weeks', 0), 2)}", unsafe_allow_html=True)
            st.markdown(f"Age on DOI: {result.get('age', 'N/A')}", unsafe_allow_html=True)
            st.markdown(f"PD Weekly Rate: ${no_apport.get('pd_weekly_rate', 290.00)}", unsafe_allow_html=True)
            st.markdown(f"Total PD Payout: ${round(no_apport.get('total_pd_dollars', 0), 2)}", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            col4a, col4b = st.columns(2)
            with col4a:
                st.button("Copy", key="copy_final")
            with col4b:
                st.button("Download", key="download_final")
    else:
        st.write("\n#### Final Calculations")
        no_apport = result.get('no_apportionment', {})
        st.write(f"Combined Rating: {round(no_apport.get('final_pd_percent', 0))}%")
        st.write(f"Total Weeks of PD: {round(no_apport.get('weeks', 0), 2)}")
        st.write(f"Age on DOI: {result.get('age', 'N/A')}")
        st.write(f"PD Weekly Rate: ${no_apport.get('pd_weekly_rate', 290.00)}")
        st.write(f"Total PD Payout: ${round(no_apport.get('total_pd_dollars', 0), 2)}")
