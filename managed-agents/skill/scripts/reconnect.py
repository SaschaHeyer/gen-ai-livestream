"""Beat 2, reconnect. Fresh process, only the id. Poll until done, show the work.

Usage, pass the id printed by background_run.py:
    python reconnect.py <interaction_id>
"""
import sys
import agent

interaction_id = sys.argv[1]
print(f"reconnecting to {interaction_id} ...")
rec = agent.poll(interaction_id)
print("status:", rec.status)
print("steps the agent ran while we were disconnected:")
agent.show_steps(rec)
