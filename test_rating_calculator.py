import unittest
from unittest.mock import Mock, patch
from rating_calculator import calculate_rating
from datetime import datetime

class TestRatingCalculator(unittest.TestCase):
    def setUp(self):
        # Create a mock Supabase client
        self.mock_supabase = Mock()
        
        # Setup common test data
        self.test_occupation = "Accountant"
        self.test_bodypart = "Lower Back"
        self.test_age_injury = "2023-01-01"
        self.test_wpi = 25
        self.test_pain = 3

    def test_successful_calculation(self):
        # Setup mock chain for occupation query
        mock_occupation_chain = Mock()
        mock_occupation_chain.execute.return_value = Mock(data=[{'occ_group_number': 110}])
        mock_occupation_select = Mock()
        mock_occupation_select.eq.return_value = mock_occupation_chain
        mock_occupation_table = Mock()
        mock_occupation_table.select.return_value = mock_occupation_select
        
        # Setup mock chain for variants query
        mock_variants_chain = Mock()
        mock_variants_chain.execute.return_value = Mock(data=[{
            'vari_impairment_code': 'TEST123',
            'vari_variant': 'A'
        }])
        mock_variants_select = Mock()
        mock_variants_select.eq.return_value = mock_variants_chain
        mock_variants_eq = Mock()
        mock_variants_eq.eq.return_value = mock_variants_select
        mock_variants_table = Mock()
        mock_variants_table.select.return_value = mock_variants_eq
        
        # Setup mock chain for adjustment query
        mock_adjustment_chain = Mock()
        mock_adjustment_chain.execute.return_value = Mock(data=[{'adjustment_value': 1.4}])
        mock_adjustment_variant = Mock()
        mock_adjustment_variant.eq.return_value = mock_adjustment_chain
        mock_adjustment_select = Mock()
        mock_adjustment_select.eq.return_value = mock_adjustment_variant
        mock_adjustment_table = Mock()
        mock_adjustment_table.select.return_value = mock_adjustment_select
        
        # Setup mock chain for age query
        mock_age_chain = Mock()
        mock_age_chain.execute.return_value = Mock(data=[{'22_to_26': 35.5}])
        mock_age_select = Mock()
        mock_age_select.eq.return_value = mock_age_chain
        mock_age_table = Mock()
        mock_age_table.select.return_value = mock_age_select
        
        # Setup mock chain for insert
        mock_insert_chain = Mock()
        mock_insert_chain.execute.return_value = Mock(data=[{}])
        mock_insert_table = Mock()
        mock_insert_table.insert.return_value = mock_insert_chain
        
        # Configure table method to return appropriate mock for each call
        self.mock_supabase.table.side_effect = [
            mock_occupation_table,
            mock_variants_table,
            mock_adjustment_table,
            mock_age_table,
            mock_insert_table
        ]

        result = calculate_rating(
            self.mock_supabase,
            self.test_occupation,
            self.test_bodypart,
            self.test_age_injury,
            self.test_wpi,
            self.test_pain
        )

        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['final_value'], 35.5)
        self.assertEqual(result['details']['group_number'], 110)
        self.assertEqual(result['details']['impairment_code'], 'TEST123')
        self.assertEqual(result['details']['variant'], 'A')
        # Base value (25 + 3) * 1.4 = 39.2
        self.assertEqual(result['details']['adjustment_value'], 1.4)
        self.assertEqual(result['details']['wpi_range'], '22_to_26')

    def test_missing_occupation(self):
        # Setup mock chain for empty occupation response
        mock_empty_chain = Mock()
        mock_empty_chain.execute.return_value = Mock(data=[])
        mock_empty_select = Mock()
        mock_empty_select.eq.return_value = mock_empty_chain
        mock_empty_table = Mock()
        mock_empty_table.select.return_value = mock_empty_select
        
        self.mock_supabase.table.return_value = mock_empty_table

        result = calculate_rating(
            self.mock_supabase,
            self.test_occupation,
            self.test_bodypart,
            self.test_age_injury,
            self.test_wpi
        )

        self.assertEqual(result['status'], 'error')
        self.assertIn('No group number found', result['message'])

    def test_wpi_ranges(self):
        # Test various WPI values and their corresponding ranges
        test_cases = [
            (15, "21_and_under"),
            (22, "22_to_26"),
            (30, "27_to_31"),
            (35, "32_to_36"),
            (40, "37_to_41"),
            (45, "42_to_46"),
            (50, "47_to_51"),
            (55, "52_to_56"),
            (60, "57_to_61"),
            (65, "62_and_over")
        ]

        for wpi, expected_range in test_cases:
            # Setup mock chains for each query
            mock_occupation_chain = Mock()
            mock_occupation_chain.execute.return_value = Mock(data=[{'occ_group_number': 110}])
            mock_occupation_select = Mock()
            mock_occupation_select.eq.return_value = mock_occupation_chain
            mock_occupation_table = Mock()
            mock_occupation_table.select.return_value = mock_occupation_select
            
            mock_variants_chain = Mock()
            mock_variants_chain.execute.return_value = Mock(data=[{
                'vari_impairment_code': 'TEST123',
                'vari_variant': 'A'
            }])
            mock_variants_select = Mock()
            mock_variants_select.eq.return_value = mock_variants_chain
            mock_variants_eq = Mock()
            mock_variants_eq.eq.return_value = mock_variants_select
            mock_variants_table = Mock()
            mock_variants_table.select.return_value = mock_variants_eq
            
            mock_adjustment_chain = Mock()
            mock_adjustment_chain.execute.return_value = Mock(data=[{'adjustment_value': 1.4}])
            mock_adjustment_variant = Mock()
            mock_adjustment_variant.eq.return_value = mock_adjustment_chain
            mock_adjustment_select = Mock()
            mock_adjustment_select.eq.return_value = mock_adjustment_variant
            mock_adjustment_table = Mock()
            mock_adjustment_table.select.return_value = mock_adjustment_select
            
            mock_age_chain = Mock()
            mock_age_chain.execute.return_value = Mock(data=[{expected_range: 35.5}])
            mock_age_select = Mock()
            mock_age_select.eq.return_value = mock_age_chain
            mock_age_table = Mock()
            mock_age_table.select.return_value = mock_age_select
            
            mock_insert_chain = Mock()
            mock_insert_chain.execute.return_value = Mock(data=[{}])
            mock_insert_table = Mock()
            mock_insert_table.insert.return_value = mock_insert_chain
            
            self.mock_supabase.table.side_effect = [
                mock_occupation_table,
                mock_variants_table,
                mock_adjustment_table,
                mock_age_table,
                mock_insert_table
            ]

            result = calculate_rating(
                self.mock_supabase,
                self.test_occupation,
                self.test_bodypart,
                self.test_age_injury,
                wpi,
                self.test_pain
            )

            self.assertEqual(result['status'], 'success')
            self.assertEqual(result['details']['wpi_range'], expected_range)

    def test_pain_calculation(self):
        # Setup mock chains
        mock_occupation_chain = Mock()
        mock_occupation_chain.execute.return_value = Mock(data=[{'occ_group_number': 110}])
        mock_occupation_select = Mock()
        mock_occupation_select.eq.return_value = mock_occupation_chain
        mock_occupation_table = Mock()
        mock_occupation_table.select.return_value = mock_occupation_select
        
        mock_variants_chain = Mock()
        mock_variants_chain.execute.return_value = Mock(data=[{
            'vari_impairment_code': 'TEST123',
            'vari_variant': 'A'
        }])
        mock_variants_select = Mock()
        mock_variants_select.eq.return_value = mock_variants_chain
        mock_variants_eq = Mock()
        mock_variants_eq.eq.return_value = mock_variants_select
        mock_variants_table = Mock()
        mock_variants_table.select.return_value = mock_variants_eq
        
        # Test with WPI 10 and pain 3
        # Base value should be 13 (10 + 3)
        # Adjusted value should be 18.2 (13 * 1.4)
        mock_adjustment_chain = Mock()
        mock_adjustment_chain.execute.return_value = Mock(data=[{'adjustment_value': 1.2}])
        mock_adjustment_variant = Mock()
        mock_adjustment_variant.eq.return_value = mock_adjustment_chain
        mock_adjustment_select = Mock()
        mock_adjustment_select.eq.return_value = mock_adjustment_variant
        mock_adjustment_table = Mock()
        mock_adjustment_table.select.return_value = mock_adjustment_select
        
        mock_age_chain = Mock()
        mock_age_chain.execute.return_value = Mock(data=[{'21_and_under': 25.0}])
        mock_age_select = Mock()
        mock_age_select.eq.return_value = mock_age_chain
        mock_age_table = Mock()
        mock_age_table.select.return_value = mock_age_select
        
        mock_insert_chain = Mock()
        mock_insert_chain.execute.return_value = Mock(data=[{}])
        mock_insert_table = Mock()
        mock_insert_table.insert.return_value = mock_insert_chain
        
        self.mock_supabase.table.side_effect = [
            mock_occupation_table,
            mock_variants_table,
            mock_adjustment_table,
            mock_age_table,
            mock_insert_table
        ]

        result = calculate_rating(
            self.mock_supabase,
            self.test_occupation,
            self.test_bodypart,
            self.test_age_injury,
            10,  # WPI
            3    # Pain
        )

        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['details']['wpi_range'], '21_and_under')
        self.assertEqual(result['details']['adjustment_value'], 1.2)

    def test_database_error(self):
        # Setup mock chain for database error
        mock_error_chain = Mock()
        mock_error_chain.execute.side_effect = Exception("Database error")
        mock_error_select = Mock()
        mock_error_select.eq.return_value = mock_error_chain
        mock_error_table = Mock()
        mock_error_table.select.return_value = mock_error_select
        
        self.mock_supabase.table.return_value = mock_error_table

        result = calculate_rating(
            self.mock_supabase,
            self.test_occupation,
            self.test_bodypart,
            self.test_age_injury,
            self.test_wpi
        )

        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['message'], 'Database error')

if __name__ == '__main__':
    unittest.main()
