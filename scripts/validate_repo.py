#!/usr/bin/env python3
"""Validate AgentsFlow repository integrity.

This module is intentionally a thin compatibility facade. Domain-specific
validators live under scripts/repo_validation/; tests and external callers may
still import validate_repo.* while the CLI entrypoint remains unchanged.
"""
from __future__ import annotations

from repo_validation.behavior_bindings import *  # noqa: F401,F403
from repo_validation.collect import *  # noqa: F401,F403
from repo_validation.common import *  # noqa: F401,F403
from repo_validation.external_reviewers import *  # noqa: F401,F403
from repo_validation.gates import *  # noqa: F401,F403
from repo_validation.project_initialization import *  # noqa: F401,F403
from repo_validation.project_overlay import *  # noqa: F401,F403
from repo_validation.pr_merge_readiness import *  # noqa: F401,F403
from repo_validation.review import *  # noqa: F401,F403
from repo_validation.runner import main, validate_repository
from repo_validation.workflow_runs import *  # noqa: F401,F403
from repo_validation.workflows import *  # noqa: F401,F403


if __name__ == '__main__':
    raise SystemExit(main())
