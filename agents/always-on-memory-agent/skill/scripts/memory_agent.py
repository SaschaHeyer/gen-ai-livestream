"""Always-on memory agent, ingest, consolidate, query, over SQLite.

Built on Google ADK LlmAgents plus Gemini 3.1 Flash Lite. Each agent returns a
structured result via output_schema. Memory lives in a plain SQLite file so you
can see that the magic is the model connecting notes, not the database.

Usage
  python memory_agent.py reset
  python memory_agent.py ingest sample-files/nordlicht-kickoff.md sample-files/nordlicht-chat.png
  python memory_agent.py consolidate
  python memory_agent.py query "Who is doing the Nordlicht thumbnail and is it done?"
"""
import asyncio
import json
import mimetypes
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel
from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner
from google.genai import types

MODEL = os.environ.get("MEMORY_MODEL", "gemini-3.1-flash-lite")
DB = os.environ.get("MEMORY_DB", "memory.db")


# --- structured shapes the agents must return -------------------------------
class MemoryItem(BaseModel):
    content: str
    entities: list[str]


class IngestResult(BaseModel):
    memories: list[MemoryItem]


class Insight(BaseModel):
    content: str
    source_ids: list[int]


class ConsolidateResult(BaseModel):
    insights: list[Insight]


class QueryResult(BaseModel):
    answer: str
    cited_ids: list[int]


# --- the three agents, this is the ADK surface the skill ships --------------
ingest_agent = LlmAgent(
    name="ingest",
    model=MODEL,
    instruction=(
        "You extract durable memories from whatever the user sends, text, an image, "
        "or audio. Pull out each standalone fact worth remembering later, a person, a "
        "decision, a date, an owner. Keep each memory one short sentence and list the "
        "key entities in it. Ignore small talk."
    ),
    output_schema=IngestResult,
    output_key="ingest",
)

consolidate_agent = LlmAgent(
    name="consolidate",
    model=MODEL,
    instruction=(
        "You are given a numbered list of raw memories. Find memories that are about "
        "the same person, project, or event and write a higher level insight that "
        "connects them. Only emit an insight when it links two or more different "
        "memories, and list the exact source ids you used. Do not repeat a single "
        "memory back as an insight."
    ),
    output_schema=ConsolidateResult,
    output_key="consolidate",
)

query_agent = LlmAgent(
    name="query",
    model=MODEL,
    instruction=(
        "You answer the user's question using only the numbered memories provided. "
        "Cite the exact memory ids you relied on. If the memories do not answer it, "
        "say so plainly instead of guessing."
    ),
    output_schema=QueryResult,
    output_key="query",
)


# --- storage ----------------------------------------------------------------
def db():
    con = sqlite3.connect(DB)
    con.execute(
        "CREATE TABLE IF NOT EXISTS memories ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, content TEXT, "
        "source TEXT, source_ids TEXT, created_at TEXT)"
    )
    return con


def add_memory(con, kind, content, source="", source_ids=None):
    con.execute(
        "INSERT INTO memories (kind, content, source, source_ids, created_at) "
        "VALUES (?,?,?,?,?)",
        (kind, content, source, json.dumps(source_ids or []),
         datetime.now(timezone.utc).isoformat(timespec="seconds")),
    )
    con.commit()


def all_memories(con, kind=None):
    q = "SELECT id, kind, content, source FROM memories"
    if kind:
        q += " WHERE kind=?"
        return con.execute(q, (kind,)).fetchall()
    return con.execute(q).fetchall()


# --- run one agent once, return its structured dict -------------------------
async def _run(agent, parts):
    runner = InMemoryRunner(agent=agent, app_name="memory")
    sess = await runner.session_service.create_session(app_name="memory", user_id="sascha")
    msg = types.Content(role="user", parts=parts)
    final = None
    async for ev in runner.run_async(user_id="sascha", session_id=sess.id, new_message=msg):
        if ev.is_final_response() and ev.content:
            final = ev.content.parts[0].text
    return json.loads(final)


def run(agent, parts):
    return asyncio.run(_run(agent, parts))


def file_to_part(path):
    p = Path(path)
    mime, _ = mimetypes.guess_type(str(p))
    if mime and (mime.startswith("image/") or mime.startswith("audio/") or mime == "application/pdf"):
        return types.Part(inline_data=types.Blob(mime_type=mime, data=p.read_bytes()))
    return types.Part(text=f"File {p.name}:\n{p.read_text()}")


# --- commands ---------------------------------------------------------------
def cmd_ingest(files):
    con = db()
    for f in files:
        out = run(ingest_agent, [
            types.Part(text=f"Extract memories from this file named {Path(f).name}."),
            file_to_part(f),
        ])
        for m in out["memories"]:
            add_memory(con, "raw", m["content"], source=Path(f).name)
            print(f"  + [{Path(f).name}] {m['content']}")
    print(f"ingested {len(files)} file(s)")


def cmd_consolidate():
    con = db()
    raw = all_memories(con, "raw")
    listing = "\n".join(f"{i}. {c}" for i, k, c, s in raw)
    out = run(consolidate_agent, [types.Part(text="Raw memories:\n" + listing)])
    for ins in out["insights"]:
        add_memory(con, "insight", ins["content"], source_ids=ins["source_ids"])
        print(f"  * insight (from {ins['source_ids']}): {ins['content']}")
    print(f"wrote {len(out['insights'])} insight(s)")


def cmd_query(question):
    con = db()
    mems = all_memories(con)
    listing = "\n".join(f"{i}. [{k}] {c}" for i, k, c, s in mems)
    out = run(query_agent, [types.Part(text=f"Memories:\n{listing}\n\nQuestion: {question}")])
    print(f"\nQ: {question}")
    print(f"A: {out['answer']}")
    print(f"cited memories: {out['cited_ids']}")
    for i, k, c, s in mems:
        if i in out["cited_ids"]:
            print(f"   [{i}] {c}")


def cmd_reset():
    Path(DB).unlink(missing_ok=True)
    db()
    print("store reset")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd == "ingest":
        cmd_ingest(sys.argv[2:])
    elif cmd == "consolidate":
        cmd_consolidate()
    elif cmd == "query":
        cmd_query(" ".join(sys.argv[2:]))
    elif cmd == "reset":
        cmd_reset()
    else:
        print(__doc__)
