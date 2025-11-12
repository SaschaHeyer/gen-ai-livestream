---
description: "Turn a brain dump into a PRD and sync it back to Linear"
argument-hint: "(run without arguments)"
---
You are running the `/issue` custom command. Follow this flow every time:

1. Confirm scope  
   - If the user message already contains a Linear issue link or key, extract it automatically. Otherwise ask for the key.  
   - Fetch the issue immediately via the Linear MCP so you know what context already exists before asking for anything else.  
   - Only request a short feature name or extra summary if it is missing from both the user’s message and the current issue description.  
   - If you already have enough context, generate a concise working title yourself (e.g., trim the existing Linear issue title or condense the user’s brief) and skip the follow-up question entirely. Ask for a title only when the available information is obviously generic or conflicting.
   - Summarize the raw idea you’ve been given (including any notes you found in the issue) and call out ambiguities that still need clarification.  
   - **Do not** proceed until you have the issue key, a working feature name (from the user or the ticket), and enough context to understand the request.

2. Inspect existing issue data  
   - Use the Linear MCP to fetch the issue description.  
   - If a `## PDR` section already exists and contains a complete PRD, show it to the user and confirm whether they want to replace it or keep it.  
   - If no usable PRD exists (missing section, placeholder content, or user requests an update), continue with the clarifying-question loop.

3. Enforce the PRD clarifying-question loop  
   - Even if the initial brief feels rich, you *must* ask clarifying questions before drafting anything.  
   - Format questions as numbered or lettered options so the user can respond quickly.  
   - Cover these areas (adapt as needed):  
     1. Problem/goal the feature solves  
     2. Target user  
     3. Core functionality / key user actions  
     4. Acceptance criteria or success metrics  
     5. Scope boundaries / non-goals  
     6. Data requirements  
     7. Design or UI expectations  
     8. Edge cases or error conditions  
   - Wait for answers, confirm understanding, and loop back with follow-up questions if anything is still fuzzy.

4. Generate the PRD in Markdown using this structure:  
   - Introduction/Overview  
   - Goals  
   - User Stories  
   - Functional Requirements (numbered list)  
   - Non-Goals  
   - Design Considerations (if applicable)  
   - Technical Considerations (if applicable)  
   - Success Metrics  
   - Open Questions  
   The tone should be explicit and junior-developer friendly. Incorporate every clarification the user provided.

5. Sync the PRD back to Linear via the MCP integration  
   - Fetch the current description of the Linear issue.  
   - Insert (or replace) a `## PDR` section containing the PRD you just generated. Keep other description content intact.  
   - Update the issue description with the new `## PDR` section.  
   - Optionally add a short issue comment noting that the PRD was created and attached.

6. Report completion  
   - In your response to the user, confirm the Linear issue you updated and note that the PRD now lives there.  
   - Do not begin implementation work. Offer next steps only if asked.

Remember: this command exists to save the user from writing PRDs manually. Stay proactive about missing details, respect the clarifying-question loop, and ensure Linear remains the single source of truth once you’re done.
