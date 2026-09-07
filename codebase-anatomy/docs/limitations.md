# Limitations

`codebase-anatomy` is an engineering inventory tool, not a universal source-code parser or architecture-inference system.

## Cross-language code lines are not equivalent mathematical objects

Python currently receives token/AST-aware counting while most other programming languages receive a line-oriented comment-stripped estimate.

Therefore:

- language totals are useful for repository anatomy and rough engineering comparison;
- they should not be presented as parser-exact cross-language productivity measurements;
- a difference of a few lines can be measurement noise rather than meaningful change.

## Approximate scanners do not parse strings

For C-style and similar languages, comment markers embedded in string literals can be mistaken for comments.

Examples include URLs containing `//` or string data containing `/*`.

This is an explicit v0.1 limitation.

## Python fallback weakens precision on malformed source

If Python parsing/tokenization fails, docstring detection may be unavailable and the code-line path may fall back to nonblank-line counting.

A malformed working tree can therefore produce less precise Python numbers than a valid one.

## UTF-8 only

Files that cannot be decoded as UTF-8 are skipped.

The current report does not expose a separate skipped-file inventory. This should be added before the tool is used as a completeness proof for mixed-encoding repositories.

## Recognized suffixes are explicit

Unknown extensions are not guessed from content.

Consequently, a repository using uncommon language/file extensions can be undercounted until its mapping is added.

## Structural roles are heuristics

Built-in roles such as `tests`, `engineering-support`, and `documentation` are based on paths/names/language families.

They are useful defaults but are not semantic truth.

A project that uses unusual layouts should rely on declared semantic groups for important architectural accounting.

## Semantic groups depend on project honesty

The tool cannot prove that a group named `critical` contains every safety-critical file.

It can only report the files matched by the declared patterns.

For audit use, the repository must review its group configuration just as it reviews source code.

## Semantic groups overlap

Overlapping groups are intentional and must not be summed to produce a repository total.

## Git mode counts tracked files, not runtime influence

`git ls-files` improves reproducibility but does not mean every runtime-affecting input is represented.

Ignored/generated/vendor files, external models, local configuration, environment variables, downloaded assets, or host tools may affect a project without appearing in the report.

A release system that needs source-integrity guarantees must audit those inputs separately.

## Dirty trees are reported, not rejected

Unlike a release gate, this snippet does not refuse a dirty working tree.

That is deliberate because interactive development analysis can still be useful. A consumer requiring reproducible baselines must enforce `dirty = false` itself.

## Filesystem mode is less reproducible

Without Git, recursive filesystem discovery can include local files that another checkout does not contain.

Reports expose `source_mode` so consumers can distinguish this case.

## No generated/vendor semantics yet

The default ignores common build/cache directories, but the tool does not yet provide first-class `generated` or `vendored` provenance flags. Projects should declare ignores/groups explicitly until that feature exists.

## No trend database

The snippet produces a point-in-time report only. Historical trends should be implemented by storing JSON outputs externally rather than silently adding persistence to the analyzer.

## No complexity/quality score

Line counts are not quality scores.

The tool does not infer maintainability, architectural quality, test effectiveness, defect density, or development effort from LOC ratios.
