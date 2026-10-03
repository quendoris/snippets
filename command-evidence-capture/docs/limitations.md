# Limitations

- `--keep-shell` deliberately decouples wrapper exit status from child success.
  Consumers must inspect `childExitCode` or `success` in metadata.
- The wrapper does not impose a timeout.
- It terminates/kills only the direct child on keyboard interruption; descendant
  process-tree behavior is platform dependent.
- stdout/stderr ordering across the two independent streams is not reconstructed.
  Each stream preserves its own byte order.
- Existing artifact files with the same prefix are replaced.
- Git metadata is best-effort and does not prove a reproducible environment.
- Child commands are not sandboxed and run with the caller's permissions.
