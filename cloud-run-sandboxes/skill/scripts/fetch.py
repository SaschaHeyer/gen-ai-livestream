import urllib.request

try:
    body = urllib.request.urlopen("https://api.github.com/zen", timeout=8).read().decode()
    print("FETCH OK:", body)
except Exception as e:
    print("fetch blocked:", type(e).__name__)
