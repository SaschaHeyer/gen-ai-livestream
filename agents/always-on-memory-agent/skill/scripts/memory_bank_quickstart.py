"""Vertex AI Memory Bank quickstart, the managed alternative to the always-on sample.

Creates the agent engine that hosts a memory bank, consolidates a text file into
managed memories, then retrieves by similarity search. Verified against the live
service during the episode. Point it at your own file and question.

Auth, standard Application Default Credentials:
    gcloud auth application-default login
    gcloud config set project YOUR_PROJECT

Usage:
    python memory_bank_quickstart.py --project YOUR_PROJECT --file notes.txt \
        --query "what do you know about the project?" --user alice

The key difference from the always-on sample, retrieval here is a scoped vector
similarity search, not a load of the most recent rows.
"""
import argparse
import time

import vertexai


def main():
    ap = argparse.ArgumentParser(description="Vertex AI Memory Bank quickstart")
    ap.add_argument("--project", required=True)
    ap.add_argument("--location", default="us-central1")
    ap.add_argument("--file", required=True, help="text file to consolidate into memories")
    ap.add_argument("--query", required=True, help="question to retrieve against")
    ap.add_argument("--user", default="user", help="scope, isolates memories per user")
    ap.add_argument("--engine", default="", help="reuse an existing agent engine resource name")
    args = ap.parse_args()

    client = vertexai.Client(project=args.project, location=args.location)
    scope = {"user_id": args.user}

    # create the memory bank host, or reuse one you already made
    if args.engine:
        name = args.engine
    else:
        t = time.time()
        engine = client.agent_engines.create()
        name = engine.api_resource.name
        print(f"created agent engine in {time.time() - t:.1f}s")
        print(f"  reuse it next time with --engine {name}")

    text = open(args.file).read()

    # consolidate the content into managed memories, deduped and merged by the service
    client.agent_engines.generate_memories(
        name=name,
        direct_contents_source={"events": [{"content": {"role": "user", "parts": [{"text": text}]}}]},
        scope=scope,
    )

    # wait for the generate operation to land
    memories = []
    for _ in range(30):
        time.sleep(4)
        memories = list(client.agent_engines.list_memories(name=name))
        if memories:
            break
    print(f"\nmanaged memories, {len(memories)}:")
    for m in memories:
        print("  -", getattr(m, "fact", None))

    # retrieve by scoped vector similarity search
    t = time.time()
    hits = list(client.agent_engines.retrieve_memories(
        name=name,
        scope=scope,
        similarity_search_params={"search_query": args.query, "top_k": 5},
    ))
    print(f"\nretrieved {len(hits)} by similarity in {time.time() - t:.1f}s:")
    for h in hits:
        print("  *", getattr(getattr(h, "memory", None), "fact", None))


if __name__ == "__main__":
    main()
