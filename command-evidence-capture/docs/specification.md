# Specification

## Runtime

Python 3.11+; standard library only.

## CLI

```text
--output-prefix PATH   required artifact prefix
--cwd PATH             child working directory; default .
--keep-shell           record child failure but return wrapper status 0
-- COMMAND...          exact child argv
```

The wrapper creates parent directories for the output prefix and writes:

- `PREFIX.stdout.log` — exact captured child stdout bytes;
- `PREFIX.stderr.log` — exact captured child stderr bytes;
- `PREFIX.meta.json` — metadata schema `command-evidence-capture-v1`.

The JSON record includes command argv, absolute cwd, UTC start/end timestamps,
duration, child exit code, success/interruption flags, wrapper exit policy,
artifact paths and available Git commit/branch/dirty information.

## Exit behavior

Without `--keep-shell`:

- normal child exit → same exit code;
- keyboard interruption → 130;
- wrapper configuration failure → 2;
- child launch `OSError` → 127.

With `--keep-shell`, a launched/failed child or launch error is still recorded
but the wrapper returns 0. Configuration errors detected before execution remain
wrapper errors.

## Reproducibility

Commands are exact argv arrays and are never shell-parsed. Git metadata helps
identify source state but does not capture environment, dependencies or external
services.
