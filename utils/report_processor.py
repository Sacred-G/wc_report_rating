import os
import json
import re
from typing import Dict, Any, List, Union
import streamlit as st
from openai import OpenAI
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
            
            # Get variant info
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

def process_medical_reports(uploaded_files, manual_data=None, mode="default") -> Union[str, Dict[str, Any]]:
    """Process multiple medical report PDFs and extract relevant information."""
    try:
        # Initialize OpenAI client
        client = init_openai_client()
        
        # Create OpenAI files and save temp files
        openai_files = []
        temp_files = []
        
        for uploaded_file in uploaded_files:
            # Get file extension and create temp file
            file_extension = uploaded_file.name.split('.')[-1].lower()
            temp_filename = f"temp_file_{len(temp_files)}.{file_extension}"
            
            # Save uploaded file temporarily
            with open(temp_filename, "wb") as f:
                f.write(uploaded_file.getvalue())
            temp_files.append(temp_filename)
            
            # Create OpenAI file
            openai_file = client.files.create(
                file=open(temp_filename, "rb"),
                purpose="assistants"
            )
            openai_files.append(openai_file)
            st.info(f"File uploaded successfully: {uploaded_file.name}")
        
        # Create vector store for file search
        vector_store = client.beta.vector_stores.create(
            name="Medical Report Store"
        )
        
        # Add all files to vector store and wait for processing
        file_batch = client.beta.vector_stores.file_batches.create_and_poll(
            vector_store_id=vector_store.id,
            file_ids=[f.id for f in openai_files]
        )
        
        if file_batch.status != "completed":
            st.error(f"File processing failed with status: {file_batch.status}")
            st.stop()
            
        st.success("File processed successfully")
            
        # Create assistant with file search enabled
        assistant = client.beta.assistants.create(
            name="Medical Report Assistant",
            instructions=get_assistant_instructions(mode) + """
            IMPORTANT: You are analyzing multiple medical reports. When extracting information:
            1. Look through all reports to find the most recent information
            2. If there are multiple WPI ratings for the same body part, use the most recent one
            3. Combine all unique body parts and their ratings
            4. For occupation and age, use the most recent values
            5. When finding pain add-ons, check all reports and use the most recent value for each body part
            6. For apportionment, use the values from the most recent report for each body part
            """,
            tools=[{"type": "file_search"}],
            model=config.openai_model,
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
            
            # For detailed mode, return the text summary directly
            if mode == "detailed":
                try:
                    # Try to parse as JSON first in case it's wrapped
                    data = json.loads(response_text)
                    if isinstance(data, dict) and "detailed_summary" in data:
                        return data["detailed_summary"]
                except json.JSONDecodeError:
                    # If not JSON, return the raw text
                    return response_text.strip()
            
            # For rating calculation modes, parse JSON and process
            try:
                # First try direct JSON parsing
                extracted_data = json.loads(response_text)
                
                # Override with manual data if provided
                if manual_data:
                    if manual_data.get("age"):
                        extracted_data["age"] = manual_data["age"]
                    if manual_data.get("occupation"):
                        extracted_data["occupation"] = manual_data["occupation"]
                
                result = process_extracted_data(extracted_data)
                if mode == "raw":
                    return result
                return format_rating_output(result)
            except json.JSONDecodeError:
                # Try to find JSON in markdown code blocks
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
                if json_match:
                    try:
                        extracted_data = json.loads(json_match.group(1))
                        result = process_extracted_data(extracted_data)
                        if mode == "raw":
                            return result
                        return format_rating_output(result)
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
                        result = process_extracted_data(extracted_data)
                        if mode == "raw":
                            return result
                        return format_rating_output(result)
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
        # Cleanup all temp files
        for temp_file in temp_files:
            try:
                os.remove(temp_file)
            except:
                pass
