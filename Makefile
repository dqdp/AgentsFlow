.PHONY: check examples

check: examples

examples:
	python3 scripts/contract_lint.py --contract examples/memory-policy/Docs/contracts/memory-policy.contract.md
	python3 scripts/gherkin_lint.py --contract examples/memory-policy/Docs/contracts/memory-policy.contract.md
	python3 scripts/evidence_validate.py --evidence examples/memory-policy/evidence-report.md
	python3 scripts/boundary_check.py --contract examples/memory-policy/Docs/contracts/memory-policy.contract.md --changed-files examples/memory-policy/changed-files.txt
	python3 scripts/impact_map_check.py --impact-map examples/memory-policy/impact-map.yaml

validate-repo:
	python3 scripts/validate_repo.py --root .


validate-project-initialization-example:
	python3 scripts/validate_project_intake.py --intake examples/project-initialization/project-intake.yaml
	python3 scripts/validate_project_inventory.py --inventory examples/project-initialization/project-inventory.json
