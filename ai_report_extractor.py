import os
import json
import logging
import streamlit as st
from typing import Dict, Any, List, Optional
import PyPDF2
from openai import OpenAI
from utils.config import config
from utils.database import (
    get_occupation_group,
    get_variant_for_impairment,
    get_occupational_adjusted_wpi,
    get_age_adjusted_wpi
)
from utils.auth import init_openai_client
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
        logger.error(f"Error extracting text from PDF: {str(e)}")
        return ""

def get_extraction_instructions():
    """Get instructions for the initial extraction phase."""
    return """
You are a specialized medical report analyzer focused on extracting key information from workers' compensation medical reports.

TASK: Extract ALL relevant information needed for workers' compensation rating calculations.

Return ONLY a valid JSON object with NO additional text, using this EXACT structure:
{
    "patient_info": {
        "name": string or null,
        "date_of_birth": string (MM/DD/YYYY format) or null,
        "age": number or null,
        "gender": string or null
    },
    "injury_info": {
        "date_of_injury": string (MM/DD/YYYY format) or null,
        "mechanism_of_injury": string or null,
        "body_parts_affected": [string]
    },
    "occupation_info": {
        "job_title": string or null,
        "employer": string or null,
        "work_status": string or null
    },
    "impairments": [
        {
            "body_part": string,
            "wpi": number,
            "pain_addon": number (0-3),
            "apportionment": number (percentage),
            "context": string
        }
    ]
}

EXTRACTION GUIDELINES:

1. Patient Information:
   - Extract full name, date of birth, age, and gender
   - Format date of birth as MM/DD/YYYY if possible

2. Injury Information:
   - Extract date of injury (format as MM/DD/YYYY)
   - Extract mechanism/cause of injury
   - List all body parts mentioned as being affected

3. Occupation Information:
   - Extract job title/occupation (VERY IMPORTANT)
   - Extract employer name if available
   - Note current work status (working, disabled, modified duty, etc.)

4. Impairments (MOST IMPORTANT):
   - Search the ENTIRE document for ANY mention of impairment ratings
   - Look for Whole Person Impairment (WPI) percentages
   - Look for Permanent Disability ratings
   - Look for body part-specific impairments
   - For each impairment found:
     * Identify the specific body part (be as precise as possible)
     * Extract the WPI percentage
     * Determine if there's a pain add-on (0-3 scale)
     * Identify any apportionment percentage
     * Include a brief context snippet showing where this impairment was mentioned

5. Pay special attention to:
   - Final summary/conclusion sections
   - Tables or lists of impairments
   - Sections titled "Permanent and Stationary" or "P&S"
   - Sections discussing "disability" or "impairment"
   - ANY mention of percentages related to body parts

Be thorough - don't miss impairments that might be mentioned only once or in unusual sections of the report.
"""

def get_structured_format_instructions():
    """Get instructions for the structured formatting phase."""
    return """
You are a specialized medical report analyzer that converts extracted information into a standardized format for workers' compensation rating calculations.

TASK: Take the extracted information and convert it into a standardized format that can be used for database verification and rating calculation.

Return ONLY a valid JSON object with NO additional text, using this EXACT structure:
{
    "patient_age": number,
    "occupation": string,
    "date_of_injury": string (YYYY-MM-DD format),
    "impairments": [
        {
            "body_part": string,
            "impairment_code": string,
            "wpi": number,
            "pain_addon": number (0-3),
            "apportionment": number (percentage)
        }
    ]
}

STANDARDIZATION GUIDELINES:

1. Patient Age:
   - Use the extracted age if available
   - If age is not available but date of birth and date of injury are, calculate the age at time of injury
   - If neither is available, use 45 as a default age

2. Occupation:
   - Use the extracted job title/occupation
   - Standardize common occupation names (e.g., "truck driver" instead of "drives trucks")
   - If occupation is not available, use "Unknown" (but this is critical information)

3. Date of Injury:
   - Format as YYYY-MM-DD
   - If not available, use today's date

4. Impairments:
   - For each impairment:
     * Standardize body part names (e.g., "Lumbar Spine" instead of "lower back")
     * Assign an appropriate impairment code based on the body part
     * Include the WPI percentage
     * Include pain add-on (0-3)
     * Include apportionment percentage (0-100)

5. Impairment Codes:
   Use these standard codes for common body parts:
   - Spine/Back: "15.03.02.05" (Lumbar Range of Motion)
   - Neck/Cervical: "15.01.02.05" (Cervical Range of Motion)
   - Shoulder: "16.02.01.00" (Shoulder Range of Motion)
   - Knee: "17.05.00.00" (Knee)
   - Hand/Fingers: "16.05.00.00" (Hand/Multiple Fingers)
   - Foot/Ankle: "17.08.00.00" (Foot)
   - Upper Extremity/Arm: "16.00.00.00" (Upper Extremities)
   - Lower Extremity/Leg: "17.00.00.00" (Lower Extremities)
   - Hip: "17.03.00.00" (Hip)
   - Head/Brain: "13.00.00.00" (Central & Peripheral Nervous System)
   - Face: "11.02.01.00" (Face/cosmetic)
   - Chest/Ribs: "05.00.00.00" (Respiratory System)
   - Abdomen: "06.00.00.00" (Digestive System)
   - For any other body part, use "00.00.00.00"
"""

def extract_json_from_response(response_text: str) -> Dict[str, Any]:
    """Extract JSON data from the assistant's response text."""
    import re
    
    # Method 1: Direct JSON parsing
    try:
        result = json.loads(response_text)
        logger.info("Successfully parsed JSON directly")
        return result
    except json.JSONDecodeError:
        pass
    
    # Method 2: Find JSON in markdown code blocks
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
    if json_match:
        try:
            result = json.loads(json_match.group(1))
            logger.info("Successfully parsed JSON from code block")
            return result
        except json.JSONDecodeError:
            pass
    
    # Method 3: Find any JSON-like structure with a comprehensive regex
    json_match = re.search(r'\{(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\}))*\}))*\}', response_text, re.DOTALL)
    if json_match:
        try:
            result = json.loads(json_match.group(0))
            logger.info("Successfully parsed JSON from regex")
            return result
        except json.JSONDecodeError:
            pass
    
    # If we got here, we couldn't find valid JSON
    error_message = "Could not extract valid JSON from the assistant's response."
    logger.error(error_message)
    logger.debug(f"Response text: {response_text}")
    
    # Return a default empty structure
    return {"impairments": []}

def extract_and_structure_report(pdf_file, progress_callback=None):
    """
    Two-phase AI extraction process:
    1. Extract all relevant information from the report
    2. Structure the extracted information for database verification
    
    Args:
        pdf_file: A file-like object containing the PDF
        progress_callback: Optional callback function to report progress (0-100)
        
    Returns:
        Dict containing structured information for rating calculation
    """
    try:
        # Initialize progress reporting
        if progress_callback:
            progress_callback(5)
            
        # Initialize OpenAI client
        client = init_openai_client()
        if not client:
            raise ValueError("Failed to initialize OpenAI client. Check your API key.")
        
        if progress_callback:
            progress_callback(10)
            
        # Extract text from PDF
        pdf_file.seek(0)  # Reset file pointer
        extracted_text = extract_text_from_pdf(pdf_file)
        
        if not extracted_text:
            raise ValueError("Failed to extract text from PDF.")
        
        if progress_callback:
            progress_callback(20)
        
        # Phase 1: Extract information from the report
        logger.info("Phase 1: Extracting information from report")
        try:
            extraction_response = client.chat.completions.create(
                model=config.openai_model,
                messages=[
                    {"role": "system", "content": get_extraction_instructions()},
                    {"role": "user", "content": f"Please extract information from this medical report:\n\n{extracted_text}"}
                ],
                temperature=0.0
            )
        except Exception as e:
            # If temperature parameter is not supported, try without it
            if "temperature" in str(e) and "not supported" in str(e):
                logger.info("Temperature parameter not supported, trying without it")
                extraction_response = client.chat.completions.create(
                    model=config.openai_model,
                    messages=[
                        {"role": "system", "content": get_extraction_instructions()},
                        {"role": "user", "content": f"Please extract information from this medical report:\n\n{extracted_text}"}
                    ]
                )
            else:
                # Re-raise the exception if it's not related to temperature
                raise
        
        if progress_callback:
            progress_callback(50)
        
        # Parse the extraction response
        extraction_text = extraction_response.choices[0].message.content
        extracted_data = extract_json_from_response(extraction_text)
        
        logger.info(f"Extracted data: {json.dumps(extracted_data, indent=2)}")
        
        if progress_callback:
            progress_callback(60)
        
        # Phase 2: Structure the extracted information
        logger.info("Phase 2: Structuring extracted information")
        try:
            structure_response = client.chat.completions.create(
                model=config.openai_model,
                messages=[
                    {"role": "system", "content": get_structured_format_instructions()},
                    {"role": "user", "content": f"Please structure this extracted information for rating calculation:\n\n{json.dumps(extracted_data, indent=2)}"}
                ],
                temperature=0.0
            )
        except Exception as e:
            # If temperature parameter is not supported, try without it
            if "temperature" in str(e) and "not supported" in str(e):
                logger.info("Temperature parameter not supported, trying without it")
                structure_response = client.chat.completions.create(
                    model=config.openai_model,
                    messages=[
                        {"role": "system", "content": get_structured_format_instructions()},
                        {"role": "user", "content": f"Please structure this extracted information for rating calculation:\n\n{json.dumps(extracted_data, indent=2)}"}
                    ]
                )
            else:
                # Re-raise the exception if it's not related to temperature
                raise
        
        if progress_callback:
            progress_callback(80)
        
        # Parse the structure response
        structure_text = structure_response.choices[0].message.content
        structured_data = extract_json_from_response(structure_text)
        
        logger.info(f"Structured data: {json.dumps(structured_data, indent=2)}")
        
        if progress_callback:
            progress_callback(90)
        
        # Verify the structured data with the database
        verified_data = verify_with_database(structured_data)
        
        if progress_callback:
            progress_callback(100)
        
        return verified_data
        
    except Exception as e:
        logger.error(f"Error in extract_and_structure_report: {str(e)}", exc_info=True)
        raise Exception(f"Error extracting and structuring report: {str(e)}")

def verify_with_database(structured_data):
    """
    Verify the structured data with the database and add additional information.
    
    Args:
        structured_data: Dict containing structured information
        
    Returns:
        Dict containing verified information with additional database-derived fields
    """
    try:
        # Make a copy of the structured data
        verified_data = structured_data.copy()
        
        # Get occupation group
        occupation = structured_data.get("occupation")
        if occupation:
            try:
                group_number = get_occupation_group(occupation)
                verified_data["occupation_group"] = group_number
                logger.info(f"Found occupation group {group_number} for '{occupation}'")
            except Exception as e:
                logger.warning(f"Could not find occupation group for '{occupation}': {str(e)}")
                verified_data["occupation_group"] = None
        
        # Process each impairment
        for i, imp in enumerate(verified_data.get("impairments", [])):
            body_part = imp.get("body_part")
            impairment_code = imp.get("impairment_code")
            
            if body_part and impairment_code and "occupation_group" in verified_data and verified_data["occupation_group"]:
                try:
                    # Get variant
                    variant_info = get_variant_for_impairment(verified_data["occupation_group"], impairment_code)
                    variant_label = variant_info.get("variant_label", "G")
                    verified_data["impairments"][i]["variant"] = variant_label
                    logger.info(f"Found variant {variant_label} for group {verified_data['occupation_group']} and impairment '{impairment_code}'")
                    
                    # Calculate adjusted WPI
                    wpi = imp.get("wpi", 0)
                    pain_addon = imp.get("pain_addon", 0)
                    base_wpi = wpi + pain_addon
                    adjusted_wpi = base_wpi * 1.4  # Apply 1.4 multiplier
                    verified_data["impairments"][i]["adjusted_wpi"] = adjusted_wpi
                    
                    # Get occupational adjusted WPI
                    occupant_adjusted_wpi = get_occupational_adjusted_wpi(
                        verified_data["occupation_group"], 
                        variant_label, 
                        adjusted_wpi
                    )
                    verified_data["impairments"][i]["occupant_adjusted_wpi"] = occupant_adjusted_wpi
                    logger.info(f"Occupational adjusted WPI: {occupant_adjusted_wpi}")
                    
                    # Get age adjusted WPI
                    age = structured_data.get("patient_age", 45)  # Default to 45 if not available
                    age_adjusted_wpi = get_age_adjusted_wpi(age, occupant_adjusted_wpi)
                    verified_data["impairments"][i]["age_adjusted_wpi"] = age_adjusted_wpi
                    logger.info(f"Age adjusted WPI: {age_adjusted_wpi}")
                    
                    # Calculate final WPI with apportionment
                    apportionment = imp.get("apportionment", 0)
                    if apportionment > 0:
                        final_wpi = age_adjusted_wpi * (1 - apportionment/100)
                    else:
                        final_wpi = age_adjusted_wpi
                    verified_data["impairments"][i]["final_wpi"] = final_wpi
                    
                except Exception as e:
                    logger.warning(f"Error verifying impairment {body_part}: {str(e)}")
        
        return verified_data
        
    except Exception as e:
        logger.error(f"Error in verify_with_database: {str(e)}", exc_info=True)
        return structured_data  # Return the original data if verification fails

def format_for_rating_calculator(verified_data):
    """
    Format the verified data for use with the rating calculator.
    
    Args:
        verified_data: Dict containing verified information
        
    Returns:
        Dict formatted for the rating calculator
    """
    try:
        # Extract required fields
        occupation = verified_data.get("occupation", "Unknown")
        age_injury = verified_data.get("date_of_injury", datetime.now().strftime("%Y-%m-%d"))
        
        # Format impairments
        impairments = []
        for imp in verified_data.get("impairments", []):
            impairment = {
                "body_part": imp.get("body_part", "Unknown"),
                "wpi": imp.get("wpi", 0),
                "pain_addon": imp.get("pain_addon", 0),
                "apportionment": imp.get("apportionment", 0),
                "impairment_code": imp.get("impairment_code", "00.00.00.00")
            }
            
            # Add formatted string if available
            if "impairment_code" in imp and "body_part" in imp:
                impairment["formatted_string"] = f"{imp['impairment_code']} - {imp['body_part']}"
            
            impairments.append(impairment)
        
        # Create the formatted data
        formatted_data = {
            "occupation": occupation,
            "bodypart": impairments,
            "age_injury": age_injury,
            "wpi": 0,  # Not used when bodypart is a list of dictionaries
            "pain": 0   # Not used when bodypart is a list of dictionaries
        }
        
        return formatted_data
        
    except Exception as e:
        logger.error(f"Error in format_for_rating_calculator: {str(e)}", exc_info=True)
        raise Exception(f"Error formatting data for rating calculator: {str(e)}")

def main():
    """Main function for testing the AI report extractor."""
    st.set_page_config(page_title="AI Report Extractor", page_icon="🔍", layout="wide")
    st.title("AI Report Extractor")
    st.write("Upload a medical report to extract information using AI and verify with the database.")
    
    # File upload
    uploaded_file = st.file_uploader("Upload Medical Report", type=["pdf"])
    
    if uploaded_file:
        st.write(f"Processing file: {uploaded_file.name}")
        
        # Progress bar
        progress_bar = st.progress(0)
        
        def update_progress(progress):
            progress_bar.progress(progress/100)
        
        # Process the file
        try:
            with st.spinner("Extracting information from report..."):
                verified_data = extract_and_structure_report(uploaded_file, update_progress)
            
            # Display the extracted information
            st.subheader("Extracted Information")
            
            # Patient information
            st.write("**Patient Age:**", verified_data.get("patient_age", "Not found"))
            
            # Occupation information
            st.write("**Occupation:**", verified_data.get("occupation", "Not found"))
            if "occupation_group" in verified_data and verified_data["occupation_group"]:
                st.write("**Occupation Group:**", verified_data["occupation_group"])
            
            # Injury information
            st.write("**Date of Injury:**", verified_data.get("date_of_injury", "Not found"))
            
            # Impairments
            st.subheader("Impairments")
            
            if "impairments" in verified_data and verified_data["impairments"]:
                for i, imp in enumerate(verified_data["impairments"]):
                    with st.expander(f"Impairment {i+1}: {imp.get('body_part', 'Unknown')}"):
                        st.write("**Body Part:**", imp.get("body_part", "Unknown"))
                        st.write("**Impairment Code:**", imp.get("impairment_code", "Unknown"))
                        st.write("**WPI:**", f"{imp.get('wpi', 0)}%")
                        st.write("**Pain Add-on:**", imp.get("pain_addon", 0))
                        st.write("**Apportionment:**", f"{imp.get('apportionment', 0)}%")
                        
                        if "variant" in imp:
                            st.write("**Variant:**", imp["variant"])
                        if "adjusted_wpi" in imp:
                            st.write("**Adjusted WPI (1.4x):**", f"{imp['adjusted_wpi']:.1f}%")
                        if "occupant_adjusted_wpi" in imp:
                            st.write("**Occupational Adjusted WPI:**", f"{imp['occupant_adjusted_wpi']:.1f}%")
                        if "age_adjusted_wpi" in imp:
                            st.write("**Age Adjusted WPI:**", f"{imp['age_adjusted_wpi']:.1f}%")
                        if "final_wpi" in imp:
                            st.write("**Final WPI (with apportionment):**", f"{imp['final_wpi']:.1f}%")
            else:
                st.write("No impairments found.")
            
            # Format for rating calculator
            formatted_data = format_for_rating_calculator(verified_data)
            
            # Display the formatted data
            st.subheader("Formatted Data for Rating Calculator")
            st.json(formatted_data)
            
            # Store in session state
            st.session_state.ai_extracted_data = formatted_data
            
            # Add button to use this data in the calculator
            if st.button("Use in Calculator"):
                st.success("Data ready for use in calculator!")
                st.info("Go to the PDF Calculator page and click 'Import AI Results to Calculator'")
            
        except Exception as e:
            st.error(f"Error processing report: {str(e)}")

if __name__ == "__main__":
    main()
