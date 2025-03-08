import os
import json
import re
import logging
from typing import Dict, Any, List, Union, Optional
import streamlit as st
from openai import OpenAI
import PyPDF2
import pandas as pd
from utils.auth import init_openai_client, get_assistant_instructions
from utils.config import config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Store assistant as module-level variable to reuse it
_assistant = None

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
        logger.error(f"Error extracting text from PDF: {str(e)}")
        return ""

def get_impairment_extraction_instructions():
    """Get specialized instructions for impairment extraction"""
    return """
You are a specialized medical report analyzer focused on extracting impairment information from workers' compensation medical reports.

CRITICAL INSTRUCTION: Extract ALL impairments mentioned in the report and return ONLY a valid JSON object with NO additional text.

The JSON object MUST have exactly this structure:
{
    "impairments": [
        {
            "body_part": <string>,
            "wpi": <number>,
            "pain_addon": <number>,
            "apportionment": <number>,
            "context": <string>
        }
    ]
}

EXTRACTION GUIDELINES:

1. Search the ENTIRE document for ANY mention of impairment ratings, including:
   - Whole Person Impairment (WPI) percentages
   - Permanent Disability ratings
   - Body part-specific impairments
   - Any numerical ratings associated with body parts
   - Specific impairment types like "Trigeminal", "Mastication", and "Pain"

2. For each impairment found:
   - Identify the specific body part (be as precise as possible)
   - Extract the WPI percentage
   - Determine if there's a pain add-on (0-3 scale)
   - Identify any apportionment percentage
   - Include a brief context snippet showing where this impairment was mentioned

3. Pay special attention to:
   - Final summary/conclusion sections
   - Tables or lists of impairments
   - Sections titled "Permanent and Stationary" or "P&S"
   - Sections discussing "disability" or "impairment"
   - ANY mention of percentages related to body parts
   - Specific impairment types like "Trigeminal: 7% WPI", "Mastication: 3% WPI", "Pain: 0% WPI"

4. Be thorough - don't miss impairments that might be mentioned only once or in unusual sections of the report.

5. If the same body part has multiple impairment ratings, include each as a separate entry.

6. For specific impairment types, use the exact name as the body part:
   - "Trigeminal" should be extracted as "Trigeminal"
   - "Mastication" should be extracted as "Mastication"
   - "Pain" should be extracted as "Pain"

7. IMPORTANT: Do NOT extract "Per" as a body part. This is an error. If you see something like "Per: 5% WPI", ignore it or try to determine the actual body part from context.

EXAMPLE OF CORRECT RESPONSE:
{"impairments":[
  {"body_part":"Lumbar Spine","wpi":8,"pain_addon":2,"apportionment":0,"context":"Lumbar spine impairment is 8% WPI with a pain add-on of 2 per Chapter 18."},
  {"body_part":"Left Shoulder","wpi":5,"pain_addon":1,"apportionment":20,"context":"Left shoulder impairment is rated at 5% WPI with 20% apportionment to pre-existing condition."},
  {"body_part":"Trigeminal","wpi":7,"pain_addon":0,"apportionment":0,"context":"Trigeminal: 7% WPI"},
  {"body_part":"Mastication","wpi":3,"pain_addon":0,"apportionment":0,"context":"Mastication: 3% WPI"}
]}

DO NOT include any explanations or text outside the JSON object. The response must be valid JSON that can be parsed directly.
"""

# Load impairment codes from CSV file
def load_impairment_codes():
    """Load impairment codes from CSV file."""
    try:
        # Load the CSV file
        df = pd.read_csv('data/bodypart_impairment_rows.csv')
        
        # Create a dictionary mapping body parts to codes and descriptions
        impairment_dict = {}
        for _, row in df.iterrows():
            code = row['Code']
            description = row['Description']
            # Use the description as the key (lowercase for case-insensitive matching)
            impairment_dict[description.lower()] = {
                'code': code,
                'description': description
            }
            
            # Also add individual words from the description as keys for better matching
            words = description.lower().split()
            for word in words:
                if len(word) > 3:  # Only use words longer than 3 characters to avoid common words
                    if word not in impairment_dict:
                        impairment_dict[word] = {
                            'code': code,
                            'description': description
                        }
        
        return impairment_dict
    except Exception as e:
        logger.error(f"Error loading impairment codes: {str(e)}")
        return {}

# Initialize the impairment codes dictionary
_impairment_codes = None

def get_impairment_codes():
    """Get or initialize the impairment codes dictionary."""
    global _impairment_codes
    if _impairment_codes is None:
        _impairment_codes = load_impairment_codes()
    return _impairment_codes

def map_body_part_to_code(body_part: str) -> tuple:
    """Maps body part descriptions to standardized impairment codes and descriptions.
    
    Args:
        body_part: The body part description to map
        
    Returns:
        tuple: (code, formatted_string) where formatted_string is in the format "code - description"
    """
    body_part_lower = body_part.lower().strip()
    impairment_codes = get_impairment_codes()
    
    # First, try direct match with the body part
    if body_part_lower in impairment_codes:
        code = impairment_codes[body_part_lower]['code']
        description = impairment_codes[body_part_lower]['description']
        return code, f"{code} - {description}"
    
    # If no direct match, try to find the best match based on words in the body part
    best_match = None
    best_match_count = 0
    
    for word in body_part_lower.split():
        if len(word) > 3 and word in impairment_codes:
            # Count how many words from the body part are in the description
            description_lower = impairment_codes[word]['description'].lower()
            match_count = sum(1 for w in body_part_lower.split() if w in description_lower)
            
            if match_count > best_match_count:
                best_match = impairment_codes[word]
                best_match_count = match_count
    
    if best_match:
        return best_match['code'], f"{best_match['code']} - {best_match['description']}"
    
    # If still no match, use the fallback mapping logic
    
    # Spine and Nervous System
    if any(term in body_part_lower for term in ["spine", "back", "lumbar", "thoracic", "cervical", "neck"]):
        if "lumbar" in body_part_lower and ("range" in body_part_lower or "motion" in body_part_lower or "rom" in body_part_lower):
            return "15.03.02.05", "15.03.02.05 - Lumbar Range of Motion Nerve Root/Spinal Cord Sensory"
        elif "cervical" in body_part_lower and ("range" in body_part_lower or "motion" in body_part_lower or "rom" in body_part_lower):
            return "15.01.02.05", "15.01.02.05 - Cervical Range of Motion Nerve Root/Spinal Cord Sensory"
        return "15.03.02.05", "15.03.02.05 - Lumbar Range of Motion Nerve Root/Spinal Cord Sensory"
    
    # Upper Extremities
    if "shoulder" in body_part_lower:
        if "range" in body_part_lower or "motion" in body_part_lower or "rom" in body_part_lower:
            return "16.02.01.00", "16.02.01.00 - Shoulder Range of Motion"
        return "16.02.01.00", "16.02.01.00 - Shoulder Range of Motion"
    
    if "elbow" in body_part_lower:
        if "range" in body_part_lower or "motion" in body_part_lower or "rom" in body_part_lower:
            return "16.03.01.00", "16.03.01.00 - Elbow/Forearm Range of Motion"
        return "16.03.01.00", "16.03.01.00 - Elbow/Forearm Range of Motion"
        
    if "wrist" in body_part_lower:
        if "range" in body_part_lower or "motion" in body_part_lower or "rom" in body_part_lower:
            return "16.04.01.00", "16.04.01.00 - Wrist Range of Motion"
        return "16.04.01.00", "16.04.01.00 - Wrist Range of Motion"
        
    if any(term in body_part_lower for term in ["hand", "finger", "thumb"]):
        return "16.05.00.00", "16.05.00.00 - Hand/Multiple Fingers"
        
    if "grip" in body_part_lower or "pinch" in body_part_lower:
        return "16.01.04.00", "16.01.04.00 - Arm Grip/Pinch Strength"
        
    # Lower Extremities
    if "knee" in body_part_lower:
        if "muscle" in body_part_lower or "strength" in body_part_lower:
            return "17.05.05.00", "17.05.05.00 - Knee Muscle Strength"
        return "17.05.00.00", "17.05.00.00 - Knee"
        
    if "ankle" in body_part_lower:
        return "17.07.00.00", "17.07.00.00 - Ankle"
        
    if "hip" in body_part_lower:
        return "17.03.00.00", "17.03.00.00 - Hip"
        
    if "leg" in body_part_lower and "amput" in body_part_lower:
        return "17.01.02.00", "17.01.02.00 - Leg Amputation"
    
    # Special impairment types
    if "trigeminal" in body_part_lower:
        return "13.07.04.00", "13.07.04.00 - Cranial Nerve Trigeminal"
        
    if "mastication" in body_part_lower or "jaw" in body_part_lower:
        return "11.03.02.00", "11.03.02.00 - Nose/Throat/Related Structures Mastication & Deglutition"
        
    if body_part_lower == "pain":
        return "18.00.00.00", "18.00.00.00 - Pain"
    
    # Generic mappings for unspecified conditions
    if any(term in body_part_lower for term in ["arm", "upper extremity", "bicep", "tricep"]):
        return "16.00.00.00", "16.00.00.00 - Upper Extremities"
    if any(term in body_part_lower for term in ["leg", "lower extremity", "shin", "calf"]):
        return "17.00.00.00", "17.00.00.00 - Lower Extremities"
    
    # Default to OTHER if no specific match found
    return "00.00.00.00", "00.00.00.00 - Other"

def extract_impairments_with_ai(pdf_file, progress_callback=None) -> List[Dict[str, Any]]:
    """Extract impairments from a PDF file using AI.
    
    Args:
        pdf_file: A file-like object containing the PDF
        progress_callback: Optional callback function to report progress (0-100)
        
    Returns:
        List of dictionaries containing impairment information
    """
    global _assistant
    client = None
    temp_files = []
    
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
            progress_callback(30)
        
        # Create or reuse assistant
        try:
            if _assistant is None:
                _assistant = client.beta.assistants.create(
                    name="Impairment Extractor",
                    instructions=get_impairment_extraction_instructions(),
                    model=config.openai_model
                )
                logger.info("Created new impairment extractor assistant")
            else:
                # Update the existing assistant with the current instructions
                _assistant = client.beta.assistants.update(
                    assistant_id=_assistant.id,
                    instructions=get_impairment_extraction_instructions()
                )
                logger.info("Updated existing impairment extractor assistant")
            
            if progress_callback:
                progress_callback(40)
        except Exception as e:
            raise ValueError(f"Failed to create/update assistant: {str(e)}")
        
        # Create a thread with the extracted text as the message
        thread = client.beta.threads.create()
        message = client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=f"Please extract all impairments from this medical report:\n\n{extracted_text}"
        )
        
        if progress_callback:
            progress_callback(50)
        
        # Run assistant
        run = client.beta.threads.runs.create_and_poll(
            thread_id=thread.id,
            assistant_id=_assistant.id
        )
        
        if progress_callback:
            progress_callback(80)
        
        if run.status == "completed":
            messages = client.beta.threads.messages.list(thread_id=thread.id)
            response_text = messages.data[0].content[0].text.value
            
            # Extract JSON from response
            extracted_data = extract_json_from_response(response_text)
            
            if progress_callback:
                progress_callback(90)
            
            # Get the impairments list
            impairments = extracted_data.get("impairments", [])
            
            # Filter out any impairments with "Per" as the body part (this is an error)
            impairments = [imp for imp in impairments if not imp["body_part"].lower().startswith("per")]
            
            # Add impairment_code and formatted_string to each impairment
            for imp in impairments:
                code, formatted_string = map_body_part_to_code(imp["body_part"])
                imp["impairment_code"] = code
                imp["formatted_string"] = formatted_string
            
            logger.info(f"Extracted {len(impairments)} impairments using AI")
            
            if progress_callback:
                progress_callback(100)
                
            return impairments
        else:
            raise ValueError(f"Assistant run failed with status: {run.status}")
            
    except Exception as e:
        logger.error(f"Error extracting impairments with AI: {str(e)}", exc_info=True)
        raise Exception(f"Error extracting impairments with AI: {str(e)}")
    finally:
        # Clean up temp files
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception:
                pass

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

def standardize_impairments(impairments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Standardize impairments by mapping to consistent body part names and codes.
    
    Args:
        impairments: List of impairments to standardize
        
    Returns:
        List of standardized impairments
    """
    # Load the impairment codes
    impairment_codes = get_impairment_codes()
    
    # Define body part synonyms to handle different names for the same body part
    body_part_synonyms = {
        "back": ["back", "lumbar", "lumbar spine", "spine", "lower back"],
        "neck": ["neck", "cervical", "cervical spine"],
        "shoulder": ["shoulder", "rotator cuff"],
        "knee": ["knee", "patella"],
        "hand": ["hand", "finger", "fingers", "thumb"],
        "foot": ["foot", "toe", "toes", "ankle"],
        "arm": ["arm", "elbow", "forearm", "upper arm"],
        "leg": ["leg", "thigh", "calf", "shin"],
        "hip": ["hip", "pelvis"],
        "head": ["head", "skull", "cranium"],
        "face": ["face", "jaw", "mandible", "maxilla"],
        "chest": ["chest", "rib", "ribs", "thoracic", "thorax"],
        "abdomen": ["abdomen", "stomach", "abdominal"]
    }
    
    # Map from normalized body part names to standard impairment codes
    standard_body_part_codes = {
        "back": "15.03.02.05",  # Lumbar Range of Motion Nerve Root/Spinal Cord Sensory
        "neck": "15.01.02.05",  # Cervical Range of Motion Nerve Root/Spinal Cord Sensory
        "shoulder": "16.02.01.00",  # Shoulder Range of Motion
        "knee": "17.05.00.00",  # Knee
        "hand": "16.05.00.00",  # Hand/Multiple Fingers
        "foot": "17.08.00.00",  # Foot
        "arm": "16.00.00.00",  # Upper Extremities
        "leg": "17.00.00.00",  # Lower Extremities
        "hip": "17.03.00.00",  # Hip
        "head": "13.00.00.00",  # Central & Peripheral Nervous System
        "face": "11.02.01.00",  # Face/cosmetic
        "chest": "05.00.00.00",  # Respiratory System
        "abdomen": "06.00.00.00",  # Digestive System
        "rib": "05.00.00.00",  # Respiratory System
    }
    
    # Create a function to normalize body part names
    def normalize_body_part(body_part: str) -> str:
        body_part_lower = body_part.lower()
        for main_name, synonyms in body_part_synonyms.items():
            if any(synonym in body_part_lower for synonym in synonyms):
                return main_name
        return body_part_lower
    
    # Standardize each impairment
    standardized_impairments = []
    for imp in impairments:
        # Make a copy of the impairment to avoid modifying the original
        standardized_imp = imp.copy()
        
        # Normalize the body part name
        normalized_body_part = normalize_body_part(standardized_imp["body_part"])
        
        # Get the standard code for this body part
        if normalized_body_part in standard_body_part_codes:
            code = standard_body_part_codes[normalized_body_part]
            
            # Find the description for this code
            description = standardized_imp["body_part"]  # Default to original body part name
            if impairment_codes:  # Only try to find description if impairment_codes is not empty
                for desc, info in impairment_codes.items():
                    if info.get('code') == code:
                        description = info.get('description', desc)
                        break
            
            # Update the impairment with standardized information
            standardized_imp["impairment_code"] = code
            standardized_imp["formatted_string"] = f"{code} - {description}"
        
        standardized_impairments.append(standardized_imp)
    
    return standardized_impairments

def merge_impairments(ai_impairments: List[Dict[str, Any]], regex_impairments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Merge impairments from AI and regex extraction, removing duplicates.
    
    Args:
        ai_impairments: List of impairments extracted by AI
        regex_impairments: List of impairments extracted by regex
        
    Returns:
        Merged list of impairments
    """
    # Define body part synonyms to handle different names for the same body part
    body_part_synonyms = {
        "back": ["back", "lumbar", "lumbar spine", "spine", "lower back"],
        "neck": ["neck", "cervical", "cervical spine"],
        "shoulder": ["shoulder", "rotator cuff"],
        "knee": ["knee", "patella"],
        "hand": ["hand", "finger", "fingers", "thumb"],
        "foot": ["foot", "toe", "toes", "ankle"],
        "arm": ["arm", "elbow", "forearm", "upper arm"],
        "leg": ["leg", "thigh", "calf", "shin"],
        "hip": ["hip", "pelvis"],
        "head": ["head", "skull", "cranium"],
        "face": ["face", "jaw", "mandible", "maxilla"],
        "chest": ["chest", "rib", "ribs", "thoracic", "thorax"],
        "abdomen": ["abdomen", "stomach", "abdominal"]
    }
    
    # Create a function to normalize body part names
    def normalize_body_part(body_part: str) -> str:
        body_part_lower = body_part.lower()
        for main_name, synonyms in body_part_synonyms.items():
            if any(synonym in body_part_lower for synonym in synonyms):
                return main_name
        return body_part_lower
    
    # Create a dictionary to track unique normalized body part + WPI combinations
    unique_impairments = {}
    
    # Process AI impairments first (they take precedence)
    for imp in ai_impairments:
        normalized_body_part = normalize_body_part(imp["body_part"])
        key = (normalized_body_part, imp["wpi"])
        unique_impairments[key] = imp
    
    # Add regex impairments if they don't already exist
    for imp in regex_impairments:
        normalized_body_part = normalize_body_part(imp["body_part"])
        key = (normalized_body_part, imp["wpi"])
        if key not in unique_impairments:
            unique_impairments[key] = imp
    
    # Convert back to list and standardize
    merged_impairments = list(unique_impairments.values())
    return standardize_impairments(merged_impairments)

def extract_impairments_with_regex(text: str) -> List[Dict[str, Any]]:
    """Extract impairments from text using regex patterns.
    
    Args:
        text: The text to extract impairments from
        
    Returns:
        List of dictionaries containing impairment information
    """
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
        'rotator cuff', 'meniscus', 'acl', 'mcl', 'lcl', 'pcl', 'labrum',
        # Add specific impairment types (excluding 'per' which is an error)
        'trigeminal', 'mastication', 'pain'
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
            body_part = found_body_part.capitalize()
            
            # Skip if body part is "Per" (this is an error)
            if body_part.lower().startswith("per"):
                continue
            
            # Get impairment code and formatted string
            code, formatted_string = map_body_part_to_code(body_part)
                
            impairment = {
                'body_part': body_part,
                'wpi': wpi_value,
                'apportionment': 0,  # Default to 0
                'pain_addon': 0,  # Default to 0
                'impairment_code': code,  # Add impairment code
                'formatted_string': formatted_string  # Add formatted string
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
        logger.info(f"Extracted {len(impairments)} impairments with regex")
    else:
        logger.info("No impairments extracted with regex")
    
    return impairments

def extract_all_impairments(pdf_file, use_ai=True, progress_callback=None) -> List[Dict[str, Any]]:
    """Extract impairments using both regex and AI methods, and merge the results.
    
    Args:
        pdf_file: A file-like object containing the PDF
        use_ai: Whether to use AI extraction (slower but more accurate)
        progress_callback: Optional callback function to report progress (0-100)
        
    Returns:
        List of dictionaries containing impairment information
    """
    # Extract text from PDF
    pdf_file.seek(0)  # Reset file pointer
    extracted_text = extract_text_from_pdf(pdf_file)
    
    if not extracted_text:
        return []
    
    # Use regex extraction first (faster)
    regex_impairments = extract_impairments_with_regex(extracted_text)
    
    if not use_ai:
        return regex_impairments
    
    try:
        # Use AI extraction (slower but more accurate)
        pdf_file.seek(0)  # Reset file pointer
        ai_impairments = extract_impairments_with_ai(pdf_file, progress_callback)
        
        # Merge the results
        merged_impairments = merge_impairments(ai_impairments, regex_impairments)
        
        return merged_impairments
    except Exception as e:
        logger.error(f"AI extraction failed, falling back to regex: {str(e)}", exc_info=True)
        return regex_impairments
