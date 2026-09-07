# Contributing

This repository collects small engineering units that are intended to remain understandable and reusable outside the project where they first appeared.

## Before adding a snippet

A candidate belongs here when all of the following are true:

- it solves one coherent engineering problem;
- the reusable behavior can be separated from product-specific composition;
- its assumptions can be stated explicitly;
- its output or side effects can be tested;
- keeping it independent is more useful than leaving it as an undocumented project-local script.

A script does **not** belong here merely because it is short.

## Required layout

```text
<snippet-name>/
├── README.md
├── snippet.toml
├── docs/
│   ├── architecture.md
│   ├── specification.md
│   └── limitations.md
├── src/
└── tests/
```

Additional files/directories are allowed when the implementation needs them.

## Naming

- directory and `id`: lowercase kebab-case;
- names describe the engineering task rather than the originating product;
- avoid generic names such as `helper`, `utils`, `misc`, or `tool`;
- prefer names that remain meaningful when read without repository context.

## Manifest

Every snippet must provide `snippet.toml` and conform to `snippet.schema.json` semantically.

The manifest declares identity and operational metadata. Detailed behavior belongs in the documentation.

## Documentation standard

Documentation is part of the implementation contract.

At minimum, document:

- problem and intended use;
- inputs, outputs and side effects;
- algorithm or measurement methodology;
- deterministic/reproducibility properties;
- failure behavior and exit semantics;
- platform/runtime dependencies;
- security/privacy implications when relevant;
- unsupported/approximate cases;
- extraction provenance when the snippet originated in another project.

Do not invent a rationale that is not supported by implementation history or source evidence. It is acceptable to document a behavior without claiming why it was originally chosen.

## Tests

Tests should cover the contract rather than implementation trivia.

For critical snippets, include cases for malformed input, partial failures, path/encoding edge cases, deterministic output, and destructive or security-sensitive behavior as applicable.

## Extraction checklist

When extracting from a real project:

1. identify the smallest reusable behavior;
2. list every product-specific dependency;
3. parameterize or remove those dependencies deliberately;
4. preserve the original algorithm only where its semantics are understood;
5. document behavior that remains approximate or project-shaped;
6. add independent tests;
7. keep the project-local implementation until migration is explicitly justified.

## Compatibility

A snippet is not automatically a stable public API. `status = "experimental"` means its interface may change while the contract is being learned. Promote it to `stable` only after tests and documentation represent the real reusable behavior.

## Licensing

The repository currently has no repository-wide reuse license. Do not add per-snippet license claims that conflict with a future repository-level decision without discussing that decision first.
