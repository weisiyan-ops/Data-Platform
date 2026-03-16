# Project Rules
- Research data abstraction platform, NOT clinical decision support
- Preserve provenance for every extracted or derived field
- Prefer structured sources over narrative NLP
- Unknown values must be null — never default or guess
- Do not infer progression, death, or stage without evidence text
- PFS/OS/local control must be timeline-derived, not single text-span extracted
- All thresholds, endpoint definitions, cancer vocabularies, and mappings must be configurable
- Every code change must include tests
- Schema changes must update: Pydantic models, docs, fixtures, export tests

# Dev Commands
- Install: `pip install -e ".[dev]"`
- Test: `python -m pytest tests/ -v`
- Lint: `ruff check --fix app/ tests/ && ruff format app/ tests/`
- Type check: `mypy app/`

# Architecture
- `app/` layout (not src/)
- Pydantic v2 — use model_validator not root_validator
- Storage backends are Protocols, not ABCs
- ProvenanceRecord is separate from data models (flat values + linked provenance list)
- Cancer configs inherit from _base.yaml via deep merge
- Pipeline steps must be idempotent
- Chinese text: always preserve original in evidence_text
