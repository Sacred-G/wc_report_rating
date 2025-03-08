import os
import streamlit as st
import pandas as pd
import PyPDF2
import re
from datetime import datetime
import sqlite3
from dotenv import load_dotenv
from utils.database import get_occupation_group, get_variant_for_impairment, get_occupational_adjusted_wpi, get_age_adjusted_wpi, init_database
from utils.calculations import combine_wpi_values
from utils.report_processor import process_medical_reports
from utils.ui import render_results
from utils.styling import get_card_css
from utils.ai_extractor import extract_all_impairments

# Load environment variables
load_dotenv()

# Initialize database
if 'db_initialized' not in st.session_state:
    try:
        init_database()
        st.session_state.db_initialized = True
    except Exception as e:
        st.error(f"Error initializing database: {str(e)}")

def load_occupations():
    """Load occupations from CSV file for dropdown menu."""
    try:
        # Print the current working directory for debugging
        st.write(f"Loading occupations from: data/occupations_rows.csv")
        
        # Load the CSV file
        df = pd.read_csv('data/occupations_rows.csv')
        
        # Create a list of occupation titles with their group numbers
        occupations = []
        for _, row in df.iterrows():
            # Strip any leading/trailing whitespace from occupation titles
            title = row['occupation_title'].strip()
            group = row['group_number']
            occupations.append(f"{title} ({group})")
        
        # Sort and return the list
        return sorted(occupations)
    except Exception as e:
        st.error(f"Error loading occupations: {str(e)}")
        st.error(f"Details: {type(e).__name__}")
        return []

def load_impairments():
    """Load impairments from CSV file for dropdown menu."""
    try:
        # Print the current working directory for debugging
        st.write(f"Loading impairments from: data/bodypart_impairment_rows.csv")
        
        # Load the CSV file
        df = pd.read_csv('data/bodypart_impairment_rows.csv')
        
        # Create a list of impairment codes with descriptions
        impairments = []
        for _, row in df.iterrows():
            code = row['Code']
            description = row['Description']
            impairments.append(f"{code} - {description}")
        
        # Sort and return the list
        return sorted(impairments)
    except Exception as e:
        st.error(f"Error loading impairments: {str(e)}")
        st.error(f"Details: {type(e).__name__}")
        return []

def extract_text_from_pdf(pdf_file):
    """Extract text from a PDF file."""
    try:
        # Create a PDF reader object
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        # Extract text from each page
        text = ""
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text += page.extract_text() + "\n\n"
            
        return text
    except Exception as e:
        st.error(f"Error extracting text from PDF: {str(e)}")
        return ""

def extract_date_of_birth(text):
    """Extract date of birth from text."""
    # Look for common date of birth patterns
    patterns = [
        r'(?:Date of Birth|DOB|Birth Date)[\s:]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'(?:Date of Birth|DOB|Birth Date)[\s:]+(\w+ \d{1,2},? \d{2,4})',
        r'(?:born on|Born)[\s:]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'(?:born on|Born)[\s:]+(\w+ \d{1,2},? \d{2,4})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    
    return None

def extract_date_of_injury(text):
    """Extract date of injury from text."""
    # Look for common date of injury patterns
    patterns = [
        r'(?:Date of Injury|DOI|Injury Date)[\s:]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'(?:Date of Injury|DOI|Injury Date)[\s:]+(\w+ \d{1,2},? \d{2,4})',
        r'(?:injured on|Injured on)[\s:]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'(?:injured on|Injured on)[\s:]+(\w+ \d{1,2},? \d{2,4})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    
    return None

def extract_occupation(text):
    """Extract occupation from text."""
    # Look for common occupation patterns
    patterns = [
        r'(?:Occupation|Job Title|Employment)[\s:]+([A-Za-z\s]+)',
        r'(?:employed as|Employed as)[\s:]+([A-Za-z\s]+)',
        r'(?:works as|Works as)[\s:]+([A-Za-z\s]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    
    return None

def extract_impairments(text):
    """Extract impairments from text."""
    # Look for common impairment patterns
    impairments = []
    
    # More flexible pattern for WPI (Whole Person Impairment) mentions
    # This pattern will match formats like "10% WPI", "10% whole person impairment", 
    # "10% impairment", "10 percent WPI", etc.
    wpi_patterns = [
        r'(\d+)%\s*(?:whole\s*person\s*impairment|WPI|impairment)',
        r'(\d+)\s*percent\s*(?:whole\s*person\s*impairment|WPI|impairment)',
        r'(?:whole\s*person\s*impairment|WPI|impairment)\s*(?:of|is|at|:)?\s*(\d+)%',
        r'(?:whole\s*person\s*impairment|WPI|impairment)\s*(?:of|is|at|:)?\s*(\d+)\s*percent'
    ]
    
    # Common body parts with more variations
    body_parts = [
        'spine', 'lumbar', 'cervical', 'thoracic', 'shoulder', 'knee', 
        'hip', 'elbow', 'wrist', 'ankle', 'foot', 'hand', 'arm', 'leg',
        'back', 'neck', 'upper extremity', 'lower extremity', 'thumb',
        'finger', 'toe', 'head', 'face', 'jaw', 'pelvis', 'sacrum',
        'coccyx', 'rib', 'chest', 'abdomen', 'groin', 'thigh', 'calf',
        'forearm', 'bicep', 'tricep', 'quadricep', 'hamstring', 'achilles',
        'rotator cuff', 'meniscus', 'acl', 'mcl', 'lcl', 'pcl', 'labrum'
    ]
    
    # Process each pattern
    for wpi_pattern in wpi_patterns:
        wpi_matches = re.finditer(wpi_pattern, text, re.IGNORECASE)
        
        for match in wpi_matches:
            # Look for body parts in a larger context around the impairment mention
            # Check both before and after the match
            start_pos = max(0, match.start() - 200)
            end_pos = min(len(text), match.end() + 200)
            context_text = text[start_pos:end_pos]
            
            found_body_part = None
            
            # First, try to find body parts in the context
            for part in body_parts:
                if part.lower() in context_text.lower():
                    # Get the position of the body part in the context
                    part_pos = context_text.lower().find(part.lower())
                    # If the body part is closer to the match, prioritize it
                    if not found_body_part or abs(part_pos - (match.start() - start_pos)) < abs(context_text.lower().find(found_body_part.lower()) - (match.start() - start_pos)):
                        found_body_part = part
            
            # If no body part found, use a default
            if not found_body_part:
                # Try to find any capitalized words that might be body parts
                words = re.findall(r'\b[A-Z][a-z]+\b', context_text)
                if words:
                    # Use the closest capitalized word as a potential body part
                    found_body_part = words[0]
                else:
                    # Default to "Unspecified" if no body part can be found
                    found_body_part = "Unspecified"
            
            # Extract the WPI value
            wpi_value = int(match.group(1))
            
            # Create the impairment entry
            impairment = {
                'body_part': found_body_part.capitalize(),
                'wpi': wpi_value,
                'apportionment': 0,  # Default to 0
                'pain_addon': 0  # Default to 0
            }
            
            # Check if this impairment is already in the list (avoid duplicates)
            duplicate = False
            for existing_imp in impairments:
                if existing_imp['body_part'] == impairment['body_part'] and existing_imp['wpi'] == impairment['wpi']:
                    duplicate = True
                    break
            
            if not duplicate:
                impairments.append(impairment)
    
    # If we found impairments, log them for debugging
    if impairments:
        print(f"Extracted {len(impairments)} impairments: {impairments}")
    else:
        print("No impairments extracted from the text.")
    
    return impairments

def calculate_age(birth_date, injury_date):
    """Calculate age at time of injury."""
    try:
        # Parse dates
        if birth_date and injury_date:
            # Try different date formats
            for fmt in ['%m/%d/%Y', '%m-%d-%Y', '%B %d, %Y', '%B %d %Y']:
                try:
                    dob = datetime.strptime(birth_date, fmt)
                    doi = datetime.strptime(injury_date, fmt)
                    age = doi.year - dob.year - ((doi.month, doi.day) < (dob.month, dob.day))
                    return age
                except ValueError:
                    continue
    except Exception:
        pass
    
    return None

def main():
    st.set_page_config(page_title="PDF Calculator", page_icon="📊", layout="wide")
    st.markdown(get_card_css(), unsafe_allow_html=True)
    st.title("PDF Calculator")
    st.write("Upload a PDF report to automatically extract information and calculate ratings.")
    
    # Load data for dropdowns
    occupations = load_occupations()
    impairments = load_impairments()
    
    # Create two columns for layout
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # File upload section
        uploaded_files = st.file_uploader("Upload Medical Report(s)", type=["pdf"], accept_multiple_files=True)
        
        if uploaded_files:
            # Process each uploaded file
            for i, uploaded_file in enumerate(uploaded_files):
                st.write(f"Processing file {i+1}: {uploaded_file.name}")
            
            # Extract text from first PDF for preview (we'll process all files later)
            first_file = uploaded_files[0]
            pdf_text = extract_text_from_pdf(first_file)
            
            if pdf_text:
                st.success("PDF processed successfully!")
                
                # Extract information
                dob = extract_date_of_birth(pdf_text)
                doi = extract_date_of_injury(pdf_text)
                occupation = extract_occupation(pdf_text)
                extracted_impairments = extract_impairments(pdf_text)
                
                # Calculate age
                age = calculate_age(dob, doi) if dob and doi else None
                
                # Store extracted information in session state
                if dob:
                    st.session_state.extracted_dob = dob
                if doi:
                    st.session_state.extracted_doi = doi
                if age:
                    st.session_state.extracted_age = age
                if occupation:
                    st.session_state.extracted_occupation = occupation
                if extracted_impairments:
                    st.session_state.extracted_impairments = extracted_impairments
                
                # Display extracted information
                st.subheader("Extracted Information")
                
                if dob:
                    st.write(f"Date of Birth: {dob}")
                if doi:
                    st.write(f"Date of Injury: {doi}")
                if age:
                    st.write(f"Age at Injury: {age}")
                if occupation:
                    st.write(f"Occupation: {occupation}")
                
                if extracted_impairments:
                    st.write("Extracted Impairments:")
                    for imp in extracted_impairments:
                        if 'formatted_string' in imp:
                            st.write(f"- {imp['formatted_string']}: {imp['wpi']}% WPI")
                        else:
                            st.write(f"- {imp['body_part']}: {imp['wpi']}% WPI")
                
                # Add button to import extracted data to calculator
                if st.button("Import Extracted Data to Calculator"):
                    # Store impairments in session state for the calculator
                    if extracted_impairments:
                        st.session_state.impairments = extracted_impairments
                        st.success(f"Extracted data imported to calculator! Added {len(extracted_impairments)} impairments.")
                    else:
                        st.warning("No impairments were extracted from the PDF. Please try using AI processing for better results.")
                    st.rerun()
                
                # AI processing options
                ai_options = st.radio(
                    "AI Processing Options",
                    ["No AI (Fast)", "Enhanced Extraction (Balanced)", "Full AI Processing (Slow)"],
                    index=1,
                    help="Choose how to process the PDFs. Enhanced extraction uses AI to find impairments but keeps the calculation local. Full AI processing uses the complete AI pipeline."
                )
                
                if ai_options != "No AI (Fast)" and st.button("Process with AI"):
                    with st.spinner(f"Processing {len(uploaded_files)} file(s) with AI..."):
                        try:
                            if ai_options == "Enhanced Extraction (Balanced)":
                                # Use our specialized AI extractor for each file
                                progress_placeholder = st.empty()
                                
                                def update_progress(progress):
                                    progress_placeholder.progress(progress/100)
                                
                                # Process each file and collect all impairments
                                all_impairments = []
                                for i, file in enumerate(uploaded_files):
                                    st.write(f"Processing file {i+1}/{len(uploaded_files)}: {file.name}")
                                    # Reset file pointer
                                    file.seek(0)
                                    
                                    file_impairments = extract_all_impairments(
                                        file, 
                                        use_ai=True, 
                                        progress_callback=update_progress
                                    )
                                    
                                    if file_impairments:
                                        all_impairments.extend(file_impairments)
                                
                                # Store impairments in session state
                                if all_impairments:
                                    st.session_state.impairments = all_impairments
                                    st.success(f"Enhanced extraction complete! Found {len(all_impairments)} impairments across {len(uploaded_files)} file(s).")
                                    st.rerun()
                                else:
                                    st.warning("No impairments were found. Please try using Full AI Processing or manual input.")
                            else:  # Full AI Processing
                                # Process with full AI pipeline
                                result = process_medical_reports(uploaded_files)
                                
                                # Store result in session state
                                st.session_state.ai_result = result
                                st.success("AI processing complete!")
                                st.rerun()
                        except Exception as e:
                            st.error(f"Error processing report: {str(e)}")
                            st.info("Please try a different processing option or use manual input.")
    
    with col2:
        # Manual input/correction section
        st.subheader("Manual Input/Correction")
        
        # Date inputs - pre-fill with extracted dates if available
        dob_default = None
        doi_default = None
        
        # Try to convert extracted dates to datetime objects
        if 'extracted_dob' in st.session_state:
            try:
                for fmt in ['%m/%d/%Y', '%m-%d-%Y', '%B %d, %Y', '%B %d %Y']:
                    try:
                        dob_default = datetime.strptime(st.session_state.extracted_dob, fmt).date()
                        break
                    except ValueError:
                        continue
            except Exception:
                pass
                
        if 'extracted_doi' in st.session_state:
            try:
                for fmt in ['%m/%d/%Y', '%m-%d-%Y', '%B %d, %Y', '%B %d %Y']:
                    try:
                        doi_default = datetime.strptime(st.session_state.extracted_doi, fmt).date()
                        break
                    except ValueError:
                        continue
            except Exception:
                pass
        
        dob_input = st.date_input("Date of Birth", value=dob_default)
        doi_input = st.date_input("Date of Injury", value=doi_default)
        
        # Calculate age from inputs
        age_input = None
        if dob_input and doi_input:
            age_input = doi_input.year - dob_input.year - ((doi_input.month, doi_input.day) < (dob_input.month, dob_input.day))
            st.write(f"Calculated Age at Injury: {age_input}")
        
        # Occupation dropdown - try to find a match for the extracted occupation
        occupation_default = 0  # Default to empty option (index 0)
        
        if 'extracted_occupation' in st.session_state and st.session_state.extracted_occupation:
            # Try to find a matching occupation in the dropdown
            extracted_occ = st.session_state.extracted_occupation.lower().strip()
            for i, occ in enumerate(occupations):
                if extracted_occ in occ.lower():
                    occupation_default = i + 1  # +1 because we added an empty option at index 0
                    break
        
        occupation_input = st.selectbox("Occupation", options=[""] + occupations, index=occupation_default)
        
        # Impairment section
        st.subheader("Impairments")
        
        # Initialize impairments list in session state if not exists
        if 'impairments' not in st.session_state:
            st.session_state.impairments = []
        
        # Display current impairments
        for i, imp in enumerate(st.session_state.impairments):
            cols = st.columns([3, 1, 1, 1, 1])
            with cols[0]:
                if 'formatted_string' in imp:
                    st.write(f"{imp['formatted_string']}")
                else:
                    st.write(f"{imp['body_part']}")
            with cols[1]:
                st.write(f"WPI: {imp['wpi']}%")
            with cols[2]:
                st.write(f"Pain: {imp['pain_addon']}")
            with cols[3]:
                st.write(f"Apport: {imp['apportionment']}%")
            with cols[4]:
                if st.button("Remove", key=f"remove_{i}"):
                    st.session_state.impairments.pop(i)
                    st.rerun()
        
        # Add new impairment
        with st.expander("Add Impairment"):
            imp_cols = st.columns([3, 1, 1, 1])
            
            with imp_cols[0]:
                new_impairment = st.selectbox("Body Part/Impairment", options=[""] + impairments, key="new_imp")
            
            with imp_cols[1]:
                new_wpi = st.number_input("WPI %", min_value=0, max_value=100, value=0, key="new_wpi")
            
            with imp_cols[2]:
                new_pain = st.number_input("Pain Add-on", min_value=0, max_value=3, value=0, key="new_pain")
            
            with imp_cols[3]:
                new_apportionment = st.number_input("Apportionment %", min_value=0, max_value=100, value=0, key="new_apport")
            
            if st.button("Add Impairment"):
                if new_impairment:
                    # Extract body part from the selected impairment
                    body_part = new_impairment.split(" - ")[1] if " - " in new_impairment else new_impairment
                    
                    # Get impairment code and formatted string
                    impairment_code = new_impairment.split(" - ")[0] if " - " in new_impairment else ""
                    formatted_string = new_impairment if " - " in new_impairment else body_part
                    
                    # Add to session state
                    st.session_state.impairments.append({
                        'body_part': body_part,
                        'wpi': new_wpi,
                        'pain_addon': new_pain,
                        'apportionment': new_apportionment,
                        'impairment_code': impairment_code,
                        'formatted_string': formatted_string
                    })
                    st.rerun()
        
        # Calculate button
        if st.button("Calculate Rating"):
            if not st.session_state.impairments:
                st.error("Please add at least one impairment.")
            elif not age_input:
                st.error("Please enter Date of Birth and Date of Injury to calculate age.")
            elif not occupation_input:
                st.error("Please select an occupation.")
            else:
                # Extract group number from occupation
                group_match = re.search(r'\((\d+)\)$', occupation_input)
                group_number = int(group_match.group(1)) if group_match else None
                
                if not group_number:
                    st.error("Could not extract occupation group number.")
                else:
                    # Prepare data for calculation
                    calculation_details = []
                    no_apportionment_wpi_list = []
                    with_apportionment_wpi_list = []
                    
                    for imp in st.session_state.impairments:
                        body_part = imp["body_part"]
                        original_wpi = float(imp["wpi"])
                        apportionment = float(imp["apportionment"])
                        pain_addon = min(imp.get("pain_addon", 0.0), 3.0)
                        
                        # Get impairment code
                        impairment_code = imp.get("impairment_code", "00.00.00.00")
                        
                        # Get variant info
                        try:
                            variant_info = get_variant_for_impairment(group_number, impairment_code)
                            variant_label = variant_info.get("variant_label", "G")
                        except Exception:
                            variant_label = "G"
                        
                        # Add pain add-on to base WPI before 1.4 multiplier
                        base_wpi = original_wpi + pain_addon
                        adjusted_wpi = base_wpi * 1.4  # Apply 1.4 multiplier after adding pain
                        
                        # Get occupational adjustment
                        try:
                            occupant_adjusted_wpi = get_occupational_adjusted_wpi(group_number, variant_label, adjusted_wpi)
                        except Exception:
                            occupant_adjusted_wpi = adjusted_wpi
                        
                        # Get age adjustment
                        try:
                            age_adjusted_wpi = get_age_adjusted_wpi(age_input, occupant_adjusted_wpi)
                        except Exception:
                            age_adjusted_wpi = occupant_adjusted_wpi
                        
                        # Calculate apportioned value if applicable
                        apportioned_wpi = age_adjusted_wpi * (1 - apportionment/100) if apportionment > 0 else age_adjusted_wpi
                        
                        # Store calculation details
                        detail = {
                            "body_part": body_part,
                            "impairment_code": impairment_code,
                            "group_number": group_number,
                            "variant": variant_label,
                            "original_wpi": original_wpi,
                            "pain_addon": pain_addon,
                            "base_wpi": base_wpi,
                            "adjusted_wpi": adjusted_wpi,
                            "occupant_adjusted_wpi": occupant_adjusted_wpi,
                            "age_adjusted_wpi": age_adjusted_wpi,
                            "apportioned_wpi": apportioned_wpi if apportionment > 0 else None,
                            "apportionment": apportionment
                        }
                        
                        calculation_details.append(detail)
                        no_apportionment_wpi_list.append(age_adjusted_wpi)
                        
                        if apportionment > 0:
                            with_apportionment_wpi_list.append(apportioned_wpi)
                    
                    # Calculate final values
                    no_apportionment_pd = combine_wpi_values(no_apportionment_wpi_list)
                    with_apportionment_pd = combine_wpi_values(with_apportionment_wpi_list) if with_apportionment_wpi_list else None
                    
                    # Calculate weeks
                    def calculate_payment_weeks(total_pd):
                        if total_pd < 10:
                            return total_pd * 4
                        elif total_pd < 24.75:
                            return total_pd * 5
                        elif total_pd < 29.75:
                            return total_pd * 6
                        elif total_pd < 49.75:
                            return total_pd * 7
                        elif total_pd < 69.75:
                            return total_pd * 8
                        elif total_pd < 99.75:
                            return total_pd * 9
                        else:
                            return total_pd * 9
                    
                    # Format impairment strings
                    formatted_impairments = []
                    for detail in calculation_details:
                        # Format the impairment code and description
                        body_part = detail["body_part"]
                        code = detail["impairment_code"]
                        variant = detail["variant"]
                        
                        # Build the rating string with proper spacing
                        base_str = (
                            f"{code} - {detail['original_wpi']:.0f} - [1.4]{detail['adjusted_wpi']:.0f} - "
                            f"{detail['group_number']}{detail['variant']} - {detail['age_adjusted_wpi']:.0f}%"
                        )
                        
                        # Add apportionment if present
                        if detail.get('apportioned_wpi') is not None:
                            rating_str = base_str
                        else:
                            rating_str = base_str
                            
                        formatted_impairments.append({
                            "body_part": body_part,
                            "formatted_string": rating_str,
                            "wpi": detail['age_adjusted_wpi'] if detail.get('apportioned_wpi') is None else detail['apportioned_wpi'],
                            "impairment_code": code  # Add impairment_code to the formatted impairments
                        })
                    
                    # Calculate no apportionment result
                    weeks = calculate_payment_weeks(no_apportionment_pd)
                    pd_weekly_rate = 290.0
                    total_pd_dollars = weeks * pd_weekly_rate
                    
                    no_apportionment_result = {
                        "final_pd_percent": round(no_apportionment_pd, 2),
                        "weeks": round(weeks, 2),
                        "pd_weekly_rate": pd_weekly_rate,
                        "total_pd_dollars": round(total_pd_dollars, 2),
                        "formatted_impairments": formatted_impairments
                    }
                    
                    # Calculate with apportionment result if applicable
                    with_apportionment_result = None
                    if with_apportionment_pd:
                        weeks = calculate_payment_weeks(with_apportionment_pd)
                        total_pd_dollars = weeks * pd_weekly_rate
                        
                        with_apportionment_result = {
                            "final_pd_percent": round(with_apportionment_pd, 2),
                            "weeks": round(weeks, 2),
                            "pd_weekly_rate": pd_weekly_rate,
                            "total_pd_dollars": round(total_pd_dollars, 2),
                            "formatted_impairments": formatted_impairments
                        }
                    
                    # Store results in session state
                    st.session_state.calculation_result = {
                        "no_apportionment": no_apportionment_result,
                        "with_apportionment": with_apportionment_result,
                        "age": age_input,
                        "occupation": occupation_input.split(" (")[0] if " (" in occupation_input else occupation_input,
                        "group_number": group_number
                    }
                    
                    st.success("Calculation complete!")
                    st.rerun()
    
    # Display results if available
    if 'calculation_result' in st.session_state:
        st.header("Calculation Results")
        # Apply CSS before rendering results
        st.markdown(get_card_css(), unsafe_allow_html=True)
        render_results(st.session_state.calculation_result, "Styled Cards")
    
    # Display AI results if available
    elif 'ai_result' in st.session_state:
        st.header("AI Processing Results")
        # Apply CSS before rendering results
        st.markdown(get_card_css(), unsafe_allow_html=True)
        render_results(st.session_state.ai_result, "Styled Cards")
        
        # Option to import AI results to calculator
        if st.button("Import AI Results to Calculator"):
            if isinstance(st.session_state.ai_result, dict):
                # Extract impairments
                if 'no_apportionment' in st.session_state.ai_result and 'formatted_impairments' in st.session_state.ai_result['no_apportionment']:
                    impairments = []
                    for imp in st.session_state.ai_result['no_apportionment']['formatted_impairments']:
                        # Parse the formatted string to extract values
                        parts = imp['formatted_string'].split(' - ')
                        if len(parts) >= 2:
                            impairments.append({
                                'body_part': imp['body_part'],
                                'wpi': float(parts[1]),
                                'pain_addon': 0,  # Default
                                'apportionment': 0,  # Default
                                'impairment_code': parts[0],
                                'formatted_string': imp.get('formatted_string', f"{parts[0]} - {imp['body_part']}")
                            })
                    
                    # Update session state
                    st.session_state.impairments = impairments
                    
                    # Extract age and occupation
                    if 'age' in st.session_state.ai_result:
                        st.session_state.age = st.session_state.ai_result['age']
                    
                    if 'occupation' in st.session_state.ai_result:
                        st.session_state.occupation = st.session_state.ai_result['occupation']
                    
                    st.success("AI results imported to calculator!")
                    st.rerun()

if __name__ == "__main__":
    main()
