import unittest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.database import get_age_adjusted_wpi

class TestAgeAdjustment(unittest.TestCase):
    def test_age_adjustment(self):
        """Test age adjustment calculation for different age brackets"""
        test_cases = [
            (20, 10.0),  # Age 20 (21_and_under) with 10% WPI
            (25, 15.0),  # Age 25 (22_to_26) with 15% WPI
            (30, 20.0),  # Age 30 (27_to_31) with 20% WPI
            (35, 25.0),  # Age 35 (32_to_36) with 25% WPI
            (40, 30.0),  # Age 40 (37_to_41) with 30% WPI
        ]
        
        for age, wpi in test_cases:
            try:
                adjusted_wpi = get_age_adjusted_wpi(age, wpi)
                self.assertIsNotNone(adjusted_wpi)
                self.assertIsInstance(adjusted_wpi, float)
                print(f"Age {age}, WPI {wpi}: Adjusted to {adjusted_wpi}")
            except Exception as e:
                self.fail(f"Failed for age {age}, WPI {wpi}: {str(e)}")

if __name__ == '__main__':
    unittest.main()
