# Limitations

## The runner does not define quality

A green gate means only that the manifest's blocking commands exited successfully. The runner cannot determine whether the selected checks are sufficient for a release.

## Child processes are not sandboxed

Commands run with the user's normal permissions and inherited environment. They may modify files, use the network, delete data, or start further processes. Review a gate manifest with the same care as other executable project automation.

## Seed propagation is advisory

Recording and exporting a seed does not make arbitrary tools deterministic. A child program must actually use that seed or another deterministic configuration.

## Clean Git is a reproducibility boundary, not content proof

`require_clean_worktree = true` verifies a resolvable `HEAD` and empty `git status --porcelain`. It does not prove that dependencies, external services, toolchains, generated caches, submodules, environment variables, system libraries or network responses are identical between runs.

## No timeout policy

Version `0.1.0` does not impose per-step timeouts. A hung child command remains running until it exits or the user interrupts the gate.

## No parallel execution

Steps and repetitions are serial by design. The runner does not attempt dependency graphs or parallel scheduling.

## No shell syntax

Pipes, redirection, glob expansion, command substitution and shell built-ins are not interpreted. If a project intentionally needs shell composition, it must invoke an explicit shell executable as one argv command and accept the portability/security implications itself.

## Placeholder braces

Command/environment strings use `str.format_map`. Literal `{` or `}` characters must be escaped as `{{` and `}}`. This matters for inline programs such as `python -c` snippets containing dictionaries or format strings.

## Partial evidence on interruption

A keyboard interruption preserves metadata and logs already created, but normal `summary.json` / `summary.md` are not guaranteed because control leaves the active run immediately. Consumers must not treat the mere presence of an evidence directory as a completed gate.

## Process trees

On keyboard interruption the runner terminates/kills the direct child process. Descendant process-tree behavior is platform/tool specific and is not yet managed as a portable process group.

## Extraction provenance

Persona Training Lab's source gate had project-specific quick/full profiles, a curated pytest manifest and hard-coded environment variables. Those behaviors are intentionally absent here. The reusable runner expresses repetition and environment composition, while profile selection remains a project-level manifest/composition concern.
