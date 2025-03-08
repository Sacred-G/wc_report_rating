import streamlit as st
import pandas as pd
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import the database functions and rating calculator
from utils.database import (
    init_database,
    get_occupation_group,
    get_variant_for_impairment,
    get_occupational_adjusted_wpi,
    get_age_adjusted_wpi
)
from rating_calculator import calculate_rating

def test_database_usage():
    """Test script to verify database usage during rating calculation."""
    print("\n===== TESTING DATABASE USAGE IN RATING CALCULATION =====\n")
    
    # Initialize the database
    print("Initializing database...")
    init_database()
    print("Database initialized successfully.")
    
    # Test parameters
    occupation = "Carpenter"
    bodypart = "SPINE"
    age_injury = datetime.now().strftime("%Y-%m-%d")  # Today's date
    wpi = 10.0
    pain = 1.0
    
    print(f"\nCalculating rating with parameters:")
    print(f"  Occupation: {occupation}")
    print(f"  Body Part: {bodypart}")
    print(f"  Age/Injury Date: {age_injury}")
    print(f"  WPI: {wpi}")
    print(f"  Pain: {pain}")
    print("\nYou should see DATABASE: log messages below showing database access:\n")
    
    # Calculate rating
    result = calculate_rating(
        occupation=occupation,
        bodypart=bodypart,
        age_injury=age_injury,
        wpi=wpi,
        pain=pain
    )
    
    # Display results
    if result['status'] == 'success':
        print("\n===== RATING CALCULATION RESULTS =====\n")
        print(f"Final Rating: {result['final_value']}%")
        print("\nDetails:")
        for detail in result['details']:
            print(f"  Body Part: {detail['body_part']}")
            print(f"  Group Number: {detail['group_number']}")
            print(f"  Variant: {detail['variant']}")
            print(f"  Base Value: {detail['base_value']}")
            print(f"  Adjusted Value: {detail['adjusted_value']}")
            print(f"  Occupational Adjusted WPI: {detail['occupant_adjusted_wpi']}")
            print(f"  Age: {detail['age']}")
            print(f"  Final Value: {detail['final_value']}")
            print("")
    else:
        print(f"\nError: {result['message']}")
    
    print("\n===== TEST COMPLETE =====\n")
    print("If you saw DATABASE: log messages above, the database is being used correctly.")

if __name__ == "__main__":
    test_database_usage()
