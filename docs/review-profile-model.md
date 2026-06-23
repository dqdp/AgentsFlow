# Review Profile Model

## Status

Accepted for v0.2.

## Purpose

Review profiles define how reviewers are composed for a workflow run. They are
separate from reviewer roles:

- a **review profile** says how many reviewers run, whether their prompts are the
  same, and whether focus zones exist;
- a **reviewer role** says what a role name such as `adversarial` means.

Agents must not infer the meaning of heterogeneous reviewer role names from the
name alone. Role ids are references to `profiles/reviewer_roles/*.yaml`.

## The Four Review Profiles

### 1. `homogeneous-dual`

Baseline profile.

Two independent reviewers run with:

- the same substantive review packet content;
- the same substantive prompt content;
- the same rubric;
- the same output schema;
- fresh context and no forked orchestrator conversation.

The reviewer labels are instance ids only, for example `generalist-a` and
`generalist-b`. They do not imply different responsibilities.

This is the default because the baseline gate is an independent replication of
judgment, not a division of labor. If two fresh-context reviewers receive the same
assignment and disagree, the disagreement is meaningful evidence.

### 2. `homogeneous-plus-focused`

Elevated-risk profile.

The workflow keeps the homogeneous baseline pair and adds one or more focused
reviewers. The baseline pair still receives the same packet, prompt and rubric.
Focused reviewers receive explicit focus zones.

Use this when a normal review is still useful, but a declared risk needs extra
attention, such as architecture, product/spec, security, adversarial or domain
risk.

### 3. `heterogeneous-variable`

High or specialized risk profile.

The workflow declares three to eight reviewers, each with explicit roles and
possibly overlapping focus zones. Focus zones are not exclusive. Every reviewer
must still report any plausible P0/P1 blocker even when it is outside the primary
focus zone.

This profile is for deliberate coverage expansion, not for default use.

### 4. `collision-control`

Exception profile, not a primary gate.

Two fresh-context control reviewers run on a focused collision batch only after:

1. a reviewer or fusion report produced a plausible blocker-path candidate finding;
2. the main/orchestrating agent rejected or downgraded it;
3. the rejection reason and supporting evidence were recorded.

The collision batch is per review cycle, not per finding. If three plausible
blocker-path candidate findings are rejected or downgraded in the same cycle,
they are sent to the same two control reviewers in one focused packet. The
packet contains the disputed findings, the orchestrator collision reason
covering the rejection or downgrade, and referenced artifacts.

## Reviewer Role Definitions

Reviewer roles are defined in `profiles/reviewer_roles/`.

Examples:

- `generalist`: common baseline rubric across contract, evidence, scope and
  obvious workflow risks;
- `architecture`: boundaries, ADR consistency, coupling and design drift;
- `verification`: tests, gate evidence, red/green framing and regression coverage;
- `adversarial`: counterexamples, hidden failure modes, bypasses, scope creep and
  false completion;
- `product-spec`: product intent, requirement ambiguity and acceptance criteria;
- `security`: security, privacy and abuse-risk implications;
- `domain`: explicit project/domain constraints supplied by artifacts or humans.

A workflow may use a short role id only because that id resolves to a role
contract. The agent should not invent the role semantics from the word.

## Prompt Policy

Homogeneous review requires:

```yaml
prompt_policy:
  same_prompt: true
  same_packet: true
  same_rubric: true
```

The assembled prompt set is recorded in `review-prompt-contract.yaml`. That
contract records reviewer instances, role contract paths, prompt component
sources, rendered prompt hashes, packet envelope hashes, shared prompt and packet
content hashes, rubric hashes and output schema hashes.

Heterogeneous review requires:

```yaml
prompt_policy:
  focus_prompts_required: true
  focus_zones_may_overlap: true
  all_reviewers_must_report_p0_p1_outside_focus: true
```

## Default

The default v0.2 review profile is `homogeneous-dual`.

Specialization is added in response to explicit risk. It is not the default.
