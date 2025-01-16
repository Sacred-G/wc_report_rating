import os
import time
import math
import re
import json
import csv
from typing import Dict, List, Any
import sqlite3
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# -------------
# ENV VARS
# -------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/local.db")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")
VECTOR_STORE = os.getenv("VECTOR_STORE")

if not OPENAI_API_KEY:
    raise EnvironmentError("Please set OPENAI_API_KEY in your .env file.")

client = OpenAI(api_key=OPENAI_API_KEY)

def init_database():
    """Initialize SQLite database with tables and import data from CSV files"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Create tables
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS occupational_adjustments (
            id INTEGER PRIMARY KEY,
            rating_percent REAL,
            c REAL,
            d REAL,
            e REAL,
            f REAL,
            g REAL,
            h REAL,
            i REAL,
            j REAL
        );

        CREATE TABLE IF NOT EXISTS occupations (
            id INTEGER PRIMARY KEY,
            group_number INTEGER,
            occupation_title TEXT,
            industry TEXT
        );

        CREATE TABLE IF NOT EXISTS variants (
            id INTEGER PRIMARY KEY,
            body_part TEXT,
            impairment_code TEXT,
            group_110 TEXT,
            group_111 TEXT,
            group_112 TEXT,
            group_120 TEXT,
            group_210 TEXT,
            group_211 TEXT,
            group_212 TEXT,
            group_213 TEXT,
            group_214 TEXT,
            group_220 TEXT,
            group_221 TEXT,
            group_230 TEXT,
            group_240 TEXT,
            group_250 TEXT,
            group_251 TEXT,
            group_290 TEXT
        );

        CREATE TABLE IF NOT EXISTS variants_2 (
            id INTEGER PRIMARY KEY,
            body_part TEXT,
            impairment_code TEXT,
            group_310 TEXT,
            group_311 TEXT,
            group_320 TEXT,
            group_321 TEXT,
            group_322 TEXT,
            group_330 TEXT,
            group_331 TEXT,
            group_332 TEXT,
            group_340 TEXT,
            group_341 TEXT,
            group_350 TEXT,
            group_351 TEXT,
            group_360 TEXT,
            group_370 TEXT,
            group_380 TEXT,
            group_390 TEXT,
            group_420 TEXT,
            group_430 TEXT,
            group_460 TEXT,
            group_470 TEXT,
            group_480 TEXT,
            group_481 TEXT,
            group_482 TEXT,
            group_490 TEXT,
            group_491 TEXT,
            group_492 TEXT,
            group_493 TEXT,
            group_560 TEXT,
            group_590 TEXT
        );

        CREATE TABLE IF NOT EXISTS age_adjustment (
            id INTEGER PRIMARY KEY,
            wpi_percent REAL,
            "21_and_under" REAL,
            "22_to_26" REAL,
            "27_to_31" REAL,
            "32_to_36" REAL,
            "37_to_41" REAL,
            "42_to_46" REAL,
            "47_to_51" REAL,
            "52_to_56" REAL,
            "57_to_61" REAL,
            "62_and_over" REAL
        );
    """)

    # Import data from CSV files if tables are empty
    def import_csv(table_name, csv_path):
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        if cursor.fetchone()[0] == 0:  # Only import if table is empty
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    placeholders = ','.join(['?' for _ in row])
                    columns = ','.join(row.keys())
                    cursor.execute(
                        f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})",
                        list(row.values())
                    )

    # Import data from CSV files
    csv_files = {
        'occupational_adjustments': 'data/sql/occupational_adjustments_rows.csv',
        'occupations': 'data/sql/occupations_rows.csv',
        'variants': 'data/sql/variants_rows.csv',
        'variants_2': 'data/sql/variants_2_rows.csv',
        'age_adjustment': 'data/sql/age_adjustment_rows.csv'
    }

    for table, csv_path in csv_files.items():
        if os.path.exists(csv_path):
            import_csv(table, csv_path)

    conn.commit()
    conn.close()

def get_assistant_instructions(mode="default"):
    base_instructions = """You are a medical report analyzer for workers' compensation cases.
    Extract key information including:
        - Patient age
        - Occupation
        - Body parts injured
        - WPI ratings
        - Pain add-on percentage
    Important Instructions for Dental/MMI:
        - ALWAYS check the ENTIRE report for dental ratings or MMI, as they may appear in any section
        - Look for terms like "dental", "teeth", "mastication", "jaw"
    
    Search through the entire document carefully for these details. They may appear in different sections.
        - The occupation might be listed under employment history or work status
        - Age might be listed in patient demographics or history
        - WPI ratings are typically found in the final review section at the end of the report
        - Pain add-ons are often mentioned alongside the impairment ratings or in a separate pain discussion section
        - Dental ratings are usually in separate dental reports - make sure to check for these, they will not be in the final review with the others. 
    
    Use the following as reference for body part    Spine and Nervous System:
        - SPINE-DRE-ROM (15.01--15.03) - For cervical, thoracic, and lumbar spine
        - PERIPH-SPINE (13.12.01.XX) - For peripheral spine conditions
        - PERIPH-UE (13.12.02.XX) - For peripheral upper extremity
        - PERIPH-LE (13.12.03.XX) - For peripheral lower extremity
        
    Upper Extremities:
        - PERIPH - UE (04.03.01.00) - For peripheral vascular upper extremity
        - ARM-AMPUT (16.01.01.XX) - For arm amputation
        - ARM-GRIP/PINCH (16.01.04.00) - For grip and pinch strength
        - HAND (16.05.XX.XX) - For hand conditions
        - SHOULDER-ROM (16.02.01.00) - For shoulder range of motion
        - ELBOW-ROM (16.03.01.00) - For elbow range of motion
        - WRIST-ROM (16.04.01.00) - For wrist range of motion
        
    Lower Extremities:
        - PERIPH - LE (04.03.02.00) - For peripheral vascular lower extremity
        - KNEE (17.05.XX.XX) - For knee conditions
        - ANKLE (17.07.XX.XX) - For ankle conditions
        - HIP (17.03.XX.XX) - For hip conditions
        - LEG-AMPUT (17.01.02.XX) - For leg amputation
        
    Cardiovascular:
        - CARDIO-HEART (03.01--03.06) - For heart conditions
        - PULM CIRC (04.04.00.00) - For pulmonary circulation
        - RESPIRATORY (05.01--05.03) - For respiratory conditions
        
    Digestive and Internal:
        - UPPER DIGEST (06.01.00.00) - For upper digestive system
        - LIVER (06.04.00.00) - For liver conditions
        - URINARY (07.01--07.04) - For urinary conditions
        
    Mental and Neurological:
        - PSYCHIATRIC (14.01.00.00) - For psychiatric conditions
        - COGNITIVE IMP (13.04.00.00) - For cognitive impairment
        - LANGUAGE DISOR (13.05.00.00) - For language disorders
        
    Other Systems:
        - MASTICATION (11.03.02.00) - For dental/jaw conditions
        - VISION (12.01--12.03) - For vision impairment
        - SKIN-SCARS (08.01--08.02) - For skin and scar conditions
    """

    if mode == "detailed":
        return base_instructions + """
    Additionally, provide a detailed analysis including:
    - Patient's medical history relevant to the injury
    - Detailed description of the injury mechanism
    - Treatment history and current status
    - Work restrictions and limitations
    - Future medical needs
    - Apportionment considerations
    - Any other relevant medical findings
    
    Return a JSON object with these fields:
    {
        "age": int,
        "occupation": string,
        "impairments": [
            {
                "body_part": string,
                "wpi": float
            }
        ],
        "pain_addon": float (optional),
        "detailed_summary": {
            "medical_history": string,
            "injury_mechanism": string,
            "treatment_history": string,
            "work_restrictions": string,
            "future_medical": string,
            "apportionment": string,
            "additional_findings": string
        }
    }"""
    
    return base_instructions + """
    Return ONLY a valid JSON object with these exact fields, no additional text or markdown:
    {
        "age": int,
        "occupation": string,
        "impairments": [
            {
                "body_part": string,
                "wpi": float
            }
        ],
        "pain_addon": float (optional)
    }
    
    IMPORTANT: 
    1. Return ONLY the JSON object, no markdown formatting or additional text
    2. Ensure all string values are properly quoted
    3. Use numbers for numeric values (no quotes)
    4. Format the JSON exactly as shown above
    """

def process_medical_report(uploaded_file, manual_data=None, mode="default"):
    try:
        # Save uploaded file temporarily
        with open("temp_file.pdf", "wb") as f:
            f.write(uploaded_file.getvalue())
            
        # Create OpenAI file
        openai_file = client.files.create(
            file=open("temp_file.pdf", "rb"),
            purpose="assistants"
        )
        st.info("File uploaded successfully")
        
        # Create vector store for file search
        vector_store = client.beta.vector_stores.create(
            name="Medical Report Store"
        )
        
        # Add file to vector store and wait for processing
        file_batch = client.beta.vector_stores.file_batches.create_and_poll(
            vector_store_id=vector_store.id,
            file_ids=[openai_file.id]
        )
        
        if file_batch.status != "completed":
            st.error(f"File processing failed with status: {file_batch.status}")
            st.stop()
            
        st.success("File processed successfully")
            
        # Create assistant with file search enabled
        assistant = client.beta.assistants.create(
            name="Medical Report Assistant",
            instructions=get_assistant_instructions(mode),
            tools=[{"type": "file_search"}],
            model="gpt-4o-mini",
            tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}}
        )
        
        # Create thread and message for AI analysi
        thread = client.beta.threads.create()
        
        # Run assistant
        with st.spinner("Analyzing report..."):
            run = client.beta.threads.runs.create_and_poll(
                thread_id=thread.id,
                assistant_id=assistant.id
            )
        
        if run.status == "completed":
            messages = client.beta.threads.messages.list(thread_id=thread.id)
            response_text = messages.data[0].content[0].text.value
            
            # Parse JSON from response with improved error handling
            try:
                # First try direct JSON parsing
                extracted_data = json.loads(response_text)
                
                # Override with manual data if provided
                if manual_data:
                    if manual_data.get("age"):
                        extracted_data["age"] = manual_data["age"]
                    if manual_data.get("occupation"):
                        extracted_data["occupation"] = manual_data["occupation"]
                
                return process_extracted_data(extracted_data)
            except json.JSONDecodeError:
                # Try to find JSON in markdown code blocks
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
                if json_match:
                    try:
                        extracted_data = json.loads(json_match.group(1))
                        return process_extracted_data(extracted_data)
                    except json.JSONDecodeError as e:
                        st.error(f"Invalid JSON in code block: {str(e)}")
                        st.text("Response text:")
                        st.code(response_text)
                        raise ValueError(f"Invalid JSON in code block: {str(e)}")
                
                # Try to find any JSON-like structure
                json_match = re.search(r'\{[^}]+\}', response_text, re.DOTALL)
                if json_match:
                    try:
                        extracted_data = json.loads(json_match.group(0))
                        return process_extracted_data(extracted_data)
                    except json.JSONDecodeError as e:
                        st.error(f"Invalid JSON structure: {str(e)}")
                        st.text("Response text:")
                        st.code(response_text)
                        raise ValueError(f"Invalid JSON structure: {str(e)}")
                
                # If no JSON found, show the full response for debugging
                st.error("Could not find valid JSON in response")
                st.text("Full response text:")
                st.code(response_text)
                raise ValueError("Could not parse JSON from assistant response")
        else:
            raise Exception(f"Assistant run failed with status: {run.status}")
            
    except Exception as e:
        raise Exception(f"Error processing medical report: {str(e)}")
    finally:
        # Cleanup
        try:
            os.remove("temp_file.pdf")
        except:
            pass

def process_extracted_data(data):
    try:
        age = data["age"]
        occupation = data["occupation"]
        impairments = data["impairments"]
        pain_addon = data.get("pain_addon", 0.0)

        # Get occupation group
        group_number = get_occupation_group(occupation)

        # Process each impairment
        wpi_list = []
        calculation_details = []
        
        for imp in impairments:
            body_part = imp["body_part"]
            original_wpi = float(imp["wpi"])

            # Map body part to impairment code
            impairment_code = map_body_part_to_code(body_part)
            
            # Get variant info
            variant_info = get_variant_for_impairment(group_number, impairment_code)
            variant_label = variant_info.get("variant_label", "variant1")

            # Calculate base WPI with pain add-on and 1.4 multiplier
            base_wpi = original_wpi + pain_addon
            adjusted_wpi = base_wpi * 1.4
            
            # Get occupational adjustment using the adjusted WPI and variant
            occupant_adjusted_wpi = get_occupational_adjusted_wpi(group_number, variant_label, adjusted_wpi)
            
            # Get age adjustment using the occupationally adjusted WPI
            age_adjusted_wpi = get_age_adjusted_wpi(age, occupant_adjusted_wpi)
            wpi_list.append(age_adjusted_wpi)
            
            # Store calculation details
            calculation_details.append({
                "body_part": body_part,
                "impairment_code": impairment_code,
                "group_number": group_number,
                "variant": variant_label,
                "original_wpi": original_wpi,
                "pain_addon": pain_addon,
                "base_wpi": base_wpi,
                "adjusted_wpi": adjusted_wpi,
                "occupant_adjusted_wpi": occupant_adjusted_wpi,
                "age_adjusted_wpi": age_adjusted_wpi
            })

        # Calculate final values
        final_pd_percent = combine_wpi_values(wpi_list)
        result = calculate_pd_payout(final_pd_percent, calculation_details, age)
        
        # Add detailed summary if available
        if "detailed_summary" in data:
            result["detailed_summary"] = data["detailed_summary"]
            
        return result

    except Exception as e:
        raise Exception(f"Error processing extracted data: {str(e)}")

def map_body_part_to_code(body_part: str) -> str:
    """Maps body part descriptions to standardized impairment codes."""
    body_part_lower = body_part.lower().strip()
    
    # Spine and Nervous System
    if any(term in body_part_lower for term in ["spine", "back", "lumbar", "thoracic", "cervical", "neck"]):
        if "lumbar" in body_part_lower and ("range" in body_part_lower or "motion" in body_part_lower or "rom" in body_part_lower):
            return "15.03.02.05"
        elif "cervical" in body_part_lower and ("range" in body_part_lower or "motion" in body_part_lower or "rom" in body_part_lower):
            return "15.01.02.05"
        return "15.03.02.05"  # Default to lumbar if not specified
    
    # Upper Extremities
    if "shoulder" in body_part_lower:
        if "range" in body_part_lower or "motion" in body_part_lower or "rom" in body_part_lower:
            return "16.02.01.00"
        return "16.02.01.00"
    
    if "elbow" in body_part_lower:
        if "range" in body_part_lower or "motion" in body_part_lower or "rom" in body_part_lower:
            return "16.03.01.00"
        return "16.03.01.00"
        
    if "wrist" in body_part_lower:
        if "range" in body_part_lower or "motion" in body_part_lower or "rom" in body_part_lower:
            return "16.04.01.00"
        return "16.04.01.00"
        
    if any(term in body_part_lower for term in ["hand", "finger", "thumb"]):
        return "16.05.00.00"
        
    if "grip" in body_part_lower or "pinch" in body_part_lower:
        return "16.01.04.00"
        
    # Lower Extremities
    if "knee" in body_part_lower:
        if "muscle" in body_part_lower or "strength" in body_part_lower:
            return "17.05.05.00"
        return "17.05.00.00"
        
    if "ankle" in body_part_lower:
        return "17.07.00.00"
        
    if "hip" in body_part_lower:
        return "17.03.00.00"
        
    if "leg" in body_part_lower and "amput" in body_part_lower:
        return "17.01.02.00"
    
    # Other Systems
    if "mastication" in body_part_lower or "jaw" in body_part_lower:
        return "11.03.02.00"
    
    # Generic mappings for unspecified conditions
    if any(term in body_part_lower for term in ["arm", "upper extremity", "bicep", "tricep"]):
        return "16.00.00.00"
    if any(term in body_part_lower for term in ["leg", "lower extremity", "shin", "calf"]):
        return "17.00.00.00"
    
    # Default to OTHER if no specific match found
    return "00.00.00.00"

def get_occupation_group(occupation: str) -> int:
    # Handle special cases first
    occupation_lower = occupation.lower()
    if 'stocker' in occupation_lower or 'sorter' in occupation_lower:
        return 360  # Same as packer group
    
    # Try to find in database
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT group_number FROM occupations WHERE occupation_title LIKE ?", ('%' + occupation + '%',))
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        raise ValueError(f"Occupation '{occupation}' not found in 'occupations' table.")
    return result[0]

def get_variant_for_impairment(group_num: int, impairment_code: str) -> Dict[str, Any]:
    """Get variant information with flexible impairment code matching."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    table_name = "variants_2" if group_num >= 310 else "variants"
    
    # Map specific codes to general body parts for lookup
    code_to_body_part = {
        "SPINE-DRE-ROM": "SPINE",
        "PERIPH-SPINE": "SPINE",
        "PERIPH-UE": "ARM",
        "PERIPH-LE": "LEG",
        "ARM-AMPUT": "ARM",
        "ARM-GRIP/PINCH": "ARM",
        "SHOULDER-ROM": "SHOULDER",
        "ELBOW-ROM": "ELBOW",
        "WRIST-ROM": "WRIST",
        "LEG-AMPUT": "LEG"
    }
    
    # Convert specific codes to general body parts
    lookup_code = code_to_body_part.get(impairment_code, impairment_code)
    
    # Try to find a match
    cursor.execute(f"SELECT * FROM {table_name} WHERE body_part = ?", (lookup_code,))
    result = cursor.fetchone()
    
    if not result:
        # If no match found, try a more generic approach
        if any(term in lookup_code.lower() for term in ["arm", "hand", "wrist", "elbow", "shoulder"]):
            cursor.execute(f"SELECT * FROM {table_name} WHERE body_part = ?", ("ARM",))
            result = cursor.fetchone()
        elif any(term in lookup_code.lower() for term in ["leg", "knee", "ankle", "foot"]):
            cursor.execute(f"SELECT * FROM {table_name} WHERE body_part = ?", ("LEG",))
            result = cursor.fetchone()
    
    conn.close()
    
    if not result:
        # Return a default variant if no match found
        return {"variant_label": "G"}
    
    column_names = [description[0] for description in cursor.description]
    variant_data = dict(zip(column_names, result))
    
    # Find the variant for the specific group number
    group_key = f"group_{group_num}"
    variant_label = variant_data.get(group_key)
    if not variant_label:
        # Return default variant if no specific group variant found
        return {"variant_label": "G"}
        
    return {"variant_label": variant_label.lower()}

def get_occupational_adjusted_wpi(group_num: int, variant_label: str, base_wpi: float) -> float:
    """Get occupational adjusted WPI value from the table."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Find the closest rating_percent that's less than or equal to our WPI
    cursor.execute("SELECT * FROM occupational_adjustments WHERE rating_percent <= ? ORDER BY rating_percent DESC LIMIT 1", (base_wpi,))
    result = cursor.fetchone()
    
    if not result:
        # If no match found, use the lowest rating
        cursor.execute("SELECT * FROM occupational_adjustments ORDER BY rating_percent ASC LIMIT 1")
        result = cursor.fetchone()
        if not result:
            conn.close()
            return base_wpi  # Return unadjusted WPI if no data available
    
    column_names = [description[0].lower() for description in cursor.description]
    
    # Convert variant label to column name (c, d, e, f, g, h, i, j)
    variant_label = variant_label.lower()
    if variant_label in column_names:
        adjustment_column = variant_label
    else:
        # Default to 'g' if variant not found
        adjustment_column = 'g'
    
    try:
        column_index = column_names.index(adjustment_column)
        # Get the actual value from the table - this IS the adjusted WPI, not a multiplier
        adjusted_wpi = float(result[column_index])
        conn.close()
        return adjusted_wpi
    except (ValueError, IndexError):
        conn.close()
        return base_wpi

def get_age_adjusted_wpi(age: int, raw_wpi: float) -> float:
    """Get age adjusted WPI value from the table."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Find the closest wpi_percent that's greater than or equal to our raw_wpi
    cursor.execute("SELECT * FROM age_adjustment WHERE wpi_percent <= ? ORDER BY wpi_percent DESC LIMIT 1", (raw_wpi,))
    result = cursor.fetchone()
    
    if not result:
        # If no match found, use the lowest WPI
        cursor.execute("SELECT * FROM age_adjustment ORDER BY wpi_percent ASC LIMIT 1")
        result = cursor.fetchone()
        if not result:
            conn.close()
            raise ValueError("No data found in age adjustment table.")
    
    column_names = [description[0] for description in cursor.description]
    age_ranges = {
        (0, 22): "21_and_under",
        (22, 27): "22_to_26",
        (27, 32): "27_to_31",
        (32, 37): "32_to_36",
        (37, 42): "37_to_41",
        (42, 47): "42_to_46",
        (47, 52): "47_to_51",
        (52, 57): "52_to_56",
        (57, 62): "57_to_61",
        (62, 150): "62_and_over"
    }
    
    age_column = next((col for (start, end), col in age_ranges.items() if start <= age < end), None)
    if not age_column:
        conn.close()
        raise ValueError(f"No age bracket found for age {age}")
    
    try:
        # Get the actual value from the table - this IS the adjusted WPI
        age_adjusted_wpi = float(result[column_names.index(age_column)])
        conn.close()
        return age_adjusted_wpi
    except (ValueError, IndexError) as e:
        conn.close()
        raise ValueError(f"Error applying age adjustment: {str(e)}")

from utils.calculations import combine_wpi_values

def calculate_payment_weeks(total_pd: float) -> float:
    """Calculate payment weeks based on PD percentage ranges."""
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
        return total_pd * 9  # Maximum rate

def calculate_pd_payout(final_pd_percent: float, calculation_details: List[Dict[str, Any]], age: int) -> Dict[str, Any]:
    weeks = calculate_payment_weeks(final_pd_percent)
    total_pd_dollars = weeks * 290.0
    return {
        "final_pd_percent": round(final_pd_percent, 2),
        "weeks": round(weeks, 2),
        "total_pd_dollars": round(total_pd_dollars, 2),
        "calculation_details": calculation_details,
        "age": age
    }

from utils.styling import (
    get_card_css,
    render_styled_card,
    render_impairments_card,
    render_combinations_card,
    render_detailed_summary_card,
    render_final_calculations_card
)

def main():
    st.set_page_config(layout="wide")
    st.markdown(get_card_css(), unsafe_allow_html=True)
    
    st.title("PDRS Workers' Comp Rating Assistant")
    st.write(f"Using Assistant ID: {ASSISTANT_ID}")
    st.write(f"Using Vector Store: {VECTOR_STORE}")

    # Initialize database
    if not os.path.exists(DATABASE_PATH):
        os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
        init_database()

    st.subheader("Upload Medical Report PDF")
    
    # Add mode selection
    mode = st.radio(
        "Select Analysis Mode",
        ["Standard Rating", "Detailed Summary"],
        help="Standard Rating: Basic rating calculation\nDetailed Summary: Comprehensive analysis with detailed findings"
    )
    
    uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"])

    # Add manual input section with expander
    manual_inputs = st.expander("Manual Input Options")
    with manual_inputs:
        manual_age = st.number_input("Age at Time of Injury", min_value=0, max_value=100, value=0)
        manual_occupation = st.text_input("Occupation")
    
    if uploaded_file is not None:
        if st.button("Process Report"):
            try:
                with st.spinner("Processing..."):
                    # Pass manual inputs to process_medical_report
                    manual_data = {
                        "age": manual_age if manual_age > 0 else None,
                        "occupation": manual_occupation if manual_occupation.strip() else None
                    }
                    result = process_medical_report(
                        uploaded_file, 
                        manual_data,
                        "detailed" if mode == "Detailed Summary" else "default"
                    )
                    st.success("Processing Complete!")
                    # Add display mode toggle
                    display_mode = st.radio(
                        "Display Mode",
                        ["Standard", "Styled Cards"],
                        horizontal=True
                    )

                    # Display each impairment with detailed calculation steps
                    details = result['calculation_details']
                    
                    # Group impairments by body region for proper combination order
                    upper_extremities = []
                    lower_extremities = []
                    spine = []
                    other = []
                    
                    for detail in details:
                        if "upper extremit" in detail['body_part'].lower():
                            upper_extremities.append(detail)
                        elif "lower extremit" in detail['body_part'].lower():
                            lower_extremities.append(detail)
                        elif any(x in detail['body_part'].lower() for x in ["spine", "lumbar", "cervical", "thoracic"]):
                            spine.append(detail)
                        else:
                            other.append(detail)

                    if display_mode == "Styled Cards":
                    
                        st.markdown(render_impairments_card(details), unsafe_allow_html=True)
                    else:
                        # Standard display
                        for detail in details:
                            impairment_str = (
                                f"({detail['impairment_code']} - {detail['original_wpi']} - [1.4] "
                                f"{round(detail['adjusted_wpi'], 2)} - {detail['group_number']}{detail['variant'].upper()} - "
                                f"{round(detail['occupant_adjusted_wpi'], 2)} - {round(detail['age_adjusted_wpi'], 2)}%) "
                                f"{round(detail['age_adjusted_wpi'], 2)}% {detail['body_part']}"
                            )
                            st.write(impairment_str)
                    
                    # Show combination steps
                    if len(details) > 1:
                        if display_mode == "Styled Cards":
                            st.markdown(render_combinations_card(
                                upper_extremities,
                                lower_extremities,
                                spine,
                                other,
                                result
                            ), unsafe_allow_html=True)
                        else:
                            st.write("\n#### Combination Steps")
                            # Combine upper extremities first if present
                            if len(upper_extremities) > 1:
                                ue_ratings = [str(round(d['age_adjusted_wpi'])) for d in upper_extremities]
                                st.write(f"{' C '.join(ue_ratings)} = {round(combine_wpi_values([d['age_adjusted_wpi'] for d in upper_extremities]))}%")
                            
                            # Combine lower extremities if present
                            if len(lower_extremities) > 1:
                                le_ratings = [str(round(d['age_adjusted_wpi'])) for d in lower_extremities]
                                st.write(f"{' C '.join(le_ratings)} = {round(combine_wpi_values([d['age_adjusted_wpi'] for d in lower_extremities]))}%")
                            
                            # Final combination of all regions
                            all_ratings = []
                            if upper_extremities:
                                all_ratings.append(str(round(combine_wpi_values([d['age_adjusted_wpi'] for d in upper_extremities]))))
                            if lower_extremities:
                                all_ratings.append(str(round(combine_wpi_values([d['age_adjusted_wpi'] for d in lower_extremities]))))
                            for s in spine:
                                all_ratings.append(str(round(s['age_adjusted_wpi'])))
                            for o in other:
                                all_ratings.append(str(round(o['age_adjusted_wpi'])))
                            
                            st.write(f"{' C '.join(all_ratings)} = {round(result['final_pd_percent'])}%")
                    
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
                            if result['detailed_summary']['additional_findings']:
                                st.write("#### Additional Findings")
                                st.write(result['detailed_summary']['additional_findings'])
                    
                    # Display final calculations
                    if display_mode == "Styled Cards":
                        st.markdown(render_final_calculations_card(result), unsafe_allow_html=True)
                    else:
                        st.write("\n#### Final Calculations")
                        st.write(f"Combined Rating: {round(result['final_pd_percent'])}%")
                        st.write(f"Total of All Add-ons for Pain: {result.get('pain_addon', 0)}%")
                        st.write(f"Total Weeks of PD: {round(result['weeks'], 2)}")
                        st.write(f"Age on DOI: {result.get('age', 'N/A')}")
                        st.write(f"PD Weekly Rate: $290.00")
                        st.write(f"Total PD Payout: ${round(result['total_pd_dollars'], 2)}")
            except Exception as e:
                st.error(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
