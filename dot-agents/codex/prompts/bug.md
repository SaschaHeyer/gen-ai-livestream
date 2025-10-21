---
description: "Capture a structured bug brief directly in Linear"
argument-hint: "(run without arguments)"
---
You are running the `/bug` custom command. Follow this flow each time:

1. Gather the issue key  
   - If the user message already contains a Linear link or key, extract it. Otherwise ask for the key explicitly.  
   - Fetch the issue via the Linear MCP immediately so you understand any existing context before asking further questions.

2. Check for an existing bug brief  
   - Look for a `## Bug Brief` section in the issue description.  
   - If one exists and looks complete, show it to the user and ask whether they want to replace or extend it. Only continue if they confirm an update is needed.  
   - If no brief exists or it is clearly incomplete, proceed with questions.

3. Collect the essentials  
   - Ask only for information missing from the ticket. Use concise numbered prompts covering:  
     1. Summary of the bug  
     2. Steps to reproduce (include environment)  
     3. Expected vs. actual behavior  
     4. Impact and severity (who or what is affected)  
     5. Evidence (logs, screenshots, URLs)  
     6. Suspected root cause or recent changes  
     7. Outstanding questions or blockers  
   - Wait for answers. If responses are incomplete, follow up specifically on the missing detail.

4. Compose the bug brief in Markdown  
   - Use the structure:  
     ```markdown
     ## Bug Brief

     **Summary**
     ...

     **Steps to Reproduce**
     1. ...

     **Expected Behavior**
     ...

     **Actual Behavior**
     ...

     **Impact / Severity**
     ...

     **Evidence**
     - ...

     **Suspected Cause**
     ...

     **Open Questions**
     - ...
     ```  
   - Fill every section with the best information available. Use placeholders like “TBD” only when the user agrees that data is unknown.

5. Sync back to Linear  
   - Insert or replace the `## Bug Brief` section in the issue description while preserving other sections.  
   - Optionally add a brief Linear comment noting that the bug brief has been updated.

6. Report completion  
   - Confirm to the user that the bug brief now lives in Linear, reiterate the issue key, and list any sections still marked TBD.  
   - Suggest `/triage` as the next command if deeper investigation is required.

Remember: keep the brief concise but actionable, and avoid re-asking for details that already exist in the ticket.

