from datetime import datetime
import logging
from typing import Dict, Any, List, Union, Optional
from utils.database import (
    get_occupation_group,
    get_variant_for_impairment,
    get_occupational_adjusted_wpi,
    get_age_adjusted_wpi
)
from utils.calculations import combine_wpi_values

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def calculate_rating(occupation: str, bodypart: Union[str, List, Dict], age_injury: str, 
                    wpi: Union[float, List[float], Dict], pain: Union[float, int] = 0) -> Dict[str, Any]:
    """
    Calculate workers compensation rating using local SQLite database.
    
    Args:
        occupation: Occupation title or group code (e.g., "380H")
        bodypart: Body part affected - can be string, list, or dictionary with body_part and wpi keys
        age_injury: Date of injury in YYYY-MM-DD format
        wpi: Whole person impairment value - can be float, list, or part of dictionary
        pain: Pain add-on value (default 0)
        
    Returns:
        Dictionary with calculation results including status, final value, and details
    """
    try:
        logger.info(f"Calculating rating for occupation: {occupation}, bodypart: {bodypart}, age_injury: {age_injury}, wpi: {wpi}, pain: {pain}")
        
        # Input validation
        if not occupation:
            raise ValueError("Occupation cannot be empty")
        
        if not bodypart:
            raise ValueError("Body part cannot be empty")
            
        if not age_injury:
            raise ValueError("Age/injury date cannot be empty")
            
        # Validate date format
        try:
            datetime.strptime(age_injury, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Invalid date format. Please use YYYY-MM-DD format for age_injury")
        
        # 1. Get group number from occupation
        group_number = get_occupation_group(occupation)
        logger.info(f"Group number found: {group_number}")
        
        # Handle multiple body parts if provided as a list or dictionary
        details = []
        final_values = []
        
        # Check if bodypart is a string (single body part) or a dictionary/list (multiple body parts)
        if isinstance(bodypart, str) and isinstance(wpi, (int, float)):
            # Single body part case
            body_parts = [{"body_part": bodypart, "wpi": wpi}]
        elif isinstance(bodypart, list) and isinstance(wpi, list):
            # Multiple body parts as lists
            if len(bodypart) != len(wpi):
                raise ValueError("Body part list and WPI list must have the same length")
            body_parts = [{"body_part": bp, "wpi": w} for bp, w in zip(bodypart, wpi)]
        elif isinstance(bodypart, dict) and "body_part" in bodypart and "wpi" in bodypart:
            # Single body part as dictionary
            body_parts = [bodypart]
        elif isinstance(bodypart, list) and all(isinstance(bp, dict) and "body_part" in bp and "wpi" in bp for bp in bodypart):
            # Multiple body parts as list of dictionaries
            body_parts = bodypart
        else:
            # Try to convert to appropriate format
            try:
                if isinstance(bodypart, (list, dict)) and not isinstance(wpi, (list, dict)):
                    # If bodypart is complex but wpi is simple, try to extract body part info
                    if isinstance(bodypart, list):
                        body_parts = [{"body_part": str(bp), "wpi": float(wpi)} for bp in bodypart]
                    else:
                        body_parts = [{"body_part": str(bodypart), "wpi": float(wpi)}]
                else:
                    # Default case - treat as single body part
                    body_parts = [{"body_part": str(bodypart), "wpi": float(wpi)}]
            except (ValueError, TypeError) as e:
                raise ValueError(f"Invalid bodypart or wpi format: {str(e)}")
        
        # Process each body part
        for bp in body_parts:
            part_name = bp["body_part"]
            try:
                part_wpi = float(bp["wpi"])
                if part_wpi < 0:
                    logger.warning(f"Negative WPI value for {part_name}: {part_wpi}. Using absolute value.")
                    part_wpi = abs(part_wpi)
            except (ValueError, TypeError):
                raise ValueError(f"Invalid WPI value for {part_name}: {bp['wpi']}. Must be a number.")
                
            try:
                part_pain = float(bp.get("pain", pain))
                if part_pain < 0 or part_pain > 3:
                    logger.warning(f"Pain value out of range for {part_name}: {part_pain}. Clamping to 0-3 range.")
                    part_pain = max(0, min(part_pain, 3))
            except (ValueError, TypeError):
                raise ValueError(f"Invalid pain value for {part_name}: {bp.get('pain', pain)}. Must be a number.")
            
            # 2. Get variant info using group number and bodypart
            try:
                variant_info = get_variant_for_impairment(group_number, part_name)
                variant = variant_info.get('variant_label', 'G')
                logger.info(f"Variant found for {part_name}: {variant}")
            except Exception as e:
                logger.warning(f"Error getting variant for {part_name}: {str(e)}. Using default variant 'G'.")
                variant = 'G'
            
            # Calculate adjusted value
            base_value = part_wpi + part_pain
            adjusted_value = round(base_value * 1.4, 1)
            logger.info(f"Adjusted value calculated for {part_name}: {adjusted_value}")
            
            # 3. Get occupational adjusted WPI
            try:
                occupant_adjusted_wpi = get_occupational_adjusted_wpi(group_number, variant, adjusted_value)
                logger.info(f"Occupational adjusted WPI for {part_name}: {occupant_adjusted_wpi}")
            except Exception as e:
                logger.error(f"Error getting occupational adjustment: {str(e)}. Using adjusted value instead.")
                occupant_adjusted_wpi = adjusted_value
            
            # 4. Get age from injury date
            injury_date = datetime.strptime(age_injury, "%Y-%m-%d")
            age = datetime.now().year - injury_date.year
            
            # 5. Get age adjusted WPI
            try:
                part_final_value = get_age_adjusted_wpi(age, occupant_adjusted_wpi)
                logger.info(f"Final value after age adjustment for {part_name}: {part_final_value}")
            except Exception as e:
                logger.error(f"Error getting age adjustment: {str(e)}. Using occupational adjusted value instead.")
                part_final_value = occupant_adjusted_wpi
            
            # Add to details and collect final values for combining
            details.append({
                'body_part': part_name,
                'group_number': group_number,
                'variant': variant,
                'base_value': base_value,
                'adjusted_value': adjusted_value,
                'occupant_adjusted_wpi': occupant_adjusted_wpi,
                'age': age,
                'final_value': part_final_value
            })
            
            # Add to list of final values for combining
            final_values.append(part_final_value)
        
        # Combine all body part ratings using the CVC formula
        if not final_values:
            raise ValueError("No valid impairment values found")
            
        combined_final_value = combine_wpi_values(final_values) if len(final_values) > 1 else final_values[0]
        logger.info(f"Combined final value for all body parts: {combined_final_value}")
        
        return {
            'status': 'success',
            'final_value': combined_final_value,
            'details': details
        }
    
    except Exception as e:
        logger.error(f"Error calculating rating: {str(e)}", exc_info=True)
        return {
            'status': 'error',
            'message': str(e)
        }
