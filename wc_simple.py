import streamlit as st
from openai import OpenAI
import tempfile
import os
import json
import re
import psycopg2
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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
            # Re-raise as a different type to prevent connection retry loops
            raise RuntimeError(f"Failed to connect to database: {str(e)}")

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if self.cursor:
                self.cursor.close()
            if self.connection:
                if exc_type is None:
                    # Only commit if no exception occurred
                    self.connection.commit()
                self.connection.close()
        except psycopg2.Error as e:
            st.error(f"Error closing database connection: {str(e)}")

def fetch_age_adjustment(wpi_percent):
    """Fetch age adjustments based on the WPI percent."""
    try:
        with DatabaseConnection() as (connection, cursor):
            query = "SELECT * FROM public.age_adjustment WHERE wpi_percent = %s;"
            cursor.execute(query, (wpi_percent,))
            return cursor.fetchall()
    except RuntimeError:
        return []  # Return empty list on connection error

def fetch_bodypart_impairment(bodypart_name):
    """Fetch impairment codes, titles, and descriptions based on a generic body part name."""
    try:
        with DatabaseConnection() as (connection, cursor):
            query = """
            SELECT "Code", "Title", "Description" 
            FROM public.bodypart_impairment 
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
            query = "SELECT * FROM public.occupations WHERE occupation_title = %s;"
            cursor.execute(query, (occupation_title,))
            return cursor.fetchall()
    except RuntimeError:
        return []

def fetch_occupational_adjustments(rating_percent):
    """Fetch occupational adjustments based on the rating percent."""
    try:
        with DatabaseConnection() as (connection, cursor):
            query = "SELECT * FROM public.occupational_adjustments WHERE rating_percent = %s;"
            cursor.execute(query, (rating_percent,))
            return cursor.fetchall()
    except RuntimeError:
        return []

def fetch_variants(body_part):
    """Fetch variants from the first variants table based on the body part."""
    try:
        with DatabaseConnection() as (connection, cursor):
            query = "SELECT * FROM public.variants WHERE \"Body_Part\" = %s;"
            cursor.execute(query, (body_part,))
            return cursor.fetchall()
    except RuntimeError:
        return []

def fetch_variants_2(body_part):
    """Fetch variants from the second variants table based on the body part."""
    try:
        with DatabaseConnection() as (connection, cursor):
            query = "SELECT * FROM public.variants_2 WHERE \"Body_Part\" = %s;"
            cursor.execute(query, (body_part,))
            return cursor.fetchall()
    except RuntimeError:
        return []

# OpenAI API key
API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=API_KEY)

def get_assistant_instructions(mode):
    """Get instructions for the assistant based on mode"""
    if mode == "Calculate WPI Ratings":
        return """You are a medical report analyzer specializing in workers' compensation cases.
        Your task is to extract the following raw data from the medical report:
        1. Patient's age
        2. Patient's occupation and job duties
        3. For each injured body part:
           - WPI rating
           - Pain add-on (0-3)
           - Any relevant medical findings or restrictions
        
        Format your response as a JSON object with this structure:
        {
            "patient": {
                "age": number,
                "occupation": {
                    "title": string,
                    "duties": string
                }
            },
            "impairments": [
                {
                    "body_part": string,
                    "wpi": number,
                    "pain": number,
                    "findings": string
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

def main():
    """Main application"""
    st.title("Medical Report Processor")
    
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
                        # Log the raw response for debugging
                        st.write("Raw response:", response_text)
                        
                        # Handle direct JSON input or JSON within markdown
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
                        st.write("Extracted JSON string:", json_str)
                        
                        # Parse the JSON string
                        try:
                            if isinstance(json_str, str):
                                extracted_data = json.loads(json_str)
                            
                            # Validate required fields
                            if "patient" not in extracted_data:
                                raise ValueError("Missing 'patient' section in extracted data")
                            if "age" not in extracted_data["patient"]:
                                raise ValueError("Missing patient age in extracted data")
                            if "occupation" not in extracted_data["patient"]:
                                raise ValueError("Missing patient occupation in extracted data")
                            if "impairments" not in extracted_data:
                                raise ValueError("Missing 'impairments' section in extracted data")
                            if not extracted_data["impairments"]:
                                raise ValueError("No impairments found in extracted data")
                            
                            # Validate each impairment
                            for i, imp in enumerate(extracted_data["impairments"]):
                                required_fields = ["body_part", "wpi", "pain", "findings"]
                                missing = [f for f in required_fields if f not in imp]
                                if missing:
                                    raise ValueError(f"Impairment {i+1} missing required fields: {', '.join(missing)}")
                        except json.JSONDecodeError as je:
                            st.error(f"JSON parsing error: {str(je)}")
                            st.error(f"Error position: Line {je.lineno}, Column {je.colno}")
                            st.error(f"Error context: {je.doc[max(0, je.pos-20):je.pos+20]}")
                            st.stop()
                        
                        # Process extracted data
                        processed_data = {
                            "body_parts": {},
                            "combined_values": {},
                            "future_medical": {},
                            "occupation": {}
                        }
                        
                        # Process occupation
                        if "patient" in extracted_data and "occupation" in extracted_data["patient"]:
                            occupation = extracted_data["patient"]["occupation"]
                            processed_data["occupation"] = occupation
                            occupation_details = fetch_occupations(occupation["title"])
                            if occupation_details:
                                processed_data["occupation"]["details"] = occupation_details
                        
                        # Process impairments
                        total_wpi = 0
                        for impairment in extracted_data.get("impairments", []):
                            body_part = impairment["body_part"]
                            processed_data["body_parts"][body_part] = {
                                "wpi": impairment["wpi"],
                                "pain": impairment["pain"],
                                "rating_string": impairment["findings"]
                            }
                            
                            # Get impairment details
                            impairment_details = fetch_bodypart_impairment(body_part)
                            if impairment_details:
                                processed_data["body_parts"][body_part]["impairment_details"] = impairment_details
                            
                            # Get variants
                            variants = fetch_variants(body_part)
                            if variants:
                                processed_data["body_parts"][body_part]["variants"] = variants
                            
                            variants_2 = fetch_variants_2(body_part)
                            if variants_2:
                                processed_data["body_parts"][body_part]["variants_2"] = variants_2
                            
                            # Get age adjustments
                            age = extracted_data["patient"]["age"]
                            age_adjustments = fetch_age_adjustment(int(impairment["wpi"]))
                            if age_adjustments:
                                processed_data["body_parts"][body_part]["age_adjustments"] = age_adjustments
                            
                            # Calculate adjusted WPI with pain add-on
                            adjusted_wpi = impairment["wpi"] + impairment["pain"]
                            total_wpi += adjusted_wpi
                        
                        # Calculate final PD rating with adjustments
                        base_pd = total_wpi
                        processed_data["combined_values"]["base_pd"] = base_pd
                        processed_data["combined_values"]["final_pd"] = total_wpi
                        processed_data["combined_values"]["age"] = age
                        
                        # Get occupational adjustments
                        occupational_adj = fetch_occupational_adjustments(int(total_wpi))
                        if occupational_adj:
                            processed_data["combined_values"]["occupational_adjustments"] = occupational_adj
                        
                        # Update assistant instructions for formatting
                        assistant = client.beta.assistants.update(
                            assistant_id=assistant.id,
                            instructions="""You are a medical report formatter for workers' compensation cases.
                            Format the provided data into a comprehensive report with the following sections:
                            
                            1. Patient Information
                               - Age
                               - Occupation and duties
                               - Occupational group details from database
                            
                            2. Impairment Ratings
                               For each body part:
                               - WPI rating with pain add-on
                               - Medical findings and restrictions
                               - Relevant impairment codes and descriptions from database
                               - Applicable variants from database
                               - Age-based adjustments from database
                            
                            3. Combined Values
                               - Final PD rating
                               - Occupational adjustments from database
                               - Total disability percentage
                            
                            Format the response in markdown with clear headings, bullet points, and tables where appropriate.
                            Include all database lookup results in a structured format."""
                        )
                        
                        # Send processed data for formatting
                        format_message = client.beta.threads.messages.create(
                            thread_id=thread.id,
                            role="user",
                            content=f"Format this processed workers' compensation data into a final report: {json.dumps(processed_data)}"
                        )
                        
                        format_run = client.beta.threads.runs.create_and_poll(
                            thread_id=thread.id,
                            assistant_id=assistant.id
                        )
                        
                        if format_run.status == "completed":
                            format_messages = client.beta.threads.messages.list(thread_id=thread.id)
                            final_response = format_messages.data[0].content[0].text.value
                            st.write("### Final Rating Results")
                            st.markdown(final_response)
                        else:
                            st.error("Failed to format final results")
                        
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
