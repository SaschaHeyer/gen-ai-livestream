---
description: "Close out implementation branches, handle conflicts, and return PR links"
argument-hint: "(run without arguments)"
---
You are running the `/finalize` custom command. Execute this workflow end to end:

1. Collect context  
   a. Ask for the Linear issue key if it is not known.  
   b. Fetch the issue description via the Linear MCP and read the `## PLAN` section.  
   c. Confirm that every checkbox in the plan is `[x]`. If not, stop and tell the user to finish implementation first.  
   d. Record any "Worktrees" note in the plan; if absent, run `wt list` (or `git worktree list`) and identify entries whose branch name or path contains the issue key. Ask the user for clarification if multiple branches are ambiguous.

2. Prepare each worktree  
   a. For every identified worktree path, change into it.  
   b. Run `git status` to ensure there are no unstaged changes left behind. If there are, include them or ask the user how to proceed.  
   c. Fetch the latest `origin/development` (or the documented base branch) and rebase or merge so the feature branch is up to date. Example: `git fetch origin` followed by `git merge origin/development`.  
   d. If merge conflicts appear, attempt to resolve them yourself by editing the conflicted files and committing the fix. If you cannot resolve automatically, pause and ask the user for guidance.

3. Verify readiness  
   a. Stage any adjustments required by conflict resolution and, if new commits are made, ensure the commit messages follow the existing convention with the Linear issue reference.  
   b. Update the `## PLAN` section in Linear to note that the branch is ready for PR creation and include a short list of the worktree paths used.

4. Create or update pull requests  
   a. For every branch, check whether a GitHub PR already exists using `gh pr list --head <branch>`.  
   b. If a PR exists, open it in edit mode and ensure the base is `development`, the title references the feature, and the Linear issue link is present.  
   c. If no PR exists, run `gh pr create --base development --head <branch> --title "<concise title>" --body "<summary plus Linear issue link>"`.  
   d. Record the resulting PR URL along with the branch name.

5. Surface results back to Linear  
   a. Append a `## PRs` section to the Linear issue description listing each branch and its PR URL.  
   b. Optionally post a Linear comment summarizing that the work has been finalized and linking the PRs.  
   c. If the issue should transition to "In Review", update its status through the MCP.

6. Seek merge approval  
   a. Present the user with the list of PRs, highlight any outstanding checks, and explicitly ask whether to merge.  
   b. Only proceed with merges when the user responds with an affirmative signal ("merge", "yes", "go", etc.). If they decline or add blocking feedback, pause and await instructions.

7. Merge when approved  
   a. For each PR approved by the user, run `gh pr merge <url> --merge --delete-branch=false` (or the project’s preferred merge strategy) once required checks are green.  
   b. If a merge fails, surface the error, resolve conflicts if possible, rerun tests, and retry. If it still fails, halt and ask the user how to proceed.  
   c. After merging, confirm whether the remote branch should be deleted; follow existing repo policy (typically keep the branch until cleanup is confirmed).

8. Report to the user  
   a. Summarize which worktrees were processed, whether conflicts occurred (and how they were resolved), test commands executed, PR URLs, and merge status.  
   b. Note any follow-up actions still needed (manual QA, post-merge verification, status updates) so the user knows the finish line is crossed.

Important notes: do not leave worktrees dirty; ensure Linear remains the single source of truth; and never skip conflict resolution or testing steps before creating PRs.
