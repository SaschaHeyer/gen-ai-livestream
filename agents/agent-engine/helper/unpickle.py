import pickle

def unpickle_file(file_path):
    """Load a pickled file."""
    try:
        with open(file_path, 'rb') as file:
            data = pickle.load(file)
        return data
    except (pickle.UnpicklingError, FileNotFoundError, EOFError) as e:
        print(f"Error unpickling file: {e}")
        return None

def inspect_object(obj):
    """Inspect the properties of an unpickled object."""
    if obj is None:
        print("No object to inspect.")
        return

    print("Type of object:", type(obj))
    print("\nAvailable attributes and methods:")
    print(dir(obj))

    if hasattr(obj, '__dict__'):
        print("\nObject attributes (__dict__):")
        print(obj.__dict__)

    print("\nString representation of object:")
    print(str(obj))

    print("\nDetailed representation of object:")
    print(repr(obj))


def inspect_system_instruction(obj):
    """Extract and print the system instruction if available."""
    if hasattr(obj, '_system_instruction'):
        print("\nSystem Instruction:")
        print(obj._system_instruction)
        print(obj._model_name)
    else:
        print("\nNo system instruction found.")

# Example usage
file_path = "agent_engine_agent_engine.pkl"  # Replace with your actual file path
unpickled_data = unpickle_file(file_path)
inspect_object(unpickled_data)


inspect_system_instruction(unpickled_data)
