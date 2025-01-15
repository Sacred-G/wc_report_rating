import streamlit as st
from openai import OpenAI
import tempfile
import os
import json
import re
import psycopg2
from datetime import datetime
from supabase import create_client
from streamlit_supabase_auth import login_form, logout_button
from dotenv import load_dotenv
import uuid


# Load environment variables from .env file
load_dotenv()

# Initialize Supabase client
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')
supabase = create_client(supabase_url, supabase_key)

# Database connection parameters
db_params = {
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT')
}

class DatabaseConnection:
    """Context manager for database connections"""
    def __init__(self):
        self.connection = None
        self.cursor = None

    def __enter__(self):
        try:
            self.connection = psycopg2.connect(**db_params)
            self.cursor = self.connection.cursor()
            return self.connection, self.cursor
        except psycopg2.Error as e:
            st.error(f"Database connection error: {str(e)}")
            raise RuntimeError(f"Failed to connect to database: {str(e)}")

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if self.cursor:
                self.cursor.close()
            if self.connection:
                if exc_type is None:
                    self.connection.commit()
                self.connection.close()
        except psycopg2.Error as e:
            st.error(f"Error closing database connection: {str(e)}")

from rating_calculator import calculate_rating

def process_report(report_text):
    """Process report text to extract relevant information and calculate ratings."""
    try:
        # Extract information using pattern matching
        occupation_match = re.search(r'Occupation:\s*([^\n]+)', report_text)
        date_of_injury_match = re.search(r'Date of Injury:\s*(\d{1,2}/\d{1,2}/\d{4})', report_text)
        wpi_match = re.search(r'WPI:\s*(\d+(?:\.\d+)?)', report_text)
        bodypart_match = re.search(r'Body Part:\s*([^\n]+)', report_text)

        # Get the matched values or set defaults
        occupation = occupation_match.group(1) if occupation_match else "Unknown"
        date_of_injury = date_of_injury_match.group(1) if date_of_injury_match else "01/01/2000"
        wpi = float(wpi_match.group(1)) if wpi_match else 0.0
        bodypart = bodypart_match.group(1) if bodypart_match else "Unknown"

        # Convert date format to YYYY-MM-DD for database
        date_obj = datetime.strptime(date_of_injury, '%m/%d/%Y')
        formatted_date = date_obj.strftime('%Y-%m-%d')
        
        # Calculate adjusted value based on occupational adjustments
        occupational_adj = fetch_occupational_adjustments(int(wpi))
        adjusted_value = wpi * (occupational_adj[0][1] if occupational_adj else 1.0)
        
        # Calculate rating using Supabase
        rating_result = calculate_rating(
            supabase=supabase,
            occupation=occupation,
            bodypart=bodypart,
            age_injury=formatted_date,
            wpi=wpi,
            adjusted_value=adjusted_value
        )
        
        if rating_result['status'] == 'error':
            raise Exception(rating_result['message'])
            
        # Get calculation results from Supabase
        calc_results = get_calculation_results(rating_result['details']['group_number'])
        
        # Format results for AI presentation
        results_for_ai = {
            "input_data": {
                "occupation": occupation,
                "bodypart": bodypart,
                "age_injury": date_of_injury,
                "wpi": wpi,
                "adjusted_value": adjusted_value
            },
            "rating_details": rating_result['details'],
            "final_value": rating_result['final_value'],
            "calculation_results": calc_results
        }
        
        # Have AI format the results
        formatted_results = format_results_with_ai(results_for_ai)
        
        return formatted_results
        
    except Exception as e:
        st.error(f"Error processing report data: {str(e)}")
        return None

def format_results_with_ai(results):
    """Use OpenAI to format the results in a presentable way."""
    try:
        # Create message for AI formatting
        format_prompt = f"""
        Please format these workers compensation calculation results in a clear, professional way:
        
        {json.dumps(results, indent=2)}
        
        Format the response with:
        1. A summary section showing key values
        2. A detailed breakdown of calculations
        3. Any relevant notes or explanations
        
        Use markdown formatting to make it visually appealing and easy to read.
        """
        
        # Get AI response
        messages = [{"role": "user", "content": format_prompt}]
        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0
        )
        
        # Return formatted results
        return response.choices[0].message.content
        
    except Exception as e:
        st.error(f"Error formatting results: {str(e)}")
        return json.dumps(results, indent=2)

def fetch_age_adjustment(wpi_percent):
    """Fetch age adjustments based on the WPI percent."""
    try:
        with DatabaseConnection() as (connection, cursor):
            query = "SELECT * FROM workers_comp.age_adjustment WHERE wpi_percent = %s;"
            cursor.execute(query, (wpi_percent,))
            return cursor.fetchall()
    except RuntimeError:
        return []

def fetch_bodypart_impairment(bodypart_name):
    """Fetch impairment codes, titles, and descriptions based on a generic body part name."""
    try:
        with DatabaseConnection() as (connection, cursor):
            query = """
            SELECT "Code", "Title", "Description" 
            FROM workers_comp.bodypart_impairment 
            WHERE "Title" ILIKE %s OR "Description" ILIKE %s;
            """
            search_pattern = f'%{bodypart_name}%'
            cursor.execute(query, (search_pattern, search_pattern))
            return cursor.fetchall()
    except RuntimeError:
        return []

def fetch_occupations(occupation_title):
    """Fetch occupations based on the occupation title."""
    try:
        with DatabaseConnection() as (connection, cursor):
            query = "SELECT * FROM workers_comp.occupations WHERE occupation_title = %s;"
            cursor.execute(query, (occupation_title,))
            return cursor.fetchall()
    except RuntimeError:
        return []

def fetch_occupational_adjustments(rating_percent):
    """Fetch occupational adjustments based on the rating percent."""
    try:
        with DatabaseConnection() as (connection, cursor):
            query = "SELECT * FROM workers_comp.occupational_adjustments WHERE rating_percent = %s;"
            cursor.execute(query, (rating_percent,))
            return cursor.fetchall()
    except RuntimeError:
        return []

def fetch_variants(body_part):
    """Fetch variants from the first variants table based on the body part."""
    try:
        with DatabaseConnection() as (connection, cursor):
            query = "SELECT * FROM workers_comp.variants WHERE \"Body_Part\" = %s;"
            cursor.execute(query, (body_part,))
            return cursor.fetchall()
    except RuntimeError:
        return []

def fetch_variants_2(body_part):
    """Fetch variants from the second variants table based on the body part."""
    try:
        with DatabaseConnection() as (connection, cursor):
            query = "SELECT * FROM workers_comp.variants_2 WHERE \"Body_Part\" = %s;"
            cursor.execute(query, (body_part,))
            return cursor.fetchall()
    except RuntimeError:
        return []

def store_occupational_data(occupation, bodypart, age_injury, wpi, adjusted_value):
    """Store processed report data in the occupational_data table."""
    try:
        with DatabaseConnection() as (connection, cursor):
            query = """
            INSERT INTO workers_comp.occupational_data 
            (id, occupation, bodypart, age_injury, wpi, adjusted_value)
            VALUES (nextval('occupational_data_id_seq'), %s, %s, %s, %s, %s)
            RETURNING id;
            """
            cursor.execute(query, (occupation, bodypart, age_injury, wpi, adjusted_value))
            return cursor.fetchone()[0]
    except RuntimeError as e:
        st.error(f"Error storing occupational data: {str(e)}")
        return None

def get_calculation_results(input_id):
    """Get calculation results for a given input ID."""
    try:
        with DatabaseConnection() as (connection, cursor):
            # Query the calculator_results table
            query = """
            SELECT id, input_id, total_pd, payment_weeks, 
                   weekly_rate, total_payout, created_at
            FROM workers_comp.calculator_results
            WHERE input_id = %s;
            """
            cursor.execute(query, (input_id,))
            result = cursor.fetchone()
            if result:
                return {
                    "id": result[0],
                    "input_id": result[1],
                    "total_pd": result[2],
                    "payment_weeks": result[3],
                    "weekly_rate": result[4],
                    "total_payout": result[5],
                    "created_at": result[6]
                }
            return None
    except RuntimeError as e:
        st.error(f"Error getting calculation results: {str(e)}")
        return None

# OpenAI API key
API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=API_KEY)

def get_assistant_instructions(mode):
    """Get instructions for the assistant based on mode"""
    if mode == "Calculate WPI Ratings":
        return """You are a medical report analyzer specializing in workers' compensation cases. Your task is to:
        1. Extract the following raw data from the medical report:
           - Patient's age
           - Patient's occupation and job duties
           - For each injured body part:
             - WPI rating
             - Pain add-on (0-3)
             - Any relevant medical findings or restrictions
        2. Use Medical Terminology using the following list for reference 
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

        
        Format your response as a JSON object with this structure:
        {
            "patient": {
                "age": number,
                "occupation": {
                    "title": string,
                }
            },
            "impairments": [
                {
                    "body_part": string,
                    "wpi": number,
                    "pain": number,
                }
            ]
        }"""
    else:
        return """You are a medical report summarizer specializing in workers' compensation cases.
        Please provide a comprehensive summary of the medical report including:
        1. Patient demographics and history
        2. Key findings and diagnoses
        3. Treatment recommendations
        4. Work restrictions and limitations
        5. Future medical needs
        6. Prognosis
        
        Format your response in markdown with clear headings and bullet points."""

def calculate_ratings(extracted_data):
    """Calculate ratings based on extracted data."""
    processed_data = {
        "body_parts": {},
        "combined_values": {},
        "occupation": {}
    }
    
    total_wpi = 0
    age = extracted_data["patient"]["age"]
    
    # Process occupation
    occupation = extracted_data["patient"]["occupation"]
    occupation_details = fetch_occupations(occupation["title"])
    processed_data["occupation"] = occupation
    processed_data["occupation"]["details"] = occupation_details
    
    # Process impairments
    for impairment in extracted_data.get("impairments", []):
        body_part = impairment["body_part"]
        processed_data["body_parts"][body_part] = {
            "wpi": impairment["wpi"],
            "pain": impairment["pain"],
            "rating_string": impairment["findings"]
        }
        
        # Get impairment details
        impairment_details = fetch_bodypart_impairment(body_part)
        processed_data["body_parts"][body_part]["impairment_details"] = impairment_details
        
        # Get variants
        variants = fetch_variants(body_part)
        processed_data["body_parts"][body_part]["variants"] = variants
        
        # Get age adjustments
        age_adjustments = fetch_age_adjustment(int(impairment["wpi"]))
        processed_data["body_parts"][body_part]["age_adjustments"] = age_adjustments
        
        # Calculate adjusted WPI with pain add-on
        adjusted_wpi = impairment["wpi"] + impairment["pain"]
        total_wpi += adjusted_wpi
    
    # Calculate final PD rating with adjustments
    processed_data["combined_values"]["base_pd"] = total_wpi
    occupational_adj = fetch_occupational_adjustments(int(total_wpi))
    processed_data["combined_values"]["occupational_adjustments"] = occupational_adj
    
    # Calculate age-adjusted WPI
    age_adjustment = fetch_age_adjustment(age)
    adjusted_wpi = total_wpi * 1.4 * age_adjustment[0][1]  # Assuming the first column is the adjustment factor
    processed_data["combined_values"]["age_adjusted_wpi"] = adjusted_wpi
    
    return processed_data

def initialize_session_state():
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user' not in st.session_state:
        st.session_state.user = None

def login_signup():
    st.title("Welcome to Medical Report Processor")
    
    session = login_form(
        url=supabase_url,
        apiKey=supabase_key,
        providers=["google"],
    )
    
    if session:
        st.session_state.authenticated = True
        st.session_state.user = session['user']
        # Update query param to reset url fragments
        st.experimental_set_query_params(page=["success"])
        st.rerun()

def main():
    initialize_session_state()
    
    # Show login/signup if not authenticated
    if not st.session_state.authenticated:
        login_signup()
        return
        
    # Main app content for authenticated users
    st.title("Medical Report Processor")
    
    # Add logout button and user info in sidebar
    with st.sidebar:
        if st.session_state.authenticated:
            st.write(f"Welcome {st.session_state.user.get('email', 'User')}")
            if logout_button():
                st.session_state.authenticated = False
                st.session_state.user = None
                st.rerun()
    
    # Use actual user ID from Supabase auth
    st.session_state.user_id = st.session_state.user['id']
    
    # Mode selection
    mode = st.radio(
        "Select Processing Mode",
        ["Calculate WPI Ratings", "Generate Medical Summary"]
    )
    
    # File upload
    uploaded_file = st.file_uploader("Upload Medical Report PDF", type=["pdf"])
    
    if uploaded_file:
        st.write("Processing uploaded report...")
        
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
            
            # Create thread and message for AI analysis
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
                
                if mode == "Calculate WPI Ratings":
                    try:
                        # Extract JSON data
                        try:
                            # First try parsing as direct JSON
                            json_str = response_text.strip()
                            extracted_data = json.loads(json_str)
                        except json.JSONDecodeError:
                            # If that fails, try finding JSON between markdown code blocks
                            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
                            if json_match:
                                json_str = json_match.group(1).strip()
                            else:
                                # Try finding just a JSON object
                                json_match = re.search(r'(\{[^}]+\})', response_text, re.DOTALL)
                                if not json_match:
                                    st.error("Could not find valid JSON data in response")
                                    st.write("Response text for debugging:", response_text)
                                    st.stop()
                                json_str = json_match.group(1).strip()
                        
                        # Process the report data
                        result = process_report(response_text)
                        if result:
                            st.success("Report processed successfully")
                            # Display formatted results using markdown
                            st.markdown(result)
                        
                    except Exception as e:
                        st.error(f"Error processing ratings: {str(e)}")
                else:
                    # Display medical summary
                    st.markdown("### Medical Report Summary")
                    st.markdown(response_text)
                    
                    # Add download button for the summary
                    st.download_button(
                        "Download Summary",
                        response_text,
                        file_name="medical_summary.txt",
                        mime="text/plain"
                    )
            else:
                st.error(f"Analysis failed with status: {run.status}")
                if hasattr(run, 'last_error'):
                    st.error(f"Error: {run.last_error}")
                    
        except Exception as e:
            st.error(f"Error: {str(e)}")
            
        finally:
            # Clean up temporary file
            if os.path.exists("temp_file.pdf"):
                os.remove("temp_file.pdf")
            
            # Clean up OpenAI resources
            try:
                if 'vector_store' in locals():
                    client.beta.vector_stores.delete(vector_store_id=vector_store.id)
                if 'openai_file' in locals():
                    client.files.delete(file_id=openai_file.id)
                if 'assistant' in locals():
                    client.beta.assistants.delete(assistant_id=assistant.id)
            except Exception as e:
                st.error(f"Error cleaning up OpenAI resources: {str(e)}")

if __name__ == "__main__":
    main()
