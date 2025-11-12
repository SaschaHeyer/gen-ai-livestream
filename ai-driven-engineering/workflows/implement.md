---
description: "Work through the PLAN one sub-task at a time while syncing progress to Linear"
argument-hint: "(run without arguments)"
---
You are running the `/implement` custom command. Follow this protocol exactly. This workflow is fully autonomous—execute continuously without pausing for human confirmation unless a blocker prevents progress. Stay inside this command loop until every task is complete or you encounter a blocker you explicitly surface.

1. Establish context
   - Ask for the Linear issue key if it is not already known.
   - Before touching git, confirm you are inside the repo that owns the ticket. If the current directory doesn’t contain a `.git` folder, scan upward and across known sibling repos (e.g., via `find .. -maxdepth 4 -name .git`) until you locate the correct root, then `cd` there before continuing.
   - Fetch the current issue description via the Linear MCP.
   - Locate the `## PLAN` section. If it is missing or empty, look for common fallbacks such as `## Tasks`, `## Implementation Plan`, or a `## Bug Brief` with embedded checklists. If a fallback exists, treat it as the plan source without renaming it; otherwise stop and instruct the user to generate it with `/tasks` first.
   - Parse the plan into Relevant Files, Notes, and the checkbox task list.

2. Determine the next sub-task
   - Find the first unchecked sub-task in order. If a parent task has no sub-tasks, treat the parent itself as the actionable item.

3. Execute the sub-task
   - Carry out the implementation instructions for sub-task right away.
   - If critical context is missing, document the assumption you will proceed with, surface it in your status message, and keep moving.
   - Track any files you touch so you can update the Relevant Files list later.
   - Adhere to project conventions from AGENTS.md files in scope.

4. Update Linear immediately after each sub-task
- Mark the completed sub-task checkbox to `[x]` inside the same section you are using for the plan (do not rename existing headers).
- If this completion introduces new work, add fresh sub-tasks beneath the appropriate parent.
- Update the Relevant Files list with one-line explanations for each affected file (create the entry if missing).
- If you created or switched worktrees, add or update a short "Worktrees" note in the plan with the relative paths you are using so the ticket records where the branch lives.
- Use the Linear MCP to write the revised `## PLAN` back to the issue.
- Optionally leave a brief Linear comment summarizing the progress.

1. Parent-task completion protocol
   - After marking a sub-task `[x]`, check whether all sibling sub-tasks under the same parent are now `[x]`.
   - If they are, follow this sequence before checking the parent task:
     1. Run the full test suite appropriate for the repo (e.g., `npm test`, `pytest`, `bin/rails test`).
     2. Stage changes (`git add` for all relevant files).
     3. Remove temporary files or debugging artifacts.
     4. Commit using a multi-`-m` command in conventional commit format, summarizing the parent task and referencing the Linear task/PRD. Example:
        ```bash
        git commit -m "feat: add payment validation logic" -m "- Validates card type and expiry" -m "- Adds unit tests for edge cases" -m "Related to T123 in PRD"
        ```
   - After the commit, update the plan to mark the parent task `[x]` (since all its subtasks are now complete) and push the revised plan to Linear.

2. Repeat until completion
   - Continue the loop (steps 2–6) without exiting the command until every task and sub-task in the plan reads `[x]` or a blocker prevents further progress.
   - When everything is complete, confirm that the Linear issue status should move forward and await further instructions.

Important reminders:
- Git & Worktrees:
  * Always operate from the repository root that contains `.git`; many directories inside `coepi/` are standalone repos, so `cd` into the correct one first.
  * Start new work using `wt new feature/<linear issue> --checkout` (or `wt new bug/<linear issue> --checkout` for fixes) to create both the branch and its worktree. If worktrees aren’t available, fall back to `git checkout -b feature/<linear issue>` from the repo root.
  * Use separate worktrees for agent work. If sibling directories aren’t writable, run `mkdir -p worktrees` inside the repo and create worktrees via `wt new <branch> --checkout --path worktrees/<branch>` or `git worktree add worktrees/<branch> -b <branch>`.
  * Manage worktrees with Git (`git worktree list`, `git worktree remove ../<repo-name>-<branch>`, `git worktree prune`) or the `wt` CLI (`wt list`, `wt remove <branch or path>`, `wt pr <pr-number>`).
  * Commit, push, and create PRs from inside the worktree (`git push -u origin <branch>`, `gh pr create --base development --head <branch>`).
  * Base every feature branch on `development`; PRs should target `development` once the work is approved.
- Keep Linear as the source of truth; do not save separate local task files.
- Always keep the Relevant Files section accurate and up to date.
- Respect all higher-priority instructions (system, developer, AGENTS.md) alongside this workflow.
