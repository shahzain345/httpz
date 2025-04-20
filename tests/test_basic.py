import unittest
import os
import sys

# Add the parent directory to the path to import httpz
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import httpz
from httpz import Session, Browser


class TestBasicFunctionality(unittest.TestCase):
    """Test basic functionality of the httpz client."""
    
    def test_import(self):
        """Test that the module imports correctly."""
        self.assertIsNotNone(httpz)
        self.assertIsNotNone(httpz.Session)
        self.assertIsNotNone(httpz.Browser)
    
    def test_session_creation(self):
        """Test that we can create a session."""
        session = Session()
        self.assertIsNotNone(session)
        session.close()
    
    def test_top_level_functions(self):
        """Test the top level functions."""
        self.assertTrue(callable(httpz.get))
        self.assertTrue(callable(httpz.post))
        self.assertTrue(callable(httpz.put))
        self.assertTrue(callable(httpz.delete))
    
    def test_session_with_context(self):
        """Test that we can use a session as a context manager."""
        with Session() as session:
            self.assertIsNotNone(session)
    
    def test_get_session_utility(self):
        """Test the get_session utility function."""
        session = httpz.get_session()
        self.assertIsNotNone(session)
        session.close()
    
    def test_basic_request(self):
        """Test a basic request (if network is available)."""
        try:
            response = httpz.get("https://httpbin.org/get")
            self.assertIsNotNone(response)
            self.assertEqual(response.status_code, 200)
        except Exception as e:
            self.skipTest(f"Network test skipped: {e}")


if __name__ == '__main__':
    unittest.main() 