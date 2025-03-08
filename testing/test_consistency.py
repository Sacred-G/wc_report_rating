import os
import sys
import json
import unittest
import logging
import sqlite3
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add parent directory to path to import modules
sys.path.append(str(Path(__file__).parent.parent))

from utils.report_processor import extract_json_from_response
from utils.config import config

class TestConsistency(unittest.TestCase):
    """Test consistency of report processing results."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        print("Setting up test environment...")
        
        # Ensure data directory exists
        data_dir = Path(__file__).parent.parent / "data"
        os.makedirs(data_dir, exist_ok=True)
        
        # Set up test file path
        cls.test_file_path = Path(__file__).parent / "test_report.pdf"
        if not cls.test_file_path.exists():
            print(f"Test file not found: {cls.test_file_path}")
            print("Using existing test file")
    
    def test_json_extraction_consistency(self):
        """Test that JSON extraction is consistent."""
        # Sample responses with different formats
        responses = [
            '{"age": 45, "occupation": "Clerk", "impairments": [{"body_part": "Lumbar Spine", "wpi": 8}]}',
            'Here is the extracted data:\n```json\n{"age": 45, "occupation": "Clerk", "impairments": [{"body_part": "Lumbar Spine", "wpi": 8}]}\n```',
            'The patient is a 45-year-old Clerk with the following impairments:\n{"age": 45, "occupation": "Clerk", "impairments": [{"body_part": "Lumbar Spine", "wpi": 8}]}'
        ]
        
        results = []
        for response in responses:
            results.append(extract_json_from_response(response))
        
        # Verify all results are the same
        for i in range(1, len(results)):
            self.assertEqual(
                results[0]['age'], 
                results[i]['age'], 
                f"Age mismatch between extraction {0} and {i}"
            )
            self.assertEqual(
                results[0]['occupation'], 
                results[i]['occupation'], 
                f"Occupation mismatch between extraction {0} and {i}"
            )
            self.assertEqual(
                len(results[0]['impairments']), 
                len(results[i]['impairments']), 
                f"Impairment count mismatch between extraction {0} and {i}"
            )
            self.assertEqual(
                results[0]['impairments'][0]['body_part'], 
                results[i]['impairments'][0]['body_part'], 
                f"Body part mismatch between extraction {0} and {i}"
            )
            self.assertEqual(
                results[0]['impairments'][0]['wpi'], 
                results[i]['impairments'][0]['wpi'], 
                f"WPI mismatch between extraction {0} and {i}"
            )
    
    # Commenting out this test for now as it requires more setup
    # def test_calculation_consistency(self):
    #     """Test that calculations are consistent with the same input data."""
    #     print("Skipping calculation consistency test for now")
    #     pass

if __name__ == '__main__':
    unittest.main()
