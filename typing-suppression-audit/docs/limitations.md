# Limitations

## Python and mypy oriented

The scanner is intentionally about Python typing-suppression syntax. It does not understand TypeScript, Kotlin, C++, Rust, pyright-specific configuration, or arbitrary linter suppression comments.

## Not a type checker

A clean audit does not mean the project type-checks. It means only that the configured roots/config files contain none of the suppression forms covered by this contract.

Conversely, a finding is not proof of a bug. It is evidence that a checker rule has been suppressed at that location.

## Config parsing is deliberately shallow

Config files are line-scanned for suppression assignments. The snippet does not parse TOML/INI section semantics, overrides, includes, or environment interpolation. As a result it may report an assignment from a section that is not active for a particular mypy invocation.

This behavior is intentional: the audit inventories explicit suppression text rather than reproducing mypy's configuration resolver.

## Marker coverage is finite

Only documented patterns are recognized. New mypy directives or alternative spellings require an implementation update.

## Prefix policy is lexical

`--informational-coded-ignore-prefix` operates on normalized path prefixes. It does not resolve glob expressions or semantic test ownership. Projects with more complex policy should wrap or extend the classifier explicitly.

## Symlinks and overlapping roots

Resolved Python file paths are deduplicated when multiple scanned roots overlap. The scanner otherwise follows `Path.rglob()` behavior of the host runtime; it does not provide a separate symlink traversal policy.

## UTF-8 requirement

Scanned source/configuration files must decode as UTF-8. Decode failure is an operational error (exit `2`) rather than silently skipping the file.

## Extraction provenance

The original Persona Training Lab implementation hard-coded `src`, `tests`, `tools`, mypy config candidates, and a policy that allowed coded ignores under `tests/`. This snippet keeps those directories as convenience defaults but removes the hard-coded severity exception: test-prefix downgrades now require an explicit CLI argument.
