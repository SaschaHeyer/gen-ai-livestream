import unittest
from main import hello_world
import io
import sys

class TestHelloWorld(unittest.TestCase):

    def test_hello_world(self):
        """Tests the hello_world function."""
        captured_output = io.StringIO()
        sys.stdout = captured_output
        hello_world()
        sys.stdout = sys.__stdout__
        self.assertEqual(captured_output.getvalue().strip(), "Hello, World!")

if __name__ == '__main__':
    unittest.main()
