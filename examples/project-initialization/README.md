# Example: project initialization

This example shows an explicit `adoption-onboarding` run before a project overlay
is approved.

The files intentionally separate raw observable facts from model-produced inventory, domain identification, expert assessment, agent-led human operating decisions, and human-confirmation questions.

Unknown-project discovery still uses a standard exploratory research assignment;
it is not an empty prompt, and it may stop after scan, inventory, assessments and
questions. This example continues beyond discovery into onboarding, so it includes
operating decisions and approval-boundary artifacts.

`project-assessment.architecture.json`, `project-assessment.verification.json`
and `project-assessment.adversarial.json` are read-only candidate assessment
reports. They must be schema-valid strict JSON before synthesis. Markdown or
prose-only assessment output is invalid workflow evidence and must be rejected,
rerun or paused rather than normalized as authoritative. `project-assessment.json`
is the synthesis artifact; it records role-report validation and does not make
the role reports authoritative.

`project-documentation-disposition.yaml` records how current project
documentation should be treated before overlay drafting or target-workflow
preparation: authoritative, evidence-only, extracted/normalized,
stale/superseded, unresolved, or rewrite/delete only after explicit approval.

`project-operating-decisions.yaml` represents the normalized result of a dialogue
with the project owner. It is not a blank form the human is expected to fill by
hand.

`human-questions.yaml` and `human-decisions.yaml` show the run-level pause/resume
artifacts used by the main agent when a workflow phase waits for human input.
