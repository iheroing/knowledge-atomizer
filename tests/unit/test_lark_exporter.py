"""Unit tests for Lark Exporter retry logic.

Feature: knowledge-atomizer
Validates: Requirements 3.3
"""

import unittest
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, '.')

from src.exporters.lark_exporter import LarkClient, NetworkError


class TestLarkClientRetry(unittest.TestCase):
    """Test retry logic for LarkClient."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = LarkClient("test_app_id", "test_app_secret")
        # Pre-set a valid token to skip token fetching
        self.client._access_token = "test_token"
        self.client._token_expires_at = float('inf')
    
    @patch('src.exporters.lark_exporter.requests.post')
    def test_retry_on_network_error_max_3_times(self, mock_post):
        """
        Test that network errors trigger retry up to 3 times.
        Validates: Requirements 3.3
        """
        import requests
        
        # Simulate network error on all attempts
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection failed")
        
        with self.assertRaises(NetworkError) as context:
            self.client.batch_create_records("app_token", "table_id", [{"fields": {}}])
        
        # Verify retry count (should be exactly MAX_RETRIES = 3)
        self.assertEqual(mock_post.call_count, 3)
        self.assertIn("已重试 3 次", str(context.exception))
    
    @patch('src.exporters.lark_exporter.requests.post')
    def test_success_after_retry(self, mock_post):
        """
        Test that successful response after retry works correctly.
        Validates: Requirements 3.3
        """
        # First two calls fail, third succeeds
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {"records": [{"record_id": "rec1"}]}
        }
        mock_response.raise_for_status = MagicMock()
        
        import requests
        mock_post.side_effect = [
            requests.exceptions.ConnectionError("Connection failed"),
            requests.exceptions.Timeout("Timeout"),
            mock_response
        ]
        
        result = self.client.batch_create_records("app_token", "table_id", [{"fields": {}}])
        
        # Should succeed on third attempt
        self.assertEqual(mock_post.call_count, 3)
        self.assertEqual(result["code"], 0)
    
    @patch('src.exporters.lark_exporter.requests.post')
    def test_no_retry_on_success(self, mock_post):
        """
        Test that successful response doesn't trigger retry.
        """
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {"records": [{"record_id": "rec1"}]}
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response
        
        result = self.client.batch_create_records("app_token", "table_id", [{"fields": {}}])
        
        # Should only call once
        self.assertEqual(mock_post.call_count, 1)
        self.assertEqual(result["code"], 0)


if __name__ == '__main__':
    unittest.main()
