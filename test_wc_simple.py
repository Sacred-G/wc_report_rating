import unittest
from unittest.mock import Mock, patch
from wc_simple import process_report, format_results_with_ai
from datetime import datetime

class TestWCSimple(unittest.TestCase):
    def setUp(self):
        # Sample medical report text
        self.sample_report = """
        Patient Report
        
        Occupation: Software Engineer
        Date of Injury: 01/15/2023
        Body Part: Lower Back
        WPI: 25
        
        Additional findings and notes...
        """

    @patch('wc_simple.supabase')
    @patch('wc_simple.client')
    @patch('wc_simple.fetch_occupational_adjustments')
    @patch('wc_simple.get_calculation_results')
    def test_process_report(self, mock_get_calc_results, mock_fetch_adj, mock_openai_client, mock_supabase):
        # Mock fetch_occupational_adjustments
        mock_fetch_adj.return_value = [(1, 1.4)]

        # Mock Supabase client and its methods
        mock_supabase_instance = Mock()
        mock_supabase.return_value = mock_supabase_instance

        # Mock data for workers_comp.occupational
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(data=[{'occ_group_number': 3}])

        # Mock data for workers_comp.variants
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = Mock(data=[{'vari_impairment_code': '8001', 'vari_variant': '00'}])

        # Mock data for workers_comp.occupational_adjustment
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(data=[{'adjustment_value': 1.04}])

        # Mock data for workers_comp.age_adjustment
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(data=[{'43_to_47': 0.97}])
import unittest
from unittest.mock import Mock, patch
from wc_simple import process_report, format_results_with_ai
from datetime import datetime

class TestWCSimple(unittest.TestCase):
    def setUp(self):
        # Sample medical report text
        self.sample_report = """
        Patient Report
        
        Occupation: Software Engineer
        Date of Injury: 01/15/2023
        Body Part: Lower Back
        WPI: 25
        
        Additional findings and notes...
        """

    @patch('wc_simple.supabase')
    @patch('wc_simple.client')
    @patch('wc_simple.fetch_occupational_adjustments')
    @patch('wc_simple.get_calculation_results')
    def test_process_report(self, mock_get_calc_results, mock_fetch_adj, mock_openai_client, mock_supabase):
        # Mock fetch_occupational_adjustments
        mock_fetch_adj.return_value = [(1, 1.4)]

        # Mock Supabase client and its methods
        mock_supabase_instance = Mock()
        mock_supabase.return_value = mock_supabase_instance

        # Mock data for workers_comp.occupational
        # Mock data for workers_comp.occupational
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(data=[{'occ_group_number': 3}])

        # Mock data for workers_comp.variants
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = Mock(data=[{'vari_impairment_code': '8001', 'vari_variant': '00'}])

        # Mock data for workers_comp.occupational_adjustment
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(data=[{'adjustment_value': 1.04}])

        # Mock data for workers_comp.age_adjustment
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(data=[{'43_to_47': 0.97}])
import unittest
from unittest.mock import Mock, patch
from wc_simple import process_report, format_results_with_ai
from datetime import datetime

class TestWCSimple(unittest.TestCase):
    def setUp(self):
        # Sample medical report text
        self.sample_report = """
        Patient Report
        
        Occupation: Software Engineer
        Date of Injury: 01/15/2023
        Body Part: Lower Back
        WPI: 25
        
        Additional findings and notes...
        """

    @patch('wc_simple.supabase')
    @patch('wc_simple.client')
    @patch('wc_simple.fetch_occupational_adjustments')
    @patch('wc_simple.get_calculation_results')
    def test_process_report(self, mock_get_calc_results, mock_fetch_adj, mock_openai_client, mock_supabase):
        # Mock fetch_occupational_adjustments
        mock_fetch_adj.return_value = [(1, 1.4)]

        # Mock Supabase client and its methods
        mock_supabase_instance = Mock()
        mock_supabase.return_value = mock_supabase_instance

        # Mock data for workers_comp.occupational
        # Mock data for workers_comp.occupational
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(data=[{'occ_group_number': 110}])

        # Mock data for workers_comp.variants
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = Mock(data=[{'vari_impairment_code': 'TEST123', 'vari_variant': 'A'}])

        # Mock data for workers_comp.occupational_adjustment
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(data=[{'adjustment_value': 1.4}])

        # Mock data for workers_comp.age_adjustment
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(data=[{'22_to_26': 1.0}])
import unittest
from unittest.mock import Mock, patch
from wc_simple import process_report, format_results_with_ai
from datetime import datetime

class TestWCSimple(unittest.TestCase):
    def setUp(self):
        # Sample medical report text
        self.sample_report = """
        Patient Report
        
        Occupation: Software Engineer
        Date of Injury: 01/15/2023
        Body Part: Lower Back
        WPI: 25
        
        Additional findings and notes...
        """

    @patch('wc_simple.supabase')
    @patch('wc_simple.client')
    @patch('wc_simple.fetch_occupational_adjustments')
    @patch('wc_simple.get_calculation_results')
    def test_process_report(self, mock_get_calc_results, mock_fetch_adj, mock_openai_client, mock_supabase):
        # Mock fetch_occupational_adjustments
        mock_fetch_adj.return_value = [(1, 1.4)]

        # Mock Supabase client and its methods
        mock_supabase_instance = Mock()
        mock_supabase.return_value = mock_supabase_instance

        # Mock data for workers_comp.occupational
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(data=[{'occ_group_number': 110}])

        # Mock data for workers_comp.variants
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = Mock(data=[{'vari_impairment_code': 'TEST123', 'vari_variant': 'A'}])

        # Mock data for workers_comp.occupational_adjustment
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(data=[{'adjustment_value': 1.4}])

        # Mock data for workers_comp.age_adjustment
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(data=[{'22_to_26': 1.0}])

        # Mock insert for calculated_med_results
        mock_supabase_instance.table.return_value.insert.return_value.execute.return_value = Mock(data=[{'id': 1}])

        # Mock get_calculation_results
        mock_get_calc_results.return_value = {
            'id': 1,
            'input_id': 110,
            'total_pd': 35.0,
            'payment_weeks': 52,
            'weekly_rate': 300.0,
            'total_payout': 15600.0,
            'created_at': datetime.now().isoformat()
        }

        # Mock OpenAI client for assistants API
        mock_openai_client.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content="Formatted Results"))]
        )

        result = process_report(self.sample_report)

        self.assertIsNotNone(result)
        self.assertEqual(result, "Formatted Results")
import unittest
from unittest.mock import Mock, patch
from wc_simple import process_report, format_results_with_ai
from datetime import datetime

class TestWCSimple(unittest.TestCase):
    def setUp(self):
        # Sample medical report text
        self.sample_report = """
        Patient Report
        
        Occupation: Software Engineer
        Date of Injury: 01/15/2023
        Body Part: Lower Back
        WPI: 25
        
        Additional findings and notes...
        """

    @patch('wc_simple.supabase')
    @patch('wc_simple.client')
    @patch('wc_simple.fetch_occupational_adjustments')
    @patch('wc_simple.get_calculation_results')
    def test_process_report(self, mock_get_calc_results, mock_fetch_adj, mock_openai_client, mock_supabase):
        # Mock fetch_occupational_adjustments
        mock_fetch_adj.return_value = [(1, 1.4)]

        # Mock Supabase client and its methods
        mock_supabase_instance = Mock()
        mock_supabase.return_value = mock_supabase_instance
        mock_supabase_instance.table.return_value.insert.return_value.execute.return_value = Mock(data=[{'id': 1}])
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(data=[{'group_number': 110}])

        # Mock get_calculation_results
        mock_get_calc_results.return_value = {
            'id': 1,
            'input_id': 110,
            'total_pd': 35.0,
            'payment_weeks': 52,
            'weekly_rate': 300.0,
            'total_payout': 15600.0,
            'created_at': datetime.now().isoformat()
        }

        # Mock OpenAI client for assistants API
        mock_openai_client.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content="Formatted Results"))]
        )

        result = process_report(self.sample_report)

        self.assertIsNotNone(result)
        self.assertEqual(result, "Formatted Results")

    def test_process_report_missing_data(self):
        # Test with missing required fields
        incomplete_report = """
        Patient Report
        Some text without required fields
        """

        result = process_report(incomplete_report)
        self.assertIsNone(result)

    @patch('wc_simple.client')
    def test_format_results_with_ai(self, mock_client):
        # Test data
        test_results = {
            "input_data": {
                "occupation": "Software Engineer",
                "bodypart": "Lower Back",
                "age_injury": "2023-01-15",
                "wpi": 25,
                "adjusted_value": 35
            },
            "rating_details": {
                "group_number": 110,
                "impairment_code": "TEST123",
                "variant": "A",
                "adjustment_value": 1.4,
                "wpi_range": "22_to_26"
            },
            "final_value": 35.5,
            "calculation_results": {
                "total_pd": 35.0,
                "payment_weeks": 52,
                "weekly_rate": 300.0,
                "total_payout": 15600.0
            }
        }

        # Mock AI response
        mock_client.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content="Formatted Results"))]
        )

        result = format_results_with_ai(test_results)
        self.assertEqual(result, "Formatted Results")

        # Verify AI was called with correct prompt
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args[1]
        self.assertEqual(call_args['model'], 'gpt-4')
        self.assertEqual(call_args['temperature'], 0)
        self.assertTrue(isinstance(call_args['messages'], list))
        self.assertIn('workers compensation calculation results', call_args['messages'][0]['content'])

    @patch('wc_simple.client')
    def test_format_results_with_ai_error(self, mock_client):
        # Test handling of AI error
        mock_client.chat.completions.create.side_effect = Exception("API Error")

        test_results = {"test": "data"}
        result = format_results_with_ai(test_results)

        # Should fall back to JSON string
        self.assertEqual(result, '{\n  "test": "data"\n}')

if __name__ == '__main__':
    unittest.main()
