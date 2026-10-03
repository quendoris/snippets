# Command Evidence Capture

A tiny wrapper for long-running local commands where the console should not be
the only copy of a traceback or benchmark result.

It executes one exact argv command, streams the child's stdout/stderr live, saves
those streams separately, and records timing, exit status and available Git
metadata in JSON.

## Example

```bash
python command-evidence-capture/src/command_evidence_capture.py \
  --output-prefix recursive-front-local/million-smoke/11-factor5-portal \
  --keep-shell \
  -- python3 -u tools/recursive_factor5_portal_gate.py
```

Artifacts:

```text
11-factor5-portal.stdout.log
11-factor5-portal.stderr.log
11-factor5-portal.meta.json
```

Use `--keep-shell` for interactive debugging under `set -e`: a failing child
is still recorded with its real exit code in metadata, while the wrapper returns
0 so the parent shell stays open. Omit it in automation when the wrapper should
propagate the child status.

The wrapper uses `shell=False`; pipes/redirections belong outside the command
or should be expressed by explicitly invoking a shell.

See `docs/specification.md`, `docs/architecture.md`, and
`docs/limitations.md`.
