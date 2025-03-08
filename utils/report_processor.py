import os
import json
import re
import io
from typing import Dict, Any, List, Union
import streamlit as st
from openai import OpenAI
import PyPDF2
from utils.config import config
from utils.auth import init_openai_client, get_assistant_instructions

from utils.database import (
    get_occupation_group,
    get_variant_for_impairment,
    get_occupational_adjusted_wpi,
    get_age_adjusted_wpi
)
from utils.calculations import combine_wpi_values
from utils.formatting import format_rating_output
import logging

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
    """Calculate permanent disability payout based on final PD percentage."""
    weeks = calculate_payment_weeks(final_pd_percent)
    pd_weekly_rate = 290.0
    total_pd_dollars = weeks * pd_weekly_rate
    
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
            "wpi": detail['age_adjusted_wpi'] if detail.get('apportioned_wpi') is None else detail['apportioned_wpi']
        })
    
    # Calculate life pension if applicable
    life_pension_rate = None
    life_pension_max_earnings = None
    if final_pd_percent >= 70:
        life_pension_max_earnings = 515.38  # Life Pension Statutory Max
        life_pension_rate = 85.0  # Standard life pension rate
    
    return {
        "final_pd_percent": round(final_pd_percent, 2),
        "weeks": round(weeks, 2),
        "pd_weekly_rate": pd_weekly_rate,
        "total_pd_dollars": round(total_pd_dollars, 2),
        "formatted_impairments": formatted_impairments,
        "life_pension_weekly_rate": life_pension_rate,
        "life_pension_max_earnings": life_pension_max_earnings,
        "age": age
    }

def process_extracted_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Process the extracted data from medical report."""
    try:
        age = data["age"]
        occupation = data["occupation"]
        impairments = data["impairments"]

        # Check if occupation is in format like "380H" and extract variant if so
        occupation_variant = None
        if occupation and len(occupation) >= 3:
            if occupation[:-1].isdigit() and occupation[-1].isalpha():
                occupation_variant = occupation[-1].upper()
                # Note: get_occupation_group will handle extracting just the number

        # Get occupation group
        group_number = get_occupation_group(occupation)

        # Process impairments without apportionment
        no_apportionment_details = []
        no_apportionment_wpi_list = []
        
        # Process impairments with apportionment
        with_apportionment_details = []
        with_apportionment_wpi_list = []
        
        for imp in impairments:
            body_part = imp["body_part"]
            original_wpi = float(imp["wpi"])
            apportionment = float(imp.get("apportionment", 0))
            pain_addon = min(imp.get("pain_addon", 0.0), 3.0)

            # Map body part to impairment code
            impairment_code = map_body_part_to_code(body_part)
            
            # Get variant info - use extracted variant if available, otherwise get from database
            if occupation_variant:
                variant_label = occupation_variant
            else:
                variant_info = get_variant_for_impairment(group_number, impairment_code)
                variant_label = variant_info.get("variant_label", "variant1")

            # Add pain add-on to base WPI before 1.4 multiplier
            base_wpi = original_wpi + pain_addon
            adjusted_wpi = base_wpi * 1.4  # Apply 1.4 multiplier after adding pain
            
            # Get occupational adjustment using the adjusted WPI and variant
            occupant_adjusted_wpi = get_occupational_adjusted_wpi(group_number, variant_label, adjusted_wpi)
            
            # Get age adjustment using the occupationally adjusted WPI
            age_adjusted_wpi = get_age_adjusted_wpi(age, occupant_adjusted_wpi)
            
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
            
            # Add to appropriate lists
            no_apportionment_details.append(detail)
            no_apportionment_wpi_list.append(age_adjusted_wpi)
            
            if apportionment > 0:
                with_apportionment_details.append(detail)
                with_apportionment_wpi_list.append(apportioned_wpi)

        # Calculate final values for both scenarios
        no_apportionment_pd = combine_wpi_values(no_apportionment_wpi_list)
        with_apportionment_pd = combine_wpi_values(with_apportionment_wpi_list) if with_apportionment_wpi_list else None
        
        # Calculate payouts
        no_apportionment_result = calculate_pd_payout(no_apportionment_pd, no_apportionment_details, age)
        with_apportionment_result = calculate_pd_payout(with_apportionment_pd, with_apportionment_details, age) if with_apportionment_pd else None
        
        result = {
            "no_apportionment": no_apportionment_result,
            "with_apportionment": with_apportionment_result,
            "age": age,
            "occupation": occupation,
            "group_number": group_number
        }
        
        # Add detailed summary if available
        if "detailed_summary" in data:
            result["detailed_summary"] = data["detailed_summary"]
            
        return result

    except Exception as e:
        raise Exception(f"Error processing extracted data: {str(e)}")

# Store assistant and vector store as module-level variables to reuse them
_assistant = None
_vector_store = None

def extract_text_from_pdf(pdf_file):
    """Extract text from a PDF file.
    
    Args:
        pdf_file: A file-like object containing the PDF
        
    Returns:
        str: The extracted text from the PDF
    """
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
        logging.error(f"Error extracting text from PDF: {str(e)}")
        return ""

def process_medical_reports(uploaded_files, manual_data=None, mode="default", progress_callback=None) -> Union[str, Dict[str, Any]]:
    """Process multiple medical report PDFs and extract relevant information.
    
    Args:
        uploaded_files: List of uploaded PDF files
        manual_data: Optional manual data to override extracted values
        mode: Processing mode ('default', 'detailed', or 'raw')
        progress_callback: Optional callback function to report progress (0-100)
        
    Returns:
        Either a formatted string (detailed mode) or a dictionary with rating data
    """
    global _assistant, _vector_store
    client = None
    openai_files = []
    temp_files = []
    use_direct_text = True  # Flag to determine if we should use direct text extraction
    
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
            
        # Try direct text extraction first
        extracted_text = ""
        for i, uploaded_file in enumerate(uploaded_files):
            # Get file extension
            file_extension = uploaded_file.name.split('.')[-1].lower()
            
            # Save uploaded file temporarily for backup
            temp_filename = f"temp_file_{len(temp_files)}.{file_extension}"
            with open(temp_filename, "wb") as f:
                f.write(uploaded_file.getvalue())
            temp_files.append(temp_filename)
            
            # Extract text if it's a PDF
            if file_extension.lower() == 'pdf':
                # Reset file pointer to beginning
                uploaded_file.seek(0)
                file_text = extract_text_from_pdf(uploaded_file)
                extracted_text += f"\n\n--- Document: {uploaded_file.name} ---\n\n{file_text}"
            else:
                # For non-PDF files, we'll need to use the vector store approach
                use_direct_text = False
                break
                
            # Update progress for text extraction (10-30%)
            if progress_callback:
                file_progress = 10 + (i + 1) * 20 // len(uploaded_files)
                progress_callback(min(file_progress, 30))
        
        # Check if the extracted text is too large for the context window
        # The AI has a 200k context window, so we can use a much higher limit
        # We'll use a limit of 180k characters to be safe
        if len(extracted_text) > 180000:
            st.info(f"Extracted text is too large ({len(extracted_text)} characters). Using vector store approach instead.")
            use_direct_text = False
        
        if use_direct_text and extracted_text:
            st.info("Using direct text extraction approach")
            
            if progress_callback:
                progress_callback(50)
            
            # Create a thread with the extracted text as the message
            thread = client.beta.threads.create()
            message = client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=f"Please analyze this medical report according to the instructions provided:\n\n{extracted_text}"
            )
            
            # Create or reuse assistant without file search
            try:
                # Create a new assistant only if we don't have one already
                if _assistant is None:
                    _assistant = client.beta.assistants.create(
                        name="Medical Report Assistant",
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
                
                if progress_callback:
                    progress_callback(55)
            except Exception as e:
                raise ValueError(f"Failed to create/update assistant: {str(e)}")
            
            # Run assistant
            with st.spinner("Analyzing report..."):
                if progress_callback:
                    progress_callback(60)
                    
                run = client.beta.threads.runs.create_and_poll(
                    thread_id=thread.id,
                    assistant_id=_assistant.id
                )
        else:
            st.info("Using vector store approach")
            
            # Create OpenAI files
            for i, uploaded_file in enumerate(uploaded_files):
                # Reset file pointer to beginning
                uploaded_file.seek(0)
                
                # Create OpenAI file
                try:
                    openai_file = client.files.create(
                        file=open(temp_files[i], "rb"),
                        purpose="assistants"
                    )
                    openai_files.append(openai_file)
                    st.info(f"File uploaded to OpenAI: {uploaded_file.name}")
                except Exception as e:
                    raise ValueError(f"Failed to upload file to OpenAI: {str(e)}")
            
            # Create or reuse vector store for file search
            try:
                if progress_callback:
                    progress_callback(35)
                
                # Create a new vector store or clear the existing one
                if _vector_store is None:
                    _vector_store = client.beta.vector_stores.create(
                        name="Medical Report Store"
                    )
                    st.info("Created new vector store")
                else:
                    # Clear existing files from vector store
                    st.info("Clearing existing vector store")
                    # Note: OpenAI doesn't provide a direct way to clear a vector store
                    # We'll just reuse the existing one and add new files
                
                if progress_callback:
                    progress_callback(40)
                    
                # Add all files to vector store and wait for processing
                file_batch = client.beta.vector_stores.file_batches.create_and_poll(
                    vector_store_id=_vector_store.id,
                    file_ids=[f.id for f in openai_files]
                )
                
                if file_batch.status != "completed":
                    raise ValueError(f"File processing failed with status: {file_batch.status}")
                    
                st.success("Files processed successfully")
                
                if progress_callback:
                    progress_callback(50)
            except Exception as e:
                raise ValueError(f"Failed to process files in vector store: {str(e)}")
                
            # Create or reuse assistant with file search enabled
            try:
                # Create a new assistant only if we don't have one already
                if _assistant is None:
                    _assistant = client.beta.assistants.create(
                        name="Medical Report Assistant",
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
                
                if progress_callback:
                    progress_callback(55)
            except Exception as e:
                raise ValueError(f"Failed to create/update assistant: {str(e)}")
            
            # Create thread and message for AI analysis
            thread = client.beta.threads.create()
            message = client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content="Please analyze this medical report according to the instructions provided."
            )
            
            # Run assistant
            with st.spinner("Analyzing report..."):
                if progress_callback:
                    progress_callback(60)
                    
                run = client.beta.threads.runs.create_and_poll(
                    thread_id=thread.id,
                    assistant_id=_assistant.id
                )
            
            if progress_callback:
                progress_callback(80)
        
        if run.status == "completed":
            messages = client.beta.threads.messages.list(thread_id=thread.id)
            response_text = messages.data[0].content[0].text.value
            
            if progress_callback:
                progress_callback(85)
            
            # For detailed mode, return the text summary directly
            if mode == "detailed":
                try:
                    # Try to parse as JSON first in case it's wrapped
                    data = json.loads(response_text)
                    if isinstance(data, dict) and "detailed_summary" in data:
                        if progress_callback:
                            progress_callback(95)
                        return data["detailed_summary"]
                except json.JSONDecodeError:
                    # If not JSON, return the raw text
                    if progress_callback:
                        progress_callback(95)
                    return response_text.strip()
            
            # For rating calculation modes, parse JSON and process
            extracted_data = extract_json_from_response(response_text)
            
            if progress_callback:
                progress_callback(90)
            
            # Override with manual data if provided
            if manual_data:
                if manual_data.get("age"):
                    extracted_data["age"] = manual_data["age"]
                if manual_data.get("occupation"):
                    extracted_data["occupation"] = manual_data["occupation"]
            
            result = process_extracted_data(extracted_data)
            
            if progress_callback:
                progress_callback(95)
                
            if mode == "raw":
                return result
            return format_rating_output(result)
        else:
            raise ValueError(f"Assistant run failed with status: {run.status}")
            
    except Exception as e:
        raise Exception(f"Error processing medical report: {str(e)}")
    finally:
        # Only clean up the OpenAI files, keep the assistant and vector store
        if client:
            # Clean up OpenAI files
            for file in openai_files:
                try:
                    client.files.delete(file_id=file.id)
                except Exception:
                    pass
        
        # Clean up temp files
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception:
                pass
                
        # Final progress update
        if progress_callback:
            progress_callback(100)

def extract_json_from_response(response_text: str) -> Dict[str, Any]:
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
        logger.info(f"Successfully parsed JSON directly. Found {len(result.get('impairments', []))} impairments.")
        extraction_attempts.append(("direct_json", result))
    except json.JSONDecodeError as e:
        logger.debug(f"Direct JSON parsing failed: {str(e)}")
    
    # Method 2: Find JSON in markdown code blocks
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
    if json_match:
        try:
            result = json.loads(json_match.group(1))
            logger.info(f"Successfully parsed JSON from code block. Found {len(result.get('impairments', []))} impairments.")
            extraction_attempts.append(("code_block", result))
        except json.JSONDecodeError as e:
            logger.debug(f"Code block JSON parsing failed: {str(e)}")
    
    # Method 3: Find any JSON-like structure with a comprehensive regex
    json_match = re.search(r'\{(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\}))*\}))*\}', response_text, re.DOTALL)
    if json_match:
        try:
            result = json.loads(json_match.group(0))
            logger.info(f"Successfully parsed JSON from regex. Found {len(result.get('impairments', []))} impairments.")
            extraction_attempts.append(("regex", result))
        except json.JSONDecodeError as e:
            logger.debug(f"Regex JSON parsing failed: {str(e)}")
    
    # Method 4: Extract just the impairments array if it exists
    impairments_match = re.search(r'"impairments"\s*:\s*(\[.*?\])', response_text, re.DOTALL)
    if impairments_match:
        try:
            # Create a minimal valid JSON with just the impairments
            impairments_json = f'{{"impairments": {impairments_match.group(1)}, "age": 0, "occupation": "unknown"}}'
            result = json.loads(impairments_json)
            logger.info(f"Extracted just impairments array. Found {len(result.get('impairments', []))} impairments.")
            extraction_attempts.append(("impairments_only", result))
        except json.JSONDecodeError as e:
            logger.debug(f"Impairments extraction failed: {str(e)}")
    
    # If we have any successful extractions, use the first one (most reliable method)
    if extraction_attempts:
        method, result = extraction_attempts[0]
        logger.info(f"Using extraction method: {method}")
        
        # Validate the extracted data
        if not isinstance(result, dict):
            raise ValueError(f"Extracted data is not a dictionary: {type(result)}")
        
        required_fields = ["age", "occupation", "impairments"]
        for field in required_fields:
            if field not in result:
                logger.warning(f"Missing required field '{field}' in extracted data")
                if field == "impairments":
                    result[field] = []
                else:
                    result[field] = "unknown" if field == "occupation" else 0
        
        # Validate impairments
        if not isinstance(result["impairments"], list):
            logger.warning("Impairments is not a list, converting to empty list")
            result["impairments"] = []
        
        for i, imp in enumerate(result["impairments"]):
            if not isinstance(imp, dict):
                logger.warning(f"Impairment {i} is not a dictionary, removing")
                result["impairments"][i] = None
                continue
                
            if "body_part" not in imp:
                logger.warning(f"Impairment {i} missing body_part, adding default")
                imp["body_part"] = "Unknown"
                
            if "wpi" not in imp:
                logger.warning(f"Impairment {i} missing wpi, adding default")
                imp["wpi"] = 0
                
            # Ensure pain_addon exists
            if "pain_addon" not in imp:
                logger.warning(f"Impairment {i} missing pain_addon, adding default")
                imp["pain_addon"] = 0
                
            # Validate pain_addon is within range
            if imp.get("pain_addon", 0) > 3:
                logger.warning(f"Pain addon for impairment {i} exceeds maximum (3), capping at 3")
                imp["pain_addon"] = 3
        
        # Remove any None values from impairments
        result["impairments"] = [imp for imp in result["impairments"] if imp is not None]
        
        # Log the final impairments list
        logger.info(f"Final impairments list: {result['impairments']}")
        
        return result
    
    # If we got here, we couldn't find valid JSON
    error_message = "Could not extract valid JSON from the assistant's response."
    logger.error(error_message)
    raise ValueError(error_message)
