import os
import sys
from utils.database import get_occupation_group, get_variant_for_impairment, init_database
from utils.report_processor import process_extracted_data
from utils.config import config

# Initialize database
print("Initializing database...")
try:
    init_database()
    print("Database initialized successfully.")
except Exception as e:
    print(f"Error initializing database: {str(e)}")

# Test the get_occupation_group function
def test_get_occupation_group():
    print("\nTesting get_occupation_group function:")
    
    test_cases = [
        "380H",
        "Clerk",
        "Teacher",
        "Stocker"
    ]
    
    for occupation in test_cases:
        try:
            group_number = get_occupation_group(occupation)
            print(f"Occupation: {occupation} -> Group Number: {group_number}")
        except Exception as e:
            print(f"Error with occupation '{occupation}': {str(e)}")

# Test the process_extracted_data function
def test_process_extracted_data():
    print("\nTesting process_extracted_data function:")
    
    test_data = {
        "age": 45,
        "occupation": "380H",
        "impairments": [
            {
                "body_part": "lumbar spine",
                "wpi": 10,
                "apportionment": 0,
                "pain_addon": 2
            }
        ]
    }
    
    try:
        result = process_extracted_data(test_data)
        print(f"Result: {result}")
        
        # Check the variant used
        impairment_details = result['no_apportionment']['formatted_impairments'][0]
        print(f"Formatted string: {impairment_details['formatted_string']}")
        
    except Exception as e:
        print(f"Error processing data: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_get_occupation_group()
    test_process_extracted_data()
