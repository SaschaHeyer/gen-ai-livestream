try:
    from google.cloud import discoveryengine
    print("Success: from google.cloud import discoveryengine")
except ImportError as e:
    print(f"Failed: from google.cloud import discoveryengine - {e}")

try:
    from google.cloud import discoveryengine_v1
    print("Success: from google.cloud import discoveryengine_v1")
except ImportError as e:
    print(f"Failed: from google.cloud import discoveryengine_v1 - {e}")

try:
    from google.cloud import discoveryengine_v1beta
    print("Success: from google.cloud import discoveryengine_v1beta")
except ImportError as e:
    print(f"Failed: from google.cloud import discoveryengine_v1beta - {e}")

import google.cloud.discoveryengine
print(f"Direct import: {google.cloud.discoveryengine}")
