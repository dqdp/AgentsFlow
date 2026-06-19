# project-initialization

Mode-gated application workflow for understanding a project, onboarding it,
preparing one target workflow, cleaning up legacy agent instructions, or assessing
domain risk.

Every run starts from a project intake/research assignment, collects raw
observable facts, structures project inventory, and runs read-only triad
assessments. `unknown-discovery` and `risk-domain-assessment` may stop there with
questions. `adoption-onboarding`, `prepare-workflow` and legacy activation paths
continue into the human decisions, draft bindings/policy and approval steps that
their intent mode requires.

Each run declares an `intent_mode`. `prepare-workflow` also declares a
`target_workflow`, because preparing a concrete workflow is allowed even when the
project was not previously initialized through the full onboarding path. In v0.2
the only supported `prepare-workflow.target_workflow` is
`big-feature-contract-first`; other workflows remain utility or reference paths.

Expert assessment uses read-only architecture, verification and adversarial role
reports plus a synthesis report. These are candidate assessments for the main
agent and human; they are not authoritative decisions.

Existing-project modes record `project-documentation-disposition.yaml` before
legacy adoption, target-workflow readiness or overlay drafting. This classifies
current project documentation as authoritative, evidence-only,
extract-and-normalize, stale/superseded, needs-human-decision, or
rewrite/delete only after approval. It does not rewrite or delete project docs
during initialization.

The human operating-decisions step is conversational. In `adoption-onboarding`,
the agent asks focused questions, summarizes decisions back to the human, and
records the normalized long-lived result as `project-operating-decisions.yaml`.
In `prepare-workflow`, missing target-workflow gate/review/evidence/authority
context and material target-workflow design forks are captured as a run-level
human decision packet instead of being promoted into project operating policy.
Unresolved blocking-material forks block target workflow readiness unless they
are explicitly deferred with stated constraints.
Target workflow binding/readiness handoff artifacts are drafted after the
readiness gate, not before it.
The human is not asked to manually fill a YAML or JSON file.

Draft overlay artifacts, including `active-instruction-map.yaml`, remain
non-active until human approval. They are produced only by modes that draft or
activate project bindings/policy.

This is a lifecycle/onboarding workflow, not a normal development workflow.
