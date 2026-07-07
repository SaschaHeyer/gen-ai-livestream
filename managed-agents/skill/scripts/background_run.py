"""Beat 1, fire and forget. Kick off a real task, get an id back instantly."""
import agent

rec = agent.create(
    input="Create a folder stream-tools/ and write chapters.py inside that turns "
          "a list of video timestamps into YouTube chapter markers.",
    background=True,
)
print("id:    ", rec.id)
print("status:", rec.status)   # in_progress, it did not wait for the work
print()
print("Save this id, that is your claim ticket:")
print(rec.id)
