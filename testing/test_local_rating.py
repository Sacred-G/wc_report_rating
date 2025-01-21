import unittest
import sys
import os
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rating_calculator import calculate_rating

class TestLocalRating(unittest.TestCase):
    def setUp(self):
        """Set up test cases"""
        self.test_cases = [
            {
                'occupation': 'Software Engineer',
                'bodypart': 'Lower Back',
                'age_injury': '2023-01-15',
                'wpi': 25,
                'pain': 3
            },
            {
                'occupation': 'Accountant',
                'bodypart': 'Shoulder',
                'age_injury': '2023-06-01',
                'wpi': 15,
                'pain': 2
            }
        ]

    def test_rating_calculation(self):
        """Test rating calculation with local database"""
        for case in self.test_cases:
            try:
                result = calculate_rating(
                    occupation=case['occupation'],
                    bodypart=case['bodypart'],
                    age_injury=case['age_injury'],
                    wpi=case['wpi'],
                    pain=case['pain']
                )
                
                # Check result structure
                self.assertEqual(result['status'], 'success')
                self.assertIsNotNone(result['final_value'])
                self.assertIsInstance(result['final_value'], float)
                
                # Check details
                details = result['details']
                self.assertIsNotNone(details['group_number'])
                self.assertIsNotNone(details['variant'])
                self.assertIsNotNone(details['base_value'])
                self.assertIsNotNone(details['adjusted_value'])
                self.assertIsNotNone(details['occupant_adjusted_wpi'])
                self.assertIsNotNone(details['age'])
                self.assertIsNotNone(details['final_value'])
                
                # Check calculations
                self.assertEqual(details['base_value'], case['wpi'] + case['pain'])
                self.assertEqual(details['adjusted_value'], 
                               round(details['base_value'] * 1.4, 1))
                
                print(f"\nTest case: {case}")
                print(f"Result: {result}")
                
            except Exception as e:
                self.fail(f"Failed for case {case}: {str(e)}")

    def test_invalid_occupation(self):
        """Test with invalid occupation"""
        result = calculate_rating(
            occupation="NonexistentJob",
            bodypart="Lower Back",
            age_injury="2023-01-15",
            wpi=25
        )
        self.assertEqual(result['status'], 'error')
        self.assertIn('occupation', result['message'].lower())

    def test_invalid_date(self):
        """Test with invalid date format"""
        result = calculate_rating(
            occupation="Software Engineer",
            bodypart="Lower Back",
            age_injury="invalid-date",
            wpi=25
        )
        self.assertEqual(result['status'], 'error')
        self.assertIn('time', result['message'].lower())

if __name__ == '__main__':
    unittest.main()
