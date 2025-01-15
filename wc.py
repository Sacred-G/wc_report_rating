import pandas as pd
import streamlit as st
from openai import OpenAI
import json
import re
import os
import time
import tempfile
from datetime import datetime

# Import pages
from pages.chat import chat_interface
from pages.history import view_history
from pages.settings import settings
from pages.about import about
from pages.process_report import process_report

# Page configurations
st.set_page_config(
    page_title="QME Report Processor",
    page_icon="📋",
    layout="wide"
)

# Load the necessary CSV files
try:
    occupations = pd.read_csv('data/occupations_rows.csv')
    age_adjustments = pd.read_csv('data/age_adjustment_rows.csv')
    occupational_adjustment = pd.read_csv('data/occupational_adjustments_rows.csv')
    variants = pd.read_csv('data/variants.csv')
except FileNotFoundError as e:
    st.error(f"CSV file not found: {e}")
    st.stop()

# OpenAI Client setup
API_KEY = "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"
client = OpenAI(api_key=API_KEY)

def get_assistant_instructions(mode):
    """Get instructions for the assistant based on mode"""
    if mode == "Calculate WPI Ratings":
        return """You are a QME assistant specialized in analyzing medical reports and extracting specific data points.
    
    Look for and extract:
    1. Patient's occupation/job title
    2. Patient's age
    3. Body parts with their WPI (Whole Person Impairment) ratings
    4. Pain add-on ratings for each body part (up to 3% can be added)
    5. Dental ratings (check separate dental reports for MMI and WPI ratings)
    
    Important Instructions for Bilateral Conditions:
    - When encountering bilateral conditions (e.g., bilateral knees), split them into separate entries
    - Example: "bilateral knees" should become "left knee" and "right knee" with their respective ratings
    - Each side may have different WPI and pain ratings
    
    Important Instructions for Dental/MMI:
    - ALWAYS check the ENTIRE report for dental ratings or MMI, as they may appear in any section
    - Look for terms like "dental", "teeth", "mastication", "jaw"
    
    Search through the entire document carefully for these details. They may appear in different sections.
    - The occupation might be listed under employment history or work status
    - Age might be listed in patient demographics or history
    - WPI ratings are typically found in the final review section at the end of the report
    - Pain add-ons are often mentioned alongside the impairment ratings or in a separate pain discussion section
    - Dental ratings are usually in separate dental reports - make sure to check for these, they will not be in the final review with the others. 
    
    Always return your findings in this exact JSON format:
    {
        "occupation": "job title",
        "age": number,
        "body_parts": {
            "body part name": {
                "wpi": number,
                "pain": number (0-3)
            },
            "left body part": {
                "wpi": number,
                "pain": number (0-3)
            },
            "right body part": {
                "wpi": number,
                "pain": number (0-3)
            }
        },
        "dental": {
            "wpi": number,
            "pain": number (0-3),
            "location": "page/line reference"
        }
    }
    
    For pain ratings:
    - Only include if explicitly mentioned in the report
    - Maximum value is 3%
    - If no pain rating is mentioned for a body part, use 0
    - Look for terms like "pain add-on", "pain impairment", or "for pain"
    
    For dental ratings:
    - Check for separate dental reports
    - Look for dental MMI status
    - Extract dental WPI ratings if present
    - Include pain add-ons for dental if mentioned
    
    If you can't find a value, use null. Never skip fields or change the format.
    
    Example response for bilateral condition:
    {
        "occupation": "Construction Worker",
        "age": 45,
        "body_parts": {
            "left knee/LEG-LENGTH": {"wpi": 15, "pain": 2},
            "right knee/LEG-LENGTH": {"wpi": 12, "pain": 1},
            "spine/Cervical - Diagnosis-related Estimate (DRE)": {"wpi": 8, "pain": 3}
        },
        "dental/MASTIFICATION": {
            "wpi": 5,
            "pain": 1,
            "location": "Page 1, Line 12"
        }
    }"""
    elif mode == "Summarize Report":
        return """You are a QME assistant specialized in analyzing medical reports and providing concise summaries with source references.
        
        Please analyze the medical report and provide a clear, organized summary that includes:
        1. Claim Information
           - Claim numbers
           - Date of injury
           - Insurance carrier
           - Claims administrator
           
        2. Patient Demographics
           - Name
           - Age/DOB
           - Gender
           - Dominant hand
           
        3. Employment Information
           - Current occupation
           - Employer
           - Length of employment
           - Work status
           
        4. Injury Details
           - How injury occurred
           - Initial symptoms
           - Body parts affected
           
        5. Medical History
           - Prior injuries/conditions
           - Treatment history
           - Surgeries
           - Medications
           
        6. Physical Examination Findings
           - Detailed findings for each body part
           - Range of motion measurements
           - Strength testing
           - Special tests
           
        7. Diagnostic Studies
           - X-rays
           - MRIs
           - CT scans
           - EMG/NCV studies
           
        8. Diagnosis
           - Primary diagnosis
           - Secondary conditions
           - Complications
           
        9. MMI Status
           - Date of MMI
           - Body parts at MMI
           - Body parts not at MMI
           - Dental MMI status (check separate reports)
           
        10. Impairment Ratings
            - WPI ratings by body part
            - Pain add-ons
            - Dental ratings (from separate reports)
            - For bilateral conditions, specify left and right ratings separately
            
        11. Treatment Recommendations
            - Current treatment
            - Future medical care
            - Work restrictions
            
        12. Pain Assessment
            - Pain levels
            - Pain distribution
            - Pain factors
            - Impact on activities
        
        For each piece of information you include in the summary:
        - Add a reference in parentheses at the end of each statement showing (Page X, Line Y)
        - If information spans multiple lines, show the range (Page X, Lines Y-Z)
        - If information is from multiple locations, list all references
        - For dental information, specify which report it came from
        
        Example format:
        ### Claim Information
        - Claim #: WC123456789 (Page 1, Line 5)
        - Date of injury: 01/15/2024 (Page 1, Line 8)
        - Insurance carrier: ABC Insurance (Page 1, Line 10)
        
        ### Injury Details
        - Patient slipped on wet floor while carrying boxes (Page 2, Lines 15-18)
        - Immediate onset of low back pain radiating to right leg (Page 2, Lines 20-22, Page 5, Line 8)
        
        ### Dental Information
        - From separate dental report dated 12/15/2024:
        - Multiple tooth fractures (Dental Report Page 2, Line 15)
        - 5% WPI for dental injuries (Dental Report Page 4, Line 10)
        
        Use the file_search tool to search through the document for each section.
        Always verify the exact page and line numbers before including them in your summary.
        
        Format your response in markdown with appropriate headers and bullet points.
        Be concise but thorough, focusing on the most relevant information."""
    else:
        return """You are a medical report processing assistant. Your task is to extract impairment ratings and related information from medical reports.

Please note the following key points:

1. Body Parts and Impairment Codes:
   Use these exact names when referring to body parts. Each body part is listed with its corresponding impairment code:

   Spine and Nervous System:
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

2. Rating String Format:
   For each body part, provide a rating string in this format:
   - Example: "15.01.01.00 - 8 - [1.4]12 - 410F - 15%"
   Where:
   - First part is the impairment code
   - Second part is the standard wpi + pain wpi = base rating
   - Third part is the base rating [  multiplied by 1.4]
   - Fourth part is the occupational adjustment
   - Fifth part is the age_adjusted which is the final percentage

3. Final PD Calculation:
   - List each body part's final PD percentage
   - Show the combined value calculations
   - Provide the final combined PD percentage
   - Calculate the PD payout
     - Weeks of PD 529
     - Age on DOI 65
     - PD Weekly Rate:$290.00
     - Total PD Payout
       

4. Future Medical Costs:
   For each body part that requires future medical care:
   - Estimate annual medical costs based on:
     * Medication costs
     * Follow-up visits
     * Physical therapy
     * Potential procedures
   - Project costs over 10 years with 3% annual inflation
   - Show total projected medical costs

5. Output Format:
   Please provide your analysis in this structure:
   ```json
   {
     "ratings": {
       "body_part_1": {
         "rating_string": "15.01.01.00 - 13 - [1.4]8 - 410F - 15%",
      
       },
       "body_part_2": {
         ...
       }
     },
     "combined_values": {
       "15 C 10 = 24%",
       "final_pd": 24,
       "weeks": 529,
       "rate": 290,
       "total_pd_payment": 153482
     },
     "future_medical": {
       "total_annual_cost": 8000,
       "total_ten_year_cost": 92000,
     }
   }
   ```

6. Bilateral Conditions:
   - When you encounter bilateral conditions (e.g., "bilateral knees"), 
   - Example: "right knee and left knees" because bilateral knees.

7. References:
   - Document the page and line numbers for all ratings
   - Include references for any future medical recommendations

Please format your responses in a clear, structured way, using the JSON format shown above. Always include references to where in the report (page/line numbers) you found each piece of information."""

def find_occupation_group(occupation):
    """Find occupation group number from occupation title"""
    if not occupation:
        return None
    try:
        # Convert occupation to lowercase for case-insensitive comparison
        occupation = occupation.lower().strip()
        
        # Search for occupation in the dataframe
        result = occupations[occupations['occupation_title'].str.lower().str.contains(occupation, na=False)]
        
        if not result.empty:
            # Return the group number as a string
            return str(result['occupational_adjustment.group_number'].iloc[0])
            
        # If not found, try searching with more flexible matching
        words = occupation.split()
        for word in words:
            if len(word) > 3:  # Only search for words longer than 3 characters
                result = occupations[occupations['occupation_title'].str.lower().str.contains(word, na=False)]
                if not result.empty:
                    st.info(f"Found occupation group using partial match: {result['occupation_title'].iloc[0]}")
                    return str(result['occupational_adjustment.group_number'].iloc[0])
        
        st.warning(f"No occupation group found for '{occupation}'. Please check the occupation title.")
        return None
    except Exception as e:
        st.error(f"Error finding occupation group: {str(e)}")
        return None

def find_impairment_variant(occupation_group, body_part):
    """Find impairment code and variant based on occupation group and body part"""
    try:
        # Normalize body part name
        body_part = body_part.upper().strip()
        occupation_group = str(occupation_group)
        
        # Handle bilateral conditions
        if body_part.startswith('LEFT ') or body_part.startswith('RIGHT '):
            search_part = body_part.split(' ', 1)[1]  # Remove 'LEFT' or 'RIGHT'
        else:
            search_part = body_part
            
        # Map common body part names to their variants.csv equivalents
        body_part_mapping = {
            # Spine conditions
            'CERVICAL SPINE': 'SPINE-DRE-ROM',
            'LUMBAR SPINE': 'SPINE-DRE-ROM',
            'THORACIC SPINE': 'SPINE-DRE-ROM',
            'SPINE': 'SPINE-DRE-ROM',
            'NECK': 'SPINE-DRE-ROM',
            'LOW BACK': 'SPINE-DRE-ROM',
            'LOWER BACK': 'SPINE-DRE-ROM',
            'UPPER BACK': 'SPINE-DRE-ROM',
            'MID BACK': 'SPINE-DRE-ROM',
            'BACK': 'SPINE-DRE-ROM',
            'C-SPINE': 'SPINE-DRE-ROM',
            'L-SPINE': 'SPINE-DRE-ROM',
            'T-SPINE': 'SPINE-DRE-ROM',
            
            # Upper extremities
            'SHOULDER': 'SHOULDER-ROM',
            'ELBOW': 'ELBOW-ROM',
            'WRIST': 'WRIST-ROM',
            'GRIP': 'ARM-GRIP/PINCH',
            'PINCH': 'ARM-GRIP/PINCH',
            
            # Lower extremities
            'ANKLE': 'ANKLE',
            'HIP': 'HIP',
            'KNEE': 'KNEE',
            'LEG': 'PERIPH - LE',
            'ARM': 'PERIPH - UE',
            
            # Other common terms
            'MASTICATION': 'MASTICATION',
            'JAW': 'MASTICATION',
            'TEETH': 'MASTICATION',
            'TMJ': 'MASTICATION'
        }
        
        # Convert body part name if it's in our mapping
        for common_name, variant_name in body_part_mapping.items():
            if common_name in search_part:
                search_part = variant_name
                break
        
        # Search for variant with mapped name
        variant_match = variants[
            (variants['Occupational_Group'].astype(str) == occupation_group) &
            (variants['Body_Part'] == search_part)
        ]
        
        if not variant_match.empty:
            return variant_match.iloc[0]['Impairment_Code'], variant_match.iloc[0]['Variant']
        
        # If exact match not found, try partial match
        variant_match = variants[
            (variants['Occupational_Group'].astype(str) == occupation_group) &
            (variants['Body_Part'].str.contains(search_part, na=False))
        ]
        
        if not variant_match.empty:
            return variant_match.iloc[0]['Impairment_Code'], variant_match.iloc[0]['Variant']
        
        # If still no match, try searching without occupation group
        variant_match = variants[
            variants['Body_Part'].str.contains(search_part, na=False)
        ]
        
        if not variant_match.empty:
            return variant_match.iloc[0]['Impairment_Code'], variant_match.iloc[0]['Variant']
        
        # Special handling for dental/mastication
        dental_terms = ['DENTAL', 'TEETH', 'MASTICATION', 'JAW', 'MOUTH']
        if any(term in body_part for term in dental_terms):
            # Look for mastication-related codes
            variant_match = variants[
                variants['Body_Part'].str.contains('MASTIC|JAW|DENTAL', na=False, regex=True)
            ]
            if not variant_match.empty:
                return variant_match.iloc[0]['Impairment_Code'], variant_match.iloc[0]['Variant']
            # If no specific dental code found, return default
            return 'DENTAL', 'A'
        
        st.warning(f"No variant found for occupation group '{occupation_group}' and body part '{body_part}'")
        return None, None
    except Exception as e:
        st.error(f"Error finding variant: {str(e)}")
        return None, None

def calculate_occupational_adjustment(wpi, variant):
    """Calculate occupational adjustment using the occupational_adjustments CSV"""
    if not wpi or not variant:
        return wpi
        
    try:
        # First multiply WPI by 1.4
        adjusted_wpi = wpi * 1.4
        # Round to nearest integer
        adjusted_wpi = round(adjusted_wpi)
        
        # Get the row for this WPI value
        adjustment_row = occupational_adjustment[occupational_adjustment['rating_percent'] == adjusted_wpi]
        
        if not adjustment_row.empty:
            # Get the adjustment value from the variant column
            adjusted_value = adjustment_row[variant].iloc[0]
            st.write(f"Base WPI: {wpi}% → Adjusted WPI (×1.4): {adjusted_wpi}% → After occupational variant {variant}: {adjusted_value}%")
            return adjusted_value
            
        st.warning(f"No occupational adjustment found for WPI {adjusted_wpi}% and variant {variant}")
        return adjusted_wpi
    except Exception as e:
        st.error(f"Error calculating occupational adjustment: {str(e)}")
        return wpi

def calculate_age_adjustment(pd_value, age):
    """Calculate age adjustment using the age_adjustments CSV"""
    if not pd_value or not age:
        return pd_value
        
    try:
        age = int(age)
        pd_value = round(pd_value)  # Round to nearest integer
        
        # Find the appropriate age column
        if age <= 21:
            age_column = '21_and_under'
        elif age >= 62:
            age_column = '62_and_over'
        else:
            # Calculate the age range
            start_age = (age // 5) * 5
            if start_age % 10 == 0:
                start_age += 2
            end_age = start_age + 4
            age_column = f'{start_age}_to_{end_age}'
        
        # Get the row for this PD value
        adjustment_row = age_adjustments[age_adjustments['wpi_percent'] == pd_value]
        
        if not adjustment_row.empty:
            # Get the adjustment value from the age column
            adjusted_value = adjustment_row[age_column].iloc[0]
            st.write(f"Before age adjustment: {pd_value}% → After age adjustment ({age} years): {adjusted_value}%")
            return adjusted_value
            
        st.warning(f"No age adjustment found for PD {pd_value}% and age {age}")
        return pd_value
    except Exception as e:
        st.error(f"Error calculating age adjustment: {str(e)}")
        return pd_value

def combine_ratings(ratings):
    """Combine multiple ratings using the Combined Values Chart (CVC) method"""
    if not ratings:
        return 0
        
    # Sort ratings in descending order
    ratings = sorted(ratings, reverse=True)
    
    # Start with the largest rating
    total = ratings[0]
    
    # Combine each subsequent rating
    for i in range(1, len(ratings)):
        current = ratings[i]
        # CVC formula: A + B(1-A/100)
        total = total + current * (1 - total/100)
    
    return round(total, 4)

def format_currency(amount):
    """Format amount as currency"""
    return f"${amount:,.2f}"

def setup_vector_store(client):
    """Set up vector store for medical reports"""
    try:
        # Create a vector store for medical reports if it doesn't exist
        vector_stores = client.beta.vector_stores.list()
        for store in vector_stores.data:
            if store.name == "Medical Reports":
                return store
                
        vector_store = client.beta.vector_stores.create(
            name="Medical Reports"
        )
        return vector_store
    except Exception as e:
        st.error(f"Error setting up vector store: {str(e)}")
        return None

def setup_assistant(client, vector_store_id):
    """Set up assistant with file search capability"""
    try:
        # Create assistant with file search capability
        assistant = client.beta.assistants.create(
            name="Medical Report Analyst",
            instructions=get_assistant_instructions(),
            model="gpt-4o",
            tools=[{"type": "file_search"}],
            tool_resources={"file_search": {"vector_store_ids": [vector_store_id]}}
        )
        return assistant
    except Exception as e:
        st.error(f"Error setting up assistant: {str(e)}")
        return None

def process_report(report_text, age, occupation, injury_date, client=None, mode="ratings"):
    """Process the report text and return structured results"""
    try:
        if not client:
            st.error("OpenAI client not initialized. Please add your API key in Settings.")
            return None
            
        # Set up vector store and assistant
        vector_store = setup_vector_store(client)
        if not vector_store:
            return None
            
        # Upload report text as a file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt') as f:
            f.write(report_text)
            f.flush()
            
            report_file = client.files.create(
                file=open(f.name, 'rb'),
                purpose="assistants"
            )
            
        # Add file to vector store
        file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
            vector_store_id=vector_store.id,
            files=[open(f.name, 'rb')]
        )
        
        # Create assistant with file search
        assistant = setup_assistant(client, vector_store.id)
        if not assistant:
            return None
            
        # Create thread with the report file
        content = ""
        if mode == "ratings":
            content = f"""Please analyze this medical report and provide:
1. All body parts with their WPI and pain ratings
2. Final combined PD rating
3. Future medical costs estimate over 10 years
4. PD payment calculation

Patient age: {age}
Occupation: {occupation}
Date of injury: {injury_date}"""
        else:
            content = f"""Please provide a comprehensive summary of this medical report, including:
1. Patient demographics and history
2. Key findings and diagnoses
3. Treatment recommendations
4. Work restrictions and limitations
5. Future medical needs
6. Prognosis

Please organize the summary in a clear, well-structured format with appropriate headings."""
            
        thread = client.beta.threads.create(
            messages=[{
                "role": "user",
                "content": content,
                "attachments": [{"file_id": report_file.id, "tools": [{"type": "file_search"}]}]
            }]
        )
        
        # Create and run the analysis
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant.id
        )
        
        # Wait for completion
        while True:
            run = client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )
            if run.status == "completed":
                break
            elif run.status in ["failed", "cancelled", "expired"]:
                st.error(f"Analysis failed with status: {run.status}")
                return None
            time.sleep(1)
            
        # Get the results
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        for msg in messages.data:
            if msg.role == "assistant":
                content = msg.content[0].text.value
                if mode == "ratings":
                    # Parse the assistant's response into our results format
                    return parse_assistant_response(content)
                else:
                    # Return the summary as is
                    return content
                
        return None
        
    except Exception as e:
        st.error(f"Error processing report: {str(e)}")
        return None

def parse_assistant_response(response_text):
    """Parse the assistant's response into structured results"""
    try:
        # Initialize results dictionary
        results = {
            "ratings": {},
            "combined_values": {},
            "future_medical": {
                "total_annual_cost": 0,
                "total_ten_year_cost": 0,
                "breakdown_by_body_part": {}
            }
        }
        
        # Split response into sections
        sections = response_text.split("\n\n")
        
        for section in sections:
            if ":" in section:
                # Parse body part ratings
                if "WPI" in section and "pain" in section:
                    try:
                        body_part = section.split(":")[0].strip()
                        # Extract WPI and pain values
                        wpi_match = re.search(r"(\d+)%\s*WPI", section)
                        pain_match = re.search(r"\+\s*(\d+)%\s*pain", section)
                        
                        base_wpi = float(wpi_match.group(1)) if wpi_match else 0
                        pain_add = float(pain_match.group(1)) if pain_match else 0
                        
                        # Add to results
                        results["ratings"][body_part] = {
                            "rating_string": section.strip(),
                            "final_pd": base_wpi + pain_add,
                            "annual_medical_cost": estimate_annual_medical_cost(body_part, base_wpi),
                            "location": "AI extracted"
                        }
                    except Exception as e:
                        st.warning(f"Could not parse rating: {section}")
                        continue
                        
                # Parse combined values
                elif "Combined PD:" in section:
                    try:
                        pd_match = re.search(r"Combined PD:\s*(\d+\.?\d*)%", section)
                        if pd_match:
                            final_pd = float(pd_match.group(1))
                            results["combined_values"]["final_pd"] = final_pd
                    except Exception as e:
                        st.warning(f"Could not parse combined PD: {section}")
                        
                # Parse future medical costs
                elif "Future Medical Costs:" in section:
                    try:
                        annual_match = re.search(r"Annual Cost:\s*\$(\d+,?\d*\.?\d*)", section)
                        ten_year_match = re.search(r"10-Year Projection:\s*\$(\d+,?\d*\.?\d*)", section)
                        
                        if annual_match:
                            results["future_medical"]["total_annual_cost"] = float(annual_match.group(1).replace(",", ""))
                        if ten_year_match:
                            results["future_medical"]["total_ten_year_cost"] = float(ten_year_match.group(1).replace(",", ""))
                    except Exception as e:
                        st.warning(f"Could not parse medical costs: {section}")
        
        return results
        
    except Exception as e:
        st.error(f"Error parsing assistant response: {str(e)}")
        return None

def estimate_annual_medical_cost(body_part, severity):
    """Estimate annual medical costs based on body part and severity"""
    base_costs = {
        "SPINE-DRE-ROM": 5000,
        "KNEE": 3000,
        "SHOULDER": 3000,
        "ELBOW": 2000,
        "WRIST": 2000,
        "ANKLE": 2500,
        "HIP": 4000
    }
    
    # Get base cost or default to 2000
    base = base_costs.get(body_part.upper(), 2000)
    
    # Adjust based on severity (WPI percentage)
    severity_multiplier = 1 + (severity / 100)
    
    return round(base * severity_multiplier)

def calculate_ten_year_cost(annual_cost, inflation_rate=0.03):
    """Calculate 10-year cost with inflation"""
    total = 0
    current_cost = annual_cost
    
    for _ in range(10):
        total += current_cost
        current_cost *= (1 + inflation_rate)
    
    return round(total)

def format_combined_values_calculation(ratings):
    """Format the combined values calculation as a string"""
    values = [f"{v['final_pd']}%" for v in ratings.values()]
    return " C ".join(values)

def show_history():
    """Display processing history"""
    if 'history' not in st.session_state or not st.session_state.history:
        st.info("No processing history yet")
        return
        
    st.write("### Processing History")
    for entry in reversed(st.session_state.history):
        with st.expander(f"{entry['timestamp']} - {entry['file_name']} ({entry['mode']})"):
            if entry['mode'] == "Calculate WPI Ratings":
                st.json(entry['results'])
            else:
                st.markdown(entry['summary'])

def show_settings():
    """Display settings page"""
    st.write("### Settings")
    st.write("OpenAI API Key is configured.")

def show_about():
    """Display about page"""
    st.write("### About")
    st.write("""
    This application helps process QME medical reports for workers' compensation cases.
    
    Features:
    - Calculate WPI ratings and PD values
    - Generate comprehensive medical summaries
    - Track processing history
    """)

def main():
    """Main application"""
    st.title("Workers' Compensation Rating Calculator")
    
    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Process Report", "History", "Settings", "About"])
    
    with tab1:
        # Mode selection
        mode = st.radio(
            "Select Processing Mode",
            ["Calculate WPI Ratings", "Generate Medical Summary"],
            key="processing_mode"
        )
        
        # File upload
        uploaded_file = st.file_uploader("Upload QME Report PDF", type=["pdf"])
        
        if uploaded_file:
            st.write("Processing uploaded report...")
            
            try:
                # Initialize OpenAI client
                client = OpenAI()
                
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
                    name="QME Report Store"
                )
                st.info("Vector store created")
                
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
                    name="QME Assistant",
                    instructions=get_assistant_instructions(mode),
                    tools=[{"type": "file_search"}],
                    model="gpt-4o-mini",
                    tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}}
                )
                st.info("Assistant created")
                
                # Create thread and message
                thread = client.beta.threads.create()
                message = client.beta.threads.messages.create(
                    thread_id=thread.id,
                    role="user",
                    content="Please analyze this medical report according to the instructions provided."
                )
                
                # Run assistant
                with st.spinner("Analyzing report..."):
                    run = client.beta.threads.runs.create_and_poll(
                        thread_id=thread.id,
                        assistant_id=assistant.id
                    )
                
                if run.status == "completed":
                    messages = client.beta.threads.messages.list(thread_id=thread.id)
                    response_text = messages.data[0].content[0].text.value
                    
                    if mode == "Calculate WPI Ratings":
                        try:
                            # Extract JSON data
                            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                            if not json_match:
                                st.error("Could not find JSON data in response")
                                st.stop()
                                
                            extracted_data = json.loads(json_match.group())
                            st.write("### Extracted Data")
                            st.json(extracted_data)
                            
                            # Add to history
                            history_entry = {
                                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                'file_name': uploaded_file.name,
                                'mode': mode,
                                'results': extracted_data
                            }
                            if 'history' not in st.session_state:
                                st.session_state.history = []
                            st.session_state.history.append(history_entry)
                            
                        except Exception as e:
                            st.error(f"Error processing ratings: {str(e)}")
                    else:
                        # Display medical summary
                        st.markdown("## Medical Report Summary")
                        st.markdown(response_text)
                        
                        # Add download button for the summary
                        st.download_button(
                            "Download Summary",
                            response_text,
                            file_name="medical_summary.txt",
                            mime="text/plain"
                        )
                        
                        # Add to history
                        history_entry = {
                            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'file_name': uploaded_file.name,
                            'mode': mode,
                            'summary': response_text
                        }
                        if 'history' not in st.session_state:
                            st.session_state.history = []
                        st.session_state.history.append(history_entry)
                else:
                    st.error(f"Run failed with status: {run.status}")
                    if hasattr(run, 'last_error'):
                        st.error(f"Error: {run.last_error}")
                        
            except Exception as e:
                st.error(f"Error: {str(e)}")
                
            finally:
                # Clean up temporary file
                if os.path.exists("temp_file.pdf"):
                    os.remove("temp_file.pdf")
    
    with tab2:
        show_history()
        
    with tab3:
        show_settings()
        
    with tab4:
        show_about()

if __name__ == "__main__":
    main()
