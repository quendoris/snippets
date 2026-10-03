# Architecture

The snippet owns one child process and three evidence artifacts.

1. The child is started with `subprocess.Popen(..., shell=False)`.
2. Two pump threads read raw stdout/stderr bytes independently.
3. Each pump writes the same bytes to its log and to the corresponding parent
   terminal stream.
4. The main thread waits for the child and handles keyboard interruption.
5. After the streams close, one JSON metadata file is written.

The logs intentionally contain only child output. Wrapper summaries go to the
parent stderr but are not appended to the child's stderr log.

Git metadata is observational. Failure to invoke Git does not prevent command
execution.

## Extraction provenance

This was extracted from repeated local solver/benchmark runs where stdout was
machine-readable JSON and failures appeared only on stderr. Shell process
substitution plus `set -e` made it too easy to lose a traceback when an
interactive terminal closed. The reusable unit is the capture policy, not any
Puzzle-specific command.
