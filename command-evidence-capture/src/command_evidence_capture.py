#!/usr/bin/env python3
"""Capture reproducible evidence for one local command.

The child is executed as an exact argv vector (shell=False). stdout and stderr
are streamed live to the corresponding parent streams and copied byte-for-byte
to separate files. A JSON metadata record stores timing, child status and Git
state when available.

--keep-shell is intended for interactive debugging under shells using 'set -e':
the real child status remains in metadata, but the wrapper itself returns 0 so
the shell is not terminated before the evidence can be inspected.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from typing import BinaryIO


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def git_value(cwd: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            text=True,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def git_metadata(cwd: Path) -> dict[str, object]:
    commit = git_value(cwd, "rev-parse", "HEAD")
    branch = git_value(cwd, "branch", "--show-current")
    status = git_value(cwd, "status", "--porcelain")
    return {
        "commit": commit,
        "branch": branch,
        "dirty": bool(status) if status is not None else None,
        "statusPorcelain": (
            status.splitlines()
            if status
            else []
        ),
    }


def pump(
    source: BinaryIO,
    terminal,
    log: BinaryIO,
) -> None:
    terminal_buffer = getattr(terminal, "buffer", None)
    while True:
        chunk = source.read(64 * 1024)
        if not chunk:
            break
        log.write(chunk)
        log.flush()
        if terminal_buffer is not None:
            terminal_buffer.write(chunk)
            terminal_buffer.flush()
        else:
            terminal.write(
                chunk.decode("utf-8", errors="replace")
            )
            terminal.flush()


def run_command(
    command: list[str],
    *,
    cwd: Path,
    output_prefix: Path,
    keep_shell: bool,
) -> int:
    if not command:
        raise ValueError("command must not be empty")

    output_prefix = output_prefix.resolve()
    output_prefix.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    stdout_path = Path(
        str(output_prefix) + ".stdout.log"
    )
    stderr_path = Path(
        str(output_prefix) + ".stderr.log"
    )
    meta_path = Path(
        str(output_prefix) + ".meta.json"
    )

    started_at = utc_now()
    started = time.perf_counter()
    git = git_metadata(cwd)

    child: subprocess.Popen[bytes] | None = None
    interrupted = False
    launch_error: str | None = None
    child_exit: int

    with stdout_path.open("wb") as stdout_log, stderr_path.open("wb") as stderr_log:
        try:
            child = subprocess.Popen(
                command,
                cwd=cwd,
                stdin=None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
                bufsize=0,
            )
            assert child.stdout is not None
            assert child.stderr is not None
            out_thread = threading.Thread(
                target=pump,
                args=(child.stdout, sys.stdout, stdout_log),
                daemon=True,
            )
            err_thread = threading.Thread(
                target=pump,
                args=(child.stderr, sys.stderr, stderr_log),
                daemon=True,
            )
            out_thread.start()
            err_thread.start()
            try:
                child_exit = child.wait()
            except KeyboardInterrupt:
                interrupted = True
                child.terminate()
                try:
                    child_exit = child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child_exit = child.wait()
            out_thread.join()
            err_thread.join()
        except OSError as exc:
            launch_error = f"{type(exc).__name__}: {exc}"
            child_exit = 127
            stderr_log.write(
                (launch_error + "\n").encode(
                    "utf-8",
                    errors="replace",
                )
            )
            stderr_log.flush()
            print(launch_error, file=sys.stderr)

    finished_at = utc_now()
    duration = time.perf_counter() - started
    metadata = {
        "schema": "command-evidence-capture-v1",
        "command": command,
        "cwd": str(cwd),
        "startedAt": started_at,
        "finishedAt": finished_at,
        "durationSeconds": duration,
        "childExitCode": child_exit,
        "success": child_exit == 0 and not interrupted,
        "interrupted": interrupted,
        "launchError": launch_error,
        "keepShell": keep_shell,
        "wrapperExitCode": (
            0
            if keep_shell
            else (130 if interrupted else child_exit)
        ),
        "stdoutLog": str(stdout_path),
        "stderrLog": str(stderr_path),
        "git": git,
    }
    meta_path.write_text(
        json.dumps(
            metadata,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )

    print(
        (
            f"[command-evidence] child_exit={child_exit} "
            f"duration={duration:.3f}s "
            f"stdout={stdout_path} "
            f"stderr={stderr_path} "
            f"meta={meta_path}"
        ),
        file=sys.stderr,
    )

    if keep_shell:
        return 0
    if interrupted:
        return 130
    return child_exit


def parse_args(
    argv: list[str] | None = None,
) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-prefix",
        required=True,
        help=(
            "artifact prefix; writes PREFIX.stdout.log, "
            "PREFIX.stderr.log and PREFIX.meta.json"
        ),
    )
    parser.add_argument(
        "--cwd",
        default=".",
        help="child working directory; default current directory",
    )
    parser.add_argument(
        "--keep-shell",
        action="store_true",
        help=(
            "return wrapper status 0 even when the child fails; "
            "the real status remains in metadata"
        ),
    )
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="exact child argv after --",
    )
    args = parser.parse_args(argv)
    if args.command and args.command[0] == "--":
        args.command = args.command[1:]
    if not args.command:
        parser.error("a command is required after --")
    return args


def main(
    argv: list[str] | None = None,
) -> int:
    args = parse_args(argv)
    cwd = Path(args.cwd).resolve()
    if not cwd.is_dir():
        print(
            f"working directory does not exist: {cwd}",
            file=sys.stderr,
        )
        return 2
    try:
        return run_command(
            list(args.command),
            cwd=cwd,
            output_prefix=Path(args.output_prefix),
            keep_shell=bool(args.keep_shell),
        )
    except (ValueError, OSError) as exc:
        print(
            f"command-evidence configuration error: {exc}",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
