"""Beat 1, fire and forget. Kick off a real task, get an id back instantly."""
import agent

rec = agent.create(
    input="Create a folder named project/ and write hello.py inside that prints hi.",
    background=True,
)
print("id:    ", rec.id)
print("status:", rec.status)   # in_progress, it did not wait for the work
print()
print("Save this id, that is your claim ticket:")
print(rec.id)
