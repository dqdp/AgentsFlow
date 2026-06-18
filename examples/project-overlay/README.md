# Example Project Overlay

This example shows how a project binds AgentsFlow upstream workflow/gate contracts
to project-specific runners and commands.

It uses the canonical v0.2 overlay shape:

- flat `.agentsflow/project.yaml`;
- pinned upstream metadata in `.agentsflow/agentsflow.lock.yaml`;
- structured `.agentsflow/workflows/*.binding.yaml`;
- project-bound gate manifests under `.agentsflow/gates/`;
- deterministic project runners under `.agentsflow/scripts/`.

Validate it from the repository root:

```bash
python3 scripts/validate_project_binding.py --project examples/project-overlay --agentsflow-root .
```

As a repository fixture, binding `extends` references are validated against this
AgentsFlow checkout. A real applied project resolves them through the pinned
`.agentsflow/upstream` dependency recorded in the lock file.
