from agent import app
import inspect

print("Inspecting local AdkApp instance:")
print(f"Type: {type(app)}")
print(f"Dir: {dir(app)}")

print("\nMethods:")
for name, method in inspect.getmembers(app, predicate=inspect.ismethod):
    if not name.startswith("_"):
        print(f" - {name}")

if hasattr(app, 'async_stream_query'):
    print("\n[SUCCESS] 'async_stream_query' is present on the local object.")
else:
    print("\n[FAILURE] 'async_stream_query' is MISSING from the local object.")
