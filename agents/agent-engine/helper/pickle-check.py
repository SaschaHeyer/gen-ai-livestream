import cloudpickle
for tool in agent._tools:
    try:
        cloudpickle.dumps(tool)
        print(f"✅ {tool.__name__} is serializable")
    except Exception as e:
        print(f"❌ {tool.__name__} is not serializable: {e}")
