# Documentation Consistency Review: v0.1.13

## Scope

This review checked the repository documentation against the latest accepted pre-handoff decisions:

- v0.2 MVP workflow boundary;
- project-initialization as mandatory application workflow;
- minimal-python-project as primary e2e example;
- CMake support as documented pattern/skeleton only;
- Claude external reviewer provider included in MVP;
- subscription-local Claude Code CLI only;
- API-key usage forbidden;
- non-MVP workflows reference/experimental only;
- project overlay / project-bound gate model;
- behavior binding and legacy adoption rules.

## Findings resolved in v0.1.13

### README was stale

Previous text still said the repository did not contain real multi-model execution or integration with Claude/Codex-like harnesses. This conflicted with the accepted decision to implement a minimal Claude external reviewer provider in v0.2.

Resolution: README was rewritten around v0.2 MVP scope and the Claude provider requirement.

### Claude provider was described as planned rather than MVP

`docs/external-reviewer-provider-model.md`, ADR-0016 and example text used wording such as "planned provider".

Resolution: these now state that Claude Code CLI is the first MVP external reviewer provider, with strict subscription-local-only constraints.

### Reviewer report output schema was ambiguous

Provider outputs referred to `schemas/reviewer.schema.json`, which is a reviewer manifest schema, not a reviewer report schema.

Resolution: added `schemas/reviewer-report.schema.json` and updated provider configs, packets and docs to use it.

### v0.2 DoD was scattered

MVP boundary decisions existed across discussion/checkpoints but were not centralized.

Resolution: `docs/mvp-ready-workflow-standard.md` now centralizes v0.2 DoD.

### Primary e2e example was not represented

The accepted default `examples/e2e/minimal-python-project/` did not exist.

Resolution: added a minimal illustrative e2e project shape with project overlay, project-bound gate, behavior binding and run artifacts.

### CMake support needed explicit scope limit

CMake support could be overinterpreted as full package support.

Resolution: added `docs/cmake-fetchcontent-application-pattern.md` stating that v0.2 provides only a documented pattern/skeleton.

## Remaining known limits

- The Claude provider wrapper is minimal and not production-hardened.
- The e2e example is illustrative; it is not a full external project fixture with installed upstream submodule.
- Non-MVP workflows remain reference/experimental and may need deeper cleanup after v0.2.
- `validate_repo.py` is still a modest validator, not a full semantic consistency checker.
- Some older checkpoints intentionally preserve historical wording; latest checkpoint and ADRs are authoritative for current decisions.

## Current consistency verdict

The repository is consistent enough for coding-agent handoff under the v0.2 MVP freeze, provided the handoff prompt explicitly instructs agents to:

```text
Do not expand scope.
Use latest checkpoint + ADRs as source of truth.
Treat non-MVP workflows as reference/experimental only.
Implement accepted v0.2 MVP deliverables.
```
