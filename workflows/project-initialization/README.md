# project-initialization

Onboarding workflow that prepares a concrete repository to use AgentsFlow.

It creates a project overlay by starting from a project intake/research assignment, collecting raw observable facts, asking the main/orchestrating agent to structure project inventory, running read-only expert assessments, conducting an agent-led operating-decisions interview with the human project owner, drafting workflow bindings and project-bound gates, and validating the overlay before human approval.

The human operating-decisions step is conversational. The agent asks focused questions, summarizes decisions back to the human, and records the normalized result as `project-operating-decisions.yaml`; the human is not asked to manually fill a YAML or JSON file.

This is a lifecycle/onboarding workflow, not a normal development workflow.
