import requests
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Get the Flask app URL from environment or use default
FLASK_APP_URL = os.environ.get('FLASK_APP_URL', 'http://127.0.0.1:5000')

def test_flask_connection():
    """Test if the Flask app is running and accessible"""
    try:
        # Test the basic connection
        response = requests.get(f"{FLASK_APP_URL}/test", timeout=5)
        print(f"Connection test result: {response.status_code}")
        print(f"Response content: {response.text}")

        if response.status_code == 200:
            print("✅ Success! Flask app is running and accessible.")
        else:
            print(f"❌ Error: Received status code {response.status_code}")
            return False

        # Test the escalation endpoint
        test_question = "This is a test question for human escalation."
        print("\nTesting escalation endpoint...")

        escalation_response = requests.post(
            f"{FLASK_APP_URL}/escalate",
            json={"question": test_question},
            headers={"Content-Type": "application/json"},
            timeout=5
        )

        print(f"Escalation test result: {escalation_response.status_code}")
        print(f"Response content: {escalation_response.text}")

        if escalation_response.status_code == 200:
            print("✅ Success! Escalation endpoint is working properly.")
            # Get the conversation ID from the response
            data = escalation_response.json()
            conversation_id = data.get('conversation_id')

            if conversation_id:
                print(f"\nCreated test conversation with ID: {conversation_id}")
                print(f"You can check it at: {FLASK_APP_URL}/respond/{conversation_id}")
            return True
        else:
            print(f"❌ Error: Escalation endpoint returned status code {escalation_response.status_code}")
            return False

    except requests.exceptions.ConnectionError:
        print(f"❌ Connection Error: Could not connect to {FLASK_APP_URL}")
        print("Make sure the Flask app is running and the URL is correct.")
        print("Run 'python -m flask --app app run' to start the Flask app.")
        return False
    except requests.exceptions.Timeout:
        print(f"❌ Timeout Error: Connection to {FLASK_APP_URL} timed out")
        print("The server might be slow or unresponsive.")
        return False
    except Exception as e:
        print(f"❌ Unexpected Error: {str(e)}")
        return False

if __name__ == "__main__":
    print(f"Testing connection to Flask app at: {FLASK_APP_URL}")
    success = test_flask_connection()

    if not success:
        print("\nTroubleshooting tips:")
        print("1. Make sure the Flask app is running")
        print("2. Check if the PORT environment variable is set correctly")
        print("3. Verify that FLASK_APP_URL in .env matches the actual URL")
        print("4. Check if there are any firewall or network issues")
        sys.exit(1)
    else:
        print("\nAll tests passed! The Flask app is working correctly.")
        sys.exit(0)
