# project-operating-decisions-interview

Use this skill during `project-initialization` after the project inventory and
candidate assessment exist, and before drafting the project overlay.

## Purpose

Run an agent-led dialogue with the human project owner to decide how AgentsFlow
should operate in this concrete project.

This is not a form-filling step. The human should not be asked to manually
populate YAML or JSON. The main/orchestrating agent conducts the conversation,
summarizes decisions back to the human, and then records the normalized result in
`project-operating-decisions.yaml`.

## Inputs

- `project-intake.yaml`
- `project-raw-scan.json`
- `project-inventory.json`
- `project-assessment.json`
- legacy adoption outputs when present
- candidate gate and workflow recommendations
- current human answers from the dialogue

## Output

- `project-operating-decisions.yaml`

The output is a human-owned decision artifact. It may be draft, confirmed, or
blocked on unresolved questions. It is used to draft `.agentsflow/project.yaml`,
workflow bindings, project-bound gate manifests, review policy and profile
defaults.

## Conversation Rules

- Do not hand the user an empty file and ask them to fill it.
- Ask questions in small groups. Prefer 3 to 7 questions per exchange.
- Start from project evidence and candidate recommendations, not from an abstract
  checklist.
- Offer a conservative default when the repository evidence supports one, and
  make the default explicit.
- Distinguish a confirmed human decision from an agent recommendation.
- Record unanswered questions instead of inventing missing policy.
- Re-ask only when the answer affects gates, review topology, authority, legacy
  migration, sensitive data handling or project risk.
- If the user is unsure, record the decision as `needs-human-decision` or
  `defaulted-with-review-needed`.
- Do not change project files, `AGENTS.md`, gate runners or workflow bindings
  during the interview.
- Do not activate migration or rewrite legacy instructions without explicit human
  approval.

## Dialogue Shape

Use this sequence unless the project context requires a narrower path.

1. Restate what was observed.

   Summarize the project type, known workflows, existing tests/build tools,
   domain assumptions, legacy agent/process artifacts and open risks in a short
   evidence-grounded paragraph.

2. Confirm project intent and risk.

   Ask what the project owner wants AgentsFlow to optimize for: lightweight
   feature work, strict review discipline, legacy process cleanup, external
   review, domain-risk control, or specification-first planning.

3. Decide verification gate policy.

   Ask which checks must block acceptance, which are advisory, and which command
   or project runner is authoritative for each check. Cover tests, lint,
   typecheck, security, performance, domain-specific checks, red/green evidence
   and required evidence logs.

4. Decide review policy.

   Confirm the review profile. The default is `homogeneous-dual`: two independent
   generalist reviewers with the same prompt, packet, rubric and output schema.
   Ask whether any explicit risk requires `homogeneous-plus-focused` or
   `heterogeneous-variable` review. For heterogeneous review, record the reviewer
   role definitions and overlapping focus zones; do not leave role meanings for
   the agent to infer from names such as `adversarial`. Record that reviewers
   start from fresh zero context without forking the orchestrator conversation.
   Record the single-reviewer exception only as `collision-control` for a rejected
   blocker collision.

5. Decide review-cycle limits.

   Ask the maximum number of review cycles, when review should be rerun, when a
   finding requires human decision, and what counts as progress stall.

6. Decide authority boundaries.

   Ask who may approve scope changes, accept known risk, change gates, change
   review topology, approve legacy migration, or override a blocking gate.

7. Decide artifact and evidence policy.

   Ask where run artifacts live, whether reports are committed, whether raw logs
   are stored, what must be redacted, and whether sensitive evidence can be sent
   to external reviewers.

8. Summarize and confirm.

   Present the normalized decisions in plain language. Ask the human to confirm,
   correct, or mark unresolved items. Only then write the structured artifact.

## Standard Question Set

Use these as defaults, adapting wording to the observed project.

- What is the default AgentsFlow workflow for normal feature work in this project?
- What strictness profile should be the default for low-risk, normal and high-risk
  changes?
- Which verification checks are mandatory blockers?
- What is the canonical command or project runner for tests?
- Are lint, typecheck, security scan, performance checks or domain-specific checks
  mandatory, advisory or not applicable?
- Should implementation workflows require red-before/green-after evidence?
- Is the default `homogeneous-dual` review profile acceptable for normal work?
- Which explicit risks require focused or heterogeneous reviewers?
- For heterogeneous review, which reviewer roles and focus zones are required?
- Confirm that reviewers start from fresh zero context and do not receive forked
  orchestrator conversation context.
- Should a single control reviewer be used when the main agent rejects a
  blocker-level candidate finding and records a collision?
- Should review use different models or harnesses when available?
- Is an external Claude Code reviewer allowed for this project?
- Are external reviewers allowed to see raw logs, full repo context or only review
  packets?
- What is the maximum number of review cycles before escalation?
- When should a review be rerun?
- When should candidate findings return to the human instead of being accepted or
  rejected by the main agent?
- Who can approve scope changes, gate policy changes or review topology changes?
- Who can accept residual risk after a failed or inconclusive gate?
- Where should AgentsFlow run artifacts and evidence be stored?
- Should reports be committed to the repository?
- Should raw logs be committed, gitignored, redacted or not stored?
- Are there sensitive data, privacy, compliance or domain constraints that affect
  review packets or evidence storage?

## Quality Bar

- The final artifact is structured, but the human interaction was conversational.
- Every policy decision is marked as confirmed, defaulted, recommended or
  unresolved.
- Verification gate decisions identify mandatory blockers and evidence
  requirements.
- Review policy decisions identify reviewer count, roles, model diversity,
  external reviewer allowance and read-only/default permissions.
- Review-cycle policy identifies a maximum cycle count and escalation conditions.
- Authority decisions identify who can approve high-impact changes or risk
  acceptance.
- Artifact policy identifies run/evidence storage and redaction rules.
- Unresolved decisions are visible and must not silently become defaults.

## Anti-patterns

- Asking the user to fill a YAML file manually.
- Treating model recommendations as human approval.
- Drafting executable gates before the human decides which checks are mandatory.
- Letting reviewer count, model diversity or cycle limits remain implicit.
- Hiding unanswered questions by choosing optimistic defaults.
