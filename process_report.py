import streamlit as st
import json
import re
import os
import logging
from datetime import datetime
from contextlib import ExitStack
import PyPDF2

from utils.auth import init_openai_client, get_assistant_instructions
from rating_calculator import calculate_rating
from utils.latex_utils import clean_latex_expression, render_latex
from utils.config import config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Store assistant and vector store as module-level variables to reuse them
_assistant = None
_vector_store = None

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

def process_report(client, get_assistant_instructions):
    """Process QME reports for ratings and summaries"""
    global _assistant, _vector_store
    
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
        
        # Use ExitStack to manage multiple resources
        with ExitStack() as stack:
            openai_file = None
            temp_filename = "temp_file.pdf"
            
            # Validate client
            if not client:
                st.error("OpenAI client is not initialized. Please check your API key.")
                return
            
            # Save uploaded file temporarily
            with open(temp_filename, "wb") as f:
                f.write(uploaded_file.getvalue())
            
            # Register cleanup of temp file
            stack.callback(lambda: os.remove(temp_filename) if os.path.exists(temp_filename) else None)
            
            # Try direct text extraction first
            use_direct_text = True
            file_extension = uploaded_file.name.split('.')[-1].lower()
            
            if file_extension.lower() == 'pdf':
                # Reset file pointer to beginning
                uploaded_file.seek(0)
                extracted_text = extract_text_from_pdf(uploaded_file)
                
                # Check if the extracted text is too large for the context window
                # The AI has a 200k context window, so we can use a much higher limit
                # We'll use a limit of 180k characters to be safe
                if len(extracted_text) > 180000:
                    st.info(f"Extracted text is too large ({len(extracted_text)} characters). Using vector store approach instead.")
                    use_direct_text = False
            else:
                # For non-PDF files, we'll need to use the vector store approach
                use_direct_text = False
                
            if use_direct_text and extracted_text:
                st.info("Using direct text extraction approach")
                
                # Create or reuse assistant without file search
                try:
                    # Create a new assistant only if we don't have one already
                    if _assistant is None:
                        _assistant = client.beta.assistants.create(
                            name="QME Assistant",
                            instructions=get_assistant_instructions(mode),
                            model=config.openai_model
                        )
                        st.info("Created new assistant")
                    else:
                        # Update the existing assistant with the current instructions
                        _assistant = client.beta.assistants.update(
                            assistant_id=_assistant.id,
                            instructions=get_assistant_instructions(mode)
                        )
                        st.info("Updated existing assistant")
                except Exception as e:
                    st.error(f"Error creating/updating assistant: {str(e)}")
                    logger.error(f"Error creating/updating assistant: {str(e)}", exc_info=True)
                    return
                
                # Create thread with the extracted text as the message
                try:
                    thread = client.beta.threads.create()
                    message = client.beta.threads.messages.create(
                        thread_id=thread.id,
                        role="user",
                        content=f"Please analyze this medical report according to the instructions provided:\n\n{extracted_text}"
                    )
                except Exception as e:
                    st.error(f"Error creating thread or message: {str(e)}")
                    logger.error(f"Error creating thread or message: {str(e)}", exc_info=True)
                    return
            else:
                st.info("Using vector store approach")
                
                # Create OpenAI file
                try:
                    openai_file = client.files.create(
                        file=open(temp_filename, "rb"),
                        purpose="assistants"
                    )
                    st.info("File uploaded successfully")
                    
                    # Register cleanup of OpenAI file
                    stack.callback(lambda: client.files.delete(file_id=openai_file.id) if openai_file else None)
                except Exception as e:
                    st.error(f"Error uploading file to OpenAI: {str(e)}")
                    logger.error(f"Error uploading file to OpenAI: {str(e)}", exc_info=True)
                    return
                
                # Create or reuse vector store for file search
                try:
                    # Create a new vector store only if we don't have one already
                    if _vector_store is None:
                        _vector_store = client.beta.vector_stores.create(
                            name="QME Report Store"
                        )
                        st.info("Created new vector store")
                    else:
                        st.info("Reusing existing vector store")
                except Exception as e:
                    st.error(f"Error creating vector store: {str(e)}")
                    logger.error(f"Error creating vector store: {str(e)}", exc_info=True)
                    return
                
                # Add file to vector store and wait for processing
                try:
                    file_batch = client.beta.vector_stores.file_batches.create_and_poll(
                        vector_store_id=_vector_store.id,
                        file_ids=[openai_file.id]
                    )
                    
                    if file_batch.status != "completed":
                        st.error(f"File processing failed with status: {file_batch.status}")
                        if hasattr(file_batch, 'error'):
                            st.error(f"Error details: {file_batch.error}")
                        return
                    
                    st.success("File processed successfully")
                except Exception as e:
                    st.error(f"Error processing file in vector store: {str(e)}")
                    logger.error(f"Error processing file in vector store: {str(e)}", exc_info=True)
                    return
                
                # Create or reuse assistant with file search enabled
                try:
                    # Create a new assistant only if we don't have one already
                    if _assistant is None:
                        _assistant = client.beta.assistants.create(
                            name="QME Assistant",
                            instructions=get_assistant_instructions(mode),
                            tools=[{"type": "file_search"}],
                            model=config.openai_model,
                            tool_resources={"file_search": {"vector_store_ids": [_vector_store.id]}}
                        )
                        st.info("Created new assistant")
                    else:
                        # Update the existing assistant with the current vector store and instructions
                        _assistant = client.beta.assistants.update(
                            assistant_id=_assistant.id,
                            instructions=get_assistant_instructions(mode),
                            tools=[{"type": "file_search"}],
                            tool_resources={"file_search": {"vector_store_ids": [_vector_store.id]}}
                        )
                        st.info("Updated existing assistant")
                except Exception as e:
                    st.error(f"Error creating/updating assistant: {str(e)}")
                    logger.error(f"Error creating/updating assistant: {str(e)}", exc_info=True)
                    return
                
                # Create thread and message
                try:
                    thread = client.beta.threads.create()
                    message = client.beta.threads.messages.create(
                        thread_id=thread.id,
                        role="user",
                        content="Please analyze this medical report according to the instructions provided."
                    )
                except Exception as e:
                    st.error(f"Error creating thread or message: {str(e)}")
                    logger.error(f"Error creating thread or message: {str(e)}", exc_info=True)
                    return
                
            # Run assistant
            try:
                with st.spinner("Analyzing report..."):
                    run = client.beta.threads.runs.create_and_poll(
                        thread_id=thread.id,
                        assistant_id=_assistant.id
                    )
            except Exception as e:
                st.error(f"Error running assistant: {str(e)}")
                logger.error(f"Error running assistant: {str(e)}", exc_info=True)
                return
            
            if run.status == "completed":
                try:
                    messages = client.beta.threads.messages.list(thread_id=thread.id)
                    response_text = messages.data[0].content[0].text.value
                except Exception as e:
                    st.error(f"Error retrieving messages: {str(e)}")
                    logger.error(f"Error retrieving messages: {str(e)}", exc_info=True)
                    return
                
                if mode == "Calculate WPI Ratings":
                    try:
                        # Parse JSON from response
                        extracted_data = extract_json_from_response(response_text)
                        st.write("### Extracted Data")
                        st.json(extracted_data)
                        
                        # Calculate rating using the updated function
                        # Convert age to date format
                        age = extracted_data.get("age")
                        current_year = datetime.now().year
                        age_injury = f"{current_year}-01-01"  # Default to January 1st of current year
                        
                        # Get impairments from the extracted data
                        impairments = extracted_data.get("impairments", [])
                        
                        # Log the extracted impairments
                        logger.info(f"Extracted impairments: {impairments}")
                        
                        # Calculate rating using the updated function
                        result = calculate_rating(
                            occupation=extracted_data.get("occupation"),
                            bodypart=impairments,  # Pass the impairments list directly
                            age_injury=age_injury,
                            wpi=0,  # Not used when bodypart is a list of dictionaries
                            pain=0   # Not used when bodypart is a list of dictionaries
                        )
                        
                        if result['status'] == 'success':
                            st.write("\n### Rating Breakdown")
                            for detail in result['details']:
                                # Generate rating string for each body part
                                impairment_code = "00.00.00.00"  # Default code, should be determined based on body part
                                base_wpi = detail['base_value'] - (detail.get('pain', 0))  # Subtract pain to get original WPI
                                adjusted_value = detail['adjusted_value']
                                occupation_group = detail['group_number']
                                variant = detail['variant']
                                final_value = detail['final_value']
                                
                                # Format the rating string
                                rating_string = f"NO APPORTIONMENT 100% ({impairment_code} - {int(base_wpi)} - [1.4]{int(adjusted_value)} - {occupation_group}{variant} - {int(final_value)}%) {int(final_value)}% {detail['body_part']}"
                                
                                st.write(f"{rating_string}")
                            st.success(f"**Final Combined Rating:** {result['final_value']}%")
                        else:
                            st.error(f"Error: {result['message']}")
                            
                    except Exception as e:
                        st.error(f"Error processing rating calculation: {str(e)}")
                        st.text("Response text:")
                        st.code(response_text)
                        logger.error(f"Error processing rating calculation: {str(e)}", exc_info=True)
                        
                else:
                    # Display medical summary
                    st.markdown("## Medical Report Summary")
                    # Clean any LaTeX expressions in the response text
                    cleaned_response = clean_latex_expression(response_text)
                    st.markdown(cleaned_response)
                    
                    # Add download button for the summary
                    st.download_button(
                        "Download Summary",
                        response_text,
                        file_name="medical_summary.txt",
                        mime="text/plain"
                    )
            else:
                st.error(f"Run failed with status: {run.status}")
                if hasattr(run, 'last_error'):
                    st.error(f"Error: {run.last_error}")
                logger.error(f"Assistant run failed with status: {run.status}")

def extract_json_from_response(response_text: str) -> dict:
    """Extract JSON data from the assistant's response text.
    
    This function uses a deterministic approach to extract JSON from various response formats.
    It tries multiple methods in a consistent order and logs which method was successful.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Log the raw response for debugging
    logger.info("Extracting JSON from response")
    logger.debug(f"Raw response length: {len(response_text)} characters")
    
    # Store all extraction attempts and their results
    extraction_attempts = []
    
    # Method 1: Direct JSON parsing
    try:
        result = json.loads(response_text)
        logger.info("Successfully parsed JSON directly")
        extraction_attempts.append(("direct_json", result))
    except json.JSONDecodeError as e:
        logger.debug(f"Direct JSON parsing failed: {str(e)}")
    
    # Method 2: Find JSON in markdown code blocks
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
    if json_match:
        try:
            result = json.loads(json_match.group(1))
            logger.info("Successfully parsed JSON from code block")
            extraction_attempts.append(("code_block", result))
        except json.JSONDecodeError as e:
            logger.debug(f"Code block JSON parsing failed: {str(e)}")
    
    # Method 3: Find any JSON-like structure with a comprehensive regex
    json_match = re.search(r'\{(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\}))*\}))*\}', response_text, re.DOTALL)
    if json_match:
        try:
            result = json.loads(json_match.group(0))
            logger.info("Successfully parsed JSON from regex")
            extraction_attempts.append(("regex", result))
        except json.JSONDecodeError as e:
            logger.debug(f"Regex JSON parsing failed: {str(e)}")
    
    # If we have any successful extractions, use the first one (most reliable method)
    if extraction_attempts:
        method, result = extraction_attempts[0]
        logger.info(f"Using extraction method: {method}")
        
        # Validate the extracted data
        if not isinstance(result, dict):
            raise ValueError(f"Extracted data is not a dictionary: {type(result)}")
        
        # Ensure required fields exist
        required_fields = ["age", "occupation", "impairments"]
        for field in required_fields:
            if field not in result:
                logger.warning(f"Missing required field '{field}' in extracted data")
                if field == "impairments":
                    result[field] = []
                else:
                    result[field] = "unknown" if field == "occupation" else 0
        
        return result
    
    # If we got here, we couldn't find valid JSON
    error_message = "Could not extract valid JSON from the assistant's response."
    logger.error(error_message)
    raise ValueError(error_message)
