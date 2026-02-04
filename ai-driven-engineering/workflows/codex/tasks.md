---
description: "Turn a PRD into an implementation checklist and sync it to Linear"
argument-hint: "(run without arguments)"
---
You are running the `/tasks` custom command. Follow this flow every time:

1. Gather inputs  
   - Ask the user for the Linear issue key if it isn’t already known.  
   - Do **not** ask which PRD to use yet—pull the issue details first and inspect them automatically.

2. Inspect the Linear issue  
   - Fetch the issue description via the Linear MCP.  
   - If exactly one `## PDR` section exists, use it automatically and confirm back to the user which PRD you found.  
   - If multiple PRD sections exist, list them and ask the user to choose which one to use.  
   - If no PRD section is present:
     * If the ticket is a bug (e.g., Linear issue type is bug or it already contains a `## Bug Brief`), proceed by treating the bug brief and diagnosis notes as the functional source of truth—call this out to the user but do not force a PRD.  
     * Otherwise tell the user the issue lacks a PRD and ask whether to proceed without one or to generate it now via `/issue`. Only continue without a PRD if the user explicitly confirms.

3. Analyze the PRD and current state  
   - Read the PRD thoroughly: introduction, goals, user stories, functional requirements, non-goals, success metrics, and open questions. If you are operating from a bug brief instead of a PRD, analyze the bug sections (summary, repro steps, scope, hypotheses, evidence) the same way.  
   - Scan the repository (within the current context) to identify existing components, utilities, or patterns relevant to the feature.  
   - Note any reusable code paths or conventions the implementation should respect.

4. Phase 1 – draft parent tasks  
   - Create 4–6 high-level parent tasks that map directly to the PRD goals and functional requirements.  
   - Present them to the user in Markdown without sub-tasks yet and include them verbatim in your reply.  
   - Immediately sync these parent tasks to Linear by inserting or updating a `## PLAN` section with three consistent subheadings: `### Relevant Files`, `### Notes`, and `### Tasks`. Populate `### Tasks` with the parent items and leave the other subsections empty placeholders if needed. Keep any pre-existing plan content that remains accurate.
   - End your message with: "I have generated the high-level tasks based on the PRD. Ready to generate the sub-tasks?"  
   - Pause until the user explicitly confirms (accept "Go", "Yes", "Y", "👍", or similar acknowledgements).

5. Phase 2 – expand with sub-tasks  
   - After the user replies "Go", break each parent task into detailed sub-tasks that a junior developer can execute.  
   - Ensure sub-tasks flow logically, cover edge cases, and reference existing code patterns where helpful.  
   - Identify potential files (new or existing) that need to be created or updated, including corresponding tests.

6. Assemble the final Markdown  
   - Produce the structure exactly as specified:  
     ```markdown
     ## PLAN

     ### Relevant Files

     - `path/to/file` – reason it matters

     ### Notes

     - Important reminders or testing commands

     ### Tasks

     - [ ] 1.0 Parent Task
       - [ ] 1.1 Sub-task
     ```  
   - Include concise Notes that help the developer execute (e.g., testing commands, environment caveats).  
   - Reference the PRD slug in the intro sentence so the linkage is obvious.

7. Sync the plan back to Linear  
   - Once sub-tasks are added, replace the draft `## PLAN` section with the complete plan (parent + sub-tasks, relevant files, notes).  
   - Keep other description content intact.  
   - Optionally add a short Linear comment to note that the implementation plan was finalized.

8. Report completion  
   - In your response to the user, confirm that the plan now lives in Linear and remind them they can trigger implementation next.  
   - Do **not** save anything to disk; Linear is the source of truth.  
   - Only proceed to implementation tasks if explicitly instructed.

Remember: `/tasks` is a two-stage conversation. Always pause after the parent tasks until the user types "Go", and keep Linear as the canonical home for the resulting plan.
