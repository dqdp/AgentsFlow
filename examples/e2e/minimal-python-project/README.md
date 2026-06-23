# Minimal Python Project E2E Example

This example is the primary v0.2 MVP end-to-end shape. It demonstrates how a concrete project would apply AgentsFlow through:

1. project overlay under `.agentsflow/`;
2. project-bound gate manifests;
3. a workflow run under `Docs/agentsflow/runs/`;
4. behavior bindings from acceptance scenario to executable check;
5. gate/evidence/review/fusion artifacts.

This is a tiny illustrative project, not a full product.

The overlay intentionally uses the canonical v0.2 shape: flat
`.agentsflow/project.yaml`, structured workflow binding entries, and a pinned
`.agentsflow/agentsflow.lock.yaml`.

As a repository fixture, binding `extends` references are validated against this
AgentsFlow checkout. A real applied project resolves them through the pinned
`.agentsflow/upstream` dependency recorded in the lock file.
