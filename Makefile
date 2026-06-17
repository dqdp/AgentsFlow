.PHONY: check examples

check: examples

examples:
	python scripts/contract_lint.py --contract examples/memory-policy/Docs/contracts/memory-policy.contract.md
	python scripts/gherkin_lint.py --contract examples/memory-policy/Docs/contracts/memory-policy.contract.md
	python scripts/evidence_validate.py --evidence examples/memory-policy/evidence-report.md
	python scripts/boundary_check.py --contract examples/memory-policy/Docs/contracts/memory-policy.contract.md --changed-files examples/memory-policy/changed-files.txt
	python scripts/impact_map_check.py --impact-map examples/memory-policy/impact-map.yaml

validate-repo:
	python scripts/validate_repo.py --root .


validate-project-initialization-example:
	python scripts/validate_project_intake.py --intake examples/project-initialization/project-intake.yaml
	python scripts/validate_project_inventory.py --inventory examples/project-initialization/project-inventory.json
