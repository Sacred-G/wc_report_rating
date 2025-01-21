from datetime import datetime
from utils.database import (
    get_occupation_group,
    get_variant_for_impairment,
    get_occupational_adjusted_wpi,
    get_age_adjusted_wpi
)

def calculate_rating(occupation, bodypart, age_injury, wpi, pain=0):
    """
    Calculate workers compensation rating using local SQLite database.
    
    Args:
        occupation: Occupation title
        bodypart: Body part affected
        age_injury: Date of injury
        wpi: Whole person impairment value
        pain: Pain add-on value (default 0)
    """
    try:
        print(f"Calculating rating for occupation: {occupation}, bodypart: {bodypart}, age_injury: {age_injury}, wpi: {wpi}, pain: {pain}")
        
        # 1. Get group number from occupation
        group_number = get_occupation_group(occupation)
        print(f"Group number found: {group_number}")
        
        # 2. Get variant info using group number and bodypart
        variant_info = get_variant_for_impairment(group_number, bodypart)
        variant = variant_info.get('variant_label', 'G')
        print(f"Variant found: {variant}")
        
        # Calculate adjusted value
        base_value = wpi + pain
        adjusted_value = round(base_value * 1.4, 1)
        print(f"Adjusted value calculated: {adjusted_value}")
        
        # 3. Get occupational adjusted WPI
        occupant_adjusted_wpi = get_occupational_adjusted_wpi(group_number, variant, adjusted_value)
        print(f"Occupational adjusted WPI: {occupant_adjusted_wpi}")
        
        # 4. Get age from injury date
        injury_date = datetime.strptime(age_injury, "%Y-%m-%d")
        age = datetime.now().year - injury_date.year
        
        # 5. Get age adjusted WPI
        final_value = get_age_adjusted_wpi(age, occupant_adjusted_wpi)
        print(f"Final value after age adjustment: {final_value}")

        return {
            'status': 'success',
            'final_value': final_value,
            'details': {
                'group_number': group_number,
                'variant': variant,
                'base_value': base_value,
                'adjusted_value': adjusted_value,
                'occupant_adjusted_wpi': occupant_adjusted_wpi,
                'age': age,
                'final_value': final_value
            }
        }

    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }
