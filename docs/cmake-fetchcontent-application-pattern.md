# CMake FetchContent / FetchPackage Application Pattern

## Status

Documented pattern / skeleton only for v0.2.

## Decision

AgentsFlow v0.2 supports first-stage project application through:

- Git submodule;
- CMake FetchContent / FetchPackage-style dependency.

CMake support in v0.2 is not a full working package distribution. It is a documented pattern for projects that prefer CMake-managed dependency pinning.

## Intended shape

A CMake-based project may pin AgentsFlow similarly to:

```cmake
include(FetchContent)

FetchContent_Declare(
  AgentsFlow
  GIT_REPOSITORY <agentsflow-repo-url>
  GIT_TAG        <pinned-tag-or-commit>
)

FetchContent_MakeAvailable(AgentsFlow)
```

The project still owns its AgentsFlow overlay:

```text
.agentsflow/
  agentsflow.lock.yaml
  project.yaml
  workflows/*.binding.yaml
  gates/*.yaml
  scripts/*
```

## Non-goals

v0.2 does not provide:

- a complete installable CMake package;
- CPack distribution;
- global CLI installation;
- automatic overlay generation from CMake.

This document exists to keep the dependency mode explicit without expanding the MVP.
