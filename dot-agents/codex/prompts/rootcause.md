---
description: "Diagnose cloud incidents by correlating GCP telemetry with repository code"
argument-hint: "(issue key or brief description)"
---
You are running the `/rootcause` custom command. Use this playbook to investigate production issues that span Google Cloud and the current codebase, then feed the findings back to Linear or the user.

1. Confirm the incident scope  
   - If the invocation includes a Linear key, extract it and fetch the ticket via the MCP before asking any questions.  
   - If no key is provided, ask for either the Linear issue or a concise symptom description (metric name, stack trace snippet, failing endpoint, etc.).  
   - Summarize the reported signal (service, environment, time window) and capture any ambiguity that needs clarification.  
   - If critical metadata (project ID, region, product) is missing, ask targeted follow-up questions before moving forward.

2. Anchor in the correct repositories  
   - Ensure you are operating from the repo root that owns the service (verify `.git` is present; traverse ancestors if needed).  
   - Note any AGENTS.md or RUNBOOK.md files; follow higher-priority guidance they contain.  
   - Record the relative path to the repo/worktree in your status notes so Linear reflects where analysis occurred.

3. Gather Google Cloud telemetry  
   - Identify the likely Google Cloud service(s) from the symptom (e.g., Cloud Run, GKE, Cloud Functions, Cloud Logging, Cloud SQL).  
   - Use `gcloud` commands to inspect current state and historical signals—examples:  
     * `gcloud logging read` with a constrained filter and time range.  
     * `gcloud run services describe`, `gcloud compute instances describe`, `gcloud container clusters describe` depending on the stack.  
     * `gcloud monitoring time-series list` or `gcloud monitoring dashboards describe` when metrics are involved.  
   - Retrieve only the relevant slices of logs/metrics (sanitize secrets, avoid dumping entire logs back to the user).  
   - Document each command executed and the key findings it produced.

4. Correlate with application code  
   - Use `rg`, `git grep`, or language-aware tooling to locate the code responsible for the failing component (routes, jobs, infrastructure definitions).  
   - Review recent history (`git log`, `git blame`) around the suspect files to identify regressions or misconfigurations.  
   - Cross-check environment variables, feature flags, and deployment manifests against what the cloud telemetry shows.

5. Form and vet hypotheses  
   - Draft at least one primary hypothesis explaining the incident, supported by evidence from both GCP telemetry and code review.  
   - Note competing or secondary hypotheses if the data is inconclusive.  
   - Call out assumptions explicitly and outline what additional data would confirm or refute them.

6. Recommend a fix  
   - Propose the minimal viable remediation (code change, configuration update, rollback, infrastructure tweak).  
   - Reference specific files (`api/service.js:42`) or cloud resources (`Cloud Run service hello-api in us-central1`).  
   - Include validation steps (tests to run, canary rollout, metric to monitor post-fix).  
   - If the fix requires new workstreams, add them as follow-up tasks in the Linear plan.

7. Sync the analysis  
   - If a Linear issue was provided, insert or update a `## Root Cause Analysis` section in the ticket description containing: summary, evidence (with command references), hypotheses, and recommended fix. Preserve other sections.  
   - Post a Linear comment summarizing key findings and next steps; mention any blockers or approvals required.  
   - If no Linear key exists, deliver the same structured summary directly in your user response.

8. Report completion  
   - Reiterate the confirmed scope, main evidence, and proposed remediation.  
   - Highlight any gaps that still need follow-up (missing metrics, access requirements, upcoming rollouts).  
   - Suggest running `/finalize` or `/document` once the fix is implemented, and `/bug`/`/triage` if the issue transitions into bug-tracking mode.

Stay disciplined about least-privilege access, mask secrets in outputs, and keep Linear as the system of record for the investigation.
