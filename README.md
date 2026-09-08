# Engineering Snippets

Small, self-contained engineering utilities and algorithms extracted from real development workflows — documented, testable, reproducible, and reusable.

## What this repository is

A **snippet** in this repository is not merely a short piece of copy-paste code. It is a deliberately bounded engineering unit that solves one well-defined problem and can be understood, tested, and reused independently of the project where it originated.

Examples include:

- application screenshot and visual-audit capture helpers;
- deterministic archive/manifest builders;
- codebase anatomy and line-accounting tools;
- release/audit helpers;
- small parsing, hashing, reporting, validation, or inspection algorithms that proved useful in real development work.

The repository is intentionally named `snippets`, not `tools`. A project-local `tools/` directory may contain scripts that are tightly coupled to one product. This repository contains the **distilled reusable part** after project-specific assumptions have been identified and removed or made explicit.

## Repository contract

Every snippet should satisfy these rules:

1. **One primary responsibility.** A snippet may have several internal modules, but it should answer one coherent engineering need.
2. **Observed behavior over marketing language.** Documentation must describe what the implementation actually guarantees.
3. **Explicit inputs and outputs.** File formats, CLI arguments, environment assumptions, exit codes, generated artifacts, and side effects must be documented.
4. **Methodology is part of the interface.** Analysis/counting tools must explain what they measure, what they exclude, and where the result is approximate.
5. **Failure behavior is documented.** Invalid input, partial output, unsupported platforms, unavailable dependencies, and destructive behavior must be explicit.
6. **Machine-readable output when useful.** Analysis/reporting snippets should normally expose JSON or another stable machine-readable form in addition to human output.
7. **Tests cover critical behavior.** Happy-path examples alone are not sufficient for snippets used in release, integrity, archival, or diagnostic workflows.
8. **Project-specific code is not copied blindly.** Reusable logic is extracted; product composition, UI registries, model names, workspace rules, and other local assumptions stay in the originating project unless deliberately parameterized.
9. **No invented universality.** If behavior is language-, platform-, framework-, or repository-layout-specific, the limitation is part of the specification.
10. **Small does not mean undocumented.** A 40-line algorithm may deserve more explanation than a 400-line CLI if its assumptions are subtle.

## Layout

```text
snippets/
├── README.md
├── CONTRIBUTING.md
├── snippet.schema.json
│
├── <snippet-name>/
│   ├── README.md
│   ├── snippet.toml
│   ├── docs/
│   │   ├── architecture.md
│   │   ├── specification.md
│   │   └── limitations.md
│   ├── src/
│   └── tests/
│
└── ...
```

Not every snippet must use the same programming language or packaging system. The common contract is structural and semantic rather than language-specific.

## `snippet.toml`

Each snippet owns a small manifest describing the reusable unit itself. The manifest is metadata, not a substitute for documentation.

Typical fields include:

```toml
id = "codebase-anatomy"
name = "Codebase Anatomy"
version = "0.1.0"
status = "experimental"
category = "analysis"
language = "python"
entrypoint = "src/codebase_anatomy.py"
network_required = false
platforms = ["linux", "windows", "macos"]
outputs = ["text", "json"]
```

`snippet.schema.json` defines the repository-level manifest contract.

## Documentation inside a snippet

`README.md` answers **what is this and how do I use it?**

The `docs/` subtree answers deeper questions:

- `architecture.md` — decomposition, data flow, boundaries, important implementation choices;
- `specification.md` — exact inputs, outputs, algorithms, invariants, exit behavior, formats;
- `limitations.md` — unsupported cases, approximation boundaries, security/reproducibility caveats.

Additional documents are encouraged when the problem requires them. There is no documentation-size target.

## Current extraction policy

The first source projects for reusable snippets include Persona Training Lab and other Quendoris development work. Extraction follows this order:

```text
real project need
    ↓
working project-local implementation
    ↓
audit project-specific assumptions
    ↓
extract reusable core
    ↓
write independent specification/tests
    ↓
only then consider consuming the snippet from the original project
```

A release-critical project-local tool is **not** removed merely because a generalized version now exists here. Migration happens only after the reusable snippet has its own stable contract and verification.

## Current snippets

### [`codebase-anatomy`](codebase-anatomy/)

Experimental `0.1.0` repository-anatomy analyzer extracted conceptually from Persona Training Lab's `tools/codebase_stats.py`.

It separates:

- automatic facts such as language, physical/nonblank lines, code-line method/value, bytes and structural role;
- explicit project-declared semantic groups such as `core`, `architecture`, `critical`, or `critical-tests`.

Python receives token/AST-aware line accounting. Other supported programming languages currently use a documented comment-stripped estimate rather than pretending to be parser-exact. JSON output exposes per-file evidence and Git metadata when available.

### [`archive-bundler`](archive-bundler/)

Experimental `0.1.0` deterministic artifact packager.

It collects explicit files/directories below a declared base, inventories source bytes with SHA-256, rechecks bytes during archive construction, and publishes a normalized `ZIP_STORED` archive containing generated JSON/Markdown evidence under `_bundle/`.

The current contract deliberately rejects symlinks, strips original timestamps/permissions to normalized archive metadata, and favors deterministic evidence over compression ratio.

### [`app-screenshotter`](app-screenshotter/)

Experimental `0.1.0` PySide6 in-process visual-evidence primitive.

It captures caller-selected Qt widgets or visible top-level widgets through `QWidget.grab()`, publishes PNGs through temporary-file replacement, and records geometry, device-pixel ratio, Qt/platform metadata and PNG SHA-256 in a JSON manifest. It intentionally owns neither application navigation nor redaction and does not pretend to be a generic operating-system screenshot utility.

### [`page-evidence-batcher`](page-evidence-batcher/)

Experimental `0.1.0` page-aligned evidence exporter extracted from the Corpus Motuum editorial workflow.

It selects a contiguous sequence of manifest records, verifies source SHA-256 values, copies each source page together with any number of caller-declared evidence layers, emits a project-neutral JSON manifest, and builds a metadata-normalized deterministic `tar.gz`. Evidence layers are intentionally generic: the snippet knows nothing about OCR engines or which layer, if any, is authoritative.

## Planned snippets

Possible later candidates include reproducible gate orchestration, configurable typing-suppression auditing, and pinned-asset vendoring after their project-specific policy and provenance contracts are separated cleanly.

## Licensing

A repository-wide reuse license has not yet been selected. Until one is added explicitly, do not infer reuse permissions merely from the repository being public.
