# Design Review Agenda for v0.1

Use this file to guide the next discussion.

## 1. Name and scope

- Is `Agent Workflow Kit` the right working name?
- Is the project too broad?
- Should it be framed as a workflow kit, control plane, or skill pack?

## 2. Abstraction boundaries

- Are workflows, skills, scripts, templates, packs, and profiles separated cleanly?
- Is strictness correctly modeled as metadata rather than a primary object?
- Should review topology be a profile, a workflow parameter, or both?

## 3. Specification-development gap

- Are `new-project-spec-first` and `research-to-ADR` enough?
- Do we need a separate `plan-review-before-implementation` workflow?
- Which plan-mode behaviors should be mandatory?

## 4. BDD scope

- Where should Gherkin be used?
- Where would Gherkin create noise?
- Should `.feature` files be separate, or embedded in `.contract.md`?

## 5. Review + Fusion

- Which reviewer roles are required for v0.1?
- Should fusion be manual/prompt-only first?
- What counts as a blocking issue?

## 6. Scripts

- Which scripts are useful immediately?
- Which are premature?
- Should scripts emit JSON evidence?

## 7. MVP cut

- What should be implemented first in a real repository?
- Which workflows should be validated on the personal assistant project?
- Which workflows should be validated on the HFT/C++ project?
