# PHASES

## Phase 0 — Scaffold
- [x] `uv init --lib`, Python 3.12, `uv_build`, ruff `ALL`, pytest, branch coverage config
- [x] CLAUDE.md, PHASES.md, README.md, LICENSE
- [x] PyPI name searched: no `pyprojection` found, but `pyprojections` exists (confirm before publishing)

## Phase 1 — Design (written only)
- [x] `docs/DESIGN.md`: `Projection`, `&`, registry, `computed`, JSON shape, export recipes (CSV, `?fields=`)
- [x] Author confirms a screen lets users choose columns (gate for Phase 2): "build it", 2026-11-08

## Phase 2 — Core
- [x] `Projection`, `&`, `ProjectionRegistry` on `pyvocabulary.Vocabulary`, `computed`

## Phase 3 — Compiler, schema and release
- [x] `ProjectionCompiler` with JSON-path errors; JSON Schema
- [ ] GitHub repository, CI, PyPI
