import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import io

# Add the parent directory to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.ai_extractor import (
    extract_impairments_with_regex,
    extract_json_from_response,
    merge_impairments,
    standardize_impairments
)

class TestAIExtractor(unittest.TestCase):
    
    def test_extract_impairments_with_regex(self):
        """Test the regex-based impairment extraction."""
        # Sample text with impairments
        sample_text = """
        The patient has a lumbar spine impairment of 8% WPI.
        The cervical spine has a whole person impairment of 5%.
        The right shoulder impairment is 10 percent.
        """
        
        # Extract impairments
        impairments = extract_impairments_with_regex(sample_text)
        
        # Verify results
        self.assertEqual(len(impairments), 3)
        
        # Check if all expected impairments are found
        body_parts = [imp['body_part'].lower() for imp in impairments]
        wpi_values = [imp['wpi'] for imp in impairments]
        
        # Check that we have the expected body parts (or parts of them)
        self.assertTrue(any('spine' in bp for bp in body_parts))
        self.assertTrue(any('cervical' in bp for bp in body_parts))
        self.assertTrue(any('shoulder' in bp for bp in body_parts))
        
        self.assertIn(8, wpi_values)
        self.assertIn(5, wpi_values)
        self.assertIn(10, wpi_values)
    
    def test_extract_json_from_response(self):
        """Test JSON extraction from various response formats."""
        # Test direct JSON
        direct_json = '{"impairments":[{"body_part":"Lumbar Spine","wpi":8,"pain_addon":2,"apportionment":0}]}'
        result = extract_json_from_response(direct_json)
        self.assertEqual(len(result['impairments']), 1)
        self.assertEqual(result['impairments'][0]['wpi'], 8)
        
        # Test JSON in code block
        code_block_json = '```json\n{"impairments":[{"body_part":"Cervical Spine","wpi":5,"pain_addon":1,"apportionment":0}]}\n```'
        result = extract_json_from_response(code_block_json)
        self.assertEqual(len(result['impairments']), 1)
        self.assertEqual(result['impairments'][0]['wpi'], 5)
        
        # Test invalid JSON
        invalid_json = 'This is not JSON'
        result = extract_json_from_response(invalid_json)
        self.assertEqual(result, {"impairments": []})
    
    def test_merge_impairments(self):
        """Test merging impairments from AI and regex extraction."""
        # AI impairments
        ai_impairments = [
            {'body_part': 'Lumbar Spine', 'wpi': 8, 'pain_addon': 2, 'apportionment': 0},
            {'body_part': 'Cervical Spine', 'wpi': 5, 'pain_addon': 1, 'apportionment': 0}
        ]
        
        # Regex impairments
        regex_impairments = [
            {'body_part': 'Lumbar Spine', 'wpi': 8, 'pain_addon': 0, 'apportionment': 0},  # Duplicate
            {'body_part': 'Shoulder', 'wpi': 10, 'pain_addon': 0, 'apportionment': 0}  # New
        ]
        
        # Merge impairments
        merged = merge_impairments(ai_impairments, regex_impairments)
        
        # Verify results
        self.assertEqual(len(merged), 3)  # Should have 3 unique impairments
        
        # Check if all expected impairments are in the merged list
        body_parts = [imp['body_part'].lower() for imp in merged]
        self.assertIn('lumbar spine', body_parts)
        self.assertIn('cervical spine', body_parts)
        self.assertIn('shoulder', body_parts)
        
        # Check that AI impairments take precedence
        for imp in merged:
            if imp['body_part'].lower() == 'lumbar spine':
                self.assertEqual(imp['pain_addon'], 2)  # Should use AI value
    
    def test_merge_impairments_with_synonyms(self):
        """Test merging impairments with synonymous body part names."""
        # AI impairments
        ai_impairments = [
            {'body_part': 'Lumbar Spine', 'wpi': 8, 'pain_addon': 2, 'apportionment': 0},
            {'body_part': 'Shoulder', 'wpi': 10, 'pain_addon': 1, 'apportionment': 0}
        ]
        
        # Regex impairments with synonymous body parts
        regex_impairments = [
            {'body_part': 'Back', 'wpi': 8, 'pain_addon': 0, 'apportionment': 0},  # Synonym for Lumbar Spine
            {'body_part': 'Lumbar', 'wpi': 14, 'pain_addon': 0, 'apportionment': 0},  # Different WPI, same body part
            {'body_part': 'Knee', 'wpi': 5, 'pain_addon': 0, 'apportionment': 0}  # New body part
        ]
        
        # Merge impairments
        merged = merge_impairments(ai_impairments, regex_impairments)
        
        # Verify results - should have 4 unique impairments (not 5)
        # Lumbar Spine (8% WPI) and Back (8% WPI) should be merged as the same body part
        # But Lumbar (14% WPI) should remain as a separate entry since it has a different WPI
        self.assertEqual(len(merged), 4)
        
        # Count the number of back/lumbar related impairments (should be 2, not 3)
        back_related_count = 0
        for imp in merged:
            body_part_lower = imp['body_part'].lower()
            if 'lumbar' in body_part_lower or 'back' in body_part_lower or 'spine' in body_part_lower:
                back_related_count += 1
        
        self.assertEqual(back_related_count, 2)
        
        # Check that all expected WPI values are present
        wpi_values = [imp['wpi'] for imp in merged]
        self.assertIn(8, wpi_values)  # Lumbar Spine/Back
        self.assertIn(14, wpi_values)  # Lumbar with different WPI
        self.assertIn(10, wpi_values)  # Shoulder
        self.assertIn(5, wpi_values)  # Knee

    def test_standardize_impairments(self):
        """Test standardizing impairments with consistent body part names and codes."""
        # Sample impairments with different body part names
        impairments = [
            {'body_part': 'Lumbar Spine', 'wpi': 8, 'pain_addon': 2, 'apportionment': 0},
            {'body_part': 'Back', 'wpi': 3, 'pain_addon': 0, 'apportionment': 0},
            {'body_part': 'Rib', 'wpi': 7, 'pain_addon': 0, 'apportionment': 0},
            {'body_part': 'Knee', 'wpi': 20, 'pain_addon': 0, 'apportionment': 0}
        ]
        
        # Standardize impairments
        standardized = standardize_impairments(impairments)
        
        # Verify results
        self.assertEqual(len(standardized), 4)
        
        # Check that all impairments have standardized codes and body part names
        for imp in standardized:
            self.assertTrue('impairment_code' in imp)
            self.assertTrue('formatted_string' in imp)
            
            # Check specific mappings
            if 'lumbar' in imp['body_part'].lower() or 'back' in imp['body_part'].lower():
                self.assertTrue(imp['impairment_code'].startswith('15.'))  # Spine codes start with 15
            elif 'rib' in imp['body_part'].lower():
                self.assertTrue(imp['impairment_code'].startswith('05.'))  # Respiratory system codes start with 05
            elif 'knee' in imp['body_part'].lower():
                self.assertTrue(imp['impairment_code'].startswith('17.'))  # Lower extremities codes start with 17

if __name__ == '__main__':
    unittest.main()
