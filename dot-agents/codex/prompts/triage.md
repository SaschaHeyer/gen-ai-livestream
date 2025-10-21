---
description: "Summarize current findings and next steps for an open bug"
argument-hint: "(run without arguments)"
---
  You are running the `/triage` custom command. Execute this process:

  1. Identify the ticket
     - Extract the Linear issue key from the user message if present; otherwise ask for it.
     - Fetch the issue via the Linear MCP so you have the latest description, bug brief,
  status, and comments before asking questions.
     - If the user supplied extra context (logs, repro steps, screenshots) in this invocation,
  capture it alongside the fetched data before deciding what to ask next.

  2. Review existing context
     - Ensure a `## Bug Brief` section exists. If it is missing, instruct the user to run `/
  bug` first.
     - Scan for an existing `## Diagnosis` section. If one exists, confirm with the user
  whether this run should replace it or append updates.

  3. Collect triage data
     - Start by reusing everything already stored in the Linear issue. Treat the fetched bug brief, prior diagnosis sections, and recent comments as your primary inputs.
     - Only ask the user for information that is clearly missing, outdated, or contradictory. When you must ask, combine up to three targeted questions in a single numbered list that calls out the specific gaps (e.g., "1.") instead of re-interviewing the entire brief.
     - If the Linear ticket already contains enough data for a section, acknowledge it and move on without quizzing the user again.

  4. Draft the diagnosis in Markdown
     - Structure the update as:
       ```markdown
       ## Diagnosis

       **Observations**
       - ...

       **Scope**
       - ...

       **Hypotheses**
       - ...

       **Evidence Collected**
       - ...

       **Blockers / Risks**
       - ...

       **Next Actions**
       - ...
       ```
     - Summaries should be bullet-based and actionable. Note “None” explicitly when a section
  has no content.

  5. Sync back to Linear
     - Insert or replace the `## Diagnosis` section in the issue description while keeping
  other sections intact.
     - Optionally post a Linear comment summarizing new findings and pointing to the updated
  diagnosis.
     - Update the issue status to the appropriate triage state if your workflow requires it
  (e.g., “In Progress” or “Triage”).

  6. Report outcomes
     - Confirm to the user that the diagnosis has been stored in Linear, reiterate key
  observations, and call out any blockers.
     - Suggest creating or refreshing the implementation plan with `/tasks` if the path
  forward is clear.

  Keep updates concise, reuse existing ticket context whenever possible, and capture enough
  detail for another engineer to continue the investigation without repeating your work.
