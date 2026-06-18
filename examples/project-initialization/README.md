# Example: project initialization

This example shows the artifacts created before a project overlay is approved.

The files intentionally separate raw observable facts from model-produced inventory, domain identification, expert assessment, agent-led human operating decisions, and human-confirmation questions.

Unknown-project discovery still uses a standard exploratory research assignment; it is not an empty prompt.

`project-operating-decisions.yaml` represents the normalized result of a dialogue
with the project owner. It is not a blank form the human is expected to fill by
hand.

`human-questions.yaml` and `human-decisions.yaml` show the run-level pause/resume
artifacts used by the main agent when a workflow phase waits for human input.
