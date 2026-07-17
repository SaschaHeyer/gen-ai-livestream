# Head to head, the always-on sample vs Vertex AI Memory Bank

Both run on the same three inputs, a markdown note, a chat screenshot, an audio memo.

## The sample, verified run

- 3 files became 3 memories, one per file, model assigned importance 0.9, 0.7, 0.7.
- Ingest latency 2.4 to 4.7s per file, each is an orchestrator to sub agent to tool roundtrip.
- Consolidate 2.8s, one insight row from source ids [1, 2, 3].
- Query 1.9s, answered citing [Memory 1, Memory 2, Memory 3].
- Retrieval, `SELECT * FROM memories ORDER BY created_at DESC LIMIT 50`, no vector search.
- Consolidation input, `read_unconsolidated_memories` at LIMIT 10.
- Always-on HTTP path verified, /ingest, /consolidate, /query all work.

## Vertex AI Memory Bank, verified run

- Create the agent engine that hosts the memory bank, 4.3s.
- `generate_memories` merged the same 3 events into 2 memories, deduped and stored first person per user.
- `retrieve_memories`, scoped vector similarity search, 2 ranked hits in 0.7s.

## The differences

| | The sample | Memory Bank |
| --- | --- | --- |
| Retrieval | recent 50 rows, no similarity | scoped vector similarity search |
| Consolidation | 1 memory per file plus an insight | merged 3 events into 2 |
| Perspective | third person summaries | first person user memories |
| Isolation | one shared SQLite file | scoped per user_id |
| Setup | pip install, local, API key | GCP project, engine create 4.3s |
| Ops | you run server, loop, DB | fully managed |

The deciding row is retrieval. The sample removed the vector database and loads a recent window. Memory Bank keeps the similarity search. That is what changes how each behaves as memory grows.
