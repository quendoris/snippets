from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from io import StringIO
import json
from pathlib import Path
import re
from tokenize import COMMENT, TokenError, generate_tokens
from typing import Iterable

_SOURCE_MARKERS = (
    (
        "type_ignore",
        re.compile(r"#\s*type:\s*ignore(?:\s*\[[^\]]*\])?"),
    ),
    (
        "mypy_ignore_errors",
        re.compile(r"#\s*mypy:\s*ignore-errors\b", re.IGNORECASE),
    ),
    (
        "mypy_disable_error_code",
        re.compile(
            r"#\s*mypy:\s*disable[-_]error[-_]code\b",
            re.IGNORECASE,
        ),
    ),
)

_CONFIG_MARKERS = (
    (
        "mypy_ignore_errors_config",
        re.compile(r"^\s*ignore_errors\s*=\s*true\s*(?:#.*)?$", re.IGNORECASE),
    ),
    (
        "mypy_disable_error_code_config",
        re.compile(r"^\s*disable_error_code\s*=", re.IGNORECASE),
    ),
)

_CODED_TYPE_IGNORE = re.compile(r"#\s*type:\s*ignore\s*\[[^\]]+\]")
_DEFAULT_CODE_ROOTS = ("src", "tests", "tools")
_DEFAULT_CONFIG_PATHS = (
    "pyproject.toml",
    "mypy.ini",
    ".mypy.ini",
    "setup.cfg",
    "tox.ini",
)


@dataclass(frozen=True, slots=True)
class Finding:
    path: str
    line: int
    kind: str
    text: str


@dataclass(frozen=True, slots=True)
class ClassifiedFinding:
    finding: Finding
    blocking: bool


def _relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as error:
        raise RuntimeError(f"cannot read: {path}") from error
    except UnicodeDecodeError as error:
        raise RuntimeError(f"expected UTF-8 text: {path}") from error


def scan_python_file(path: Path, *, root: Path) -> tuple[Finding, ...]:
    text = _read_text(path)
    findings: list[Finding] = []
    try:
        tokens = generate_tokens(StringIO(text).readline)
        for token in tokens:
            if token.type != COMMENT:
                continue
            for kind, pattern in _SOURCE_MARKERS:
                if pattern.search(token.string) is None:
                    continue
                findings.append(
                    Finding(
                        path=_relative(path, root),
                        line=token.start[0],
                        kind=kind,
                        text=token.string.strip(),
                    )
                )
                break
    except (IndentationError, TokenError) as error:
        raise RuntimeError(f"cannot tokenize Python source: {path}") from error
    return tuple(findings)


def scan_config_file(path: Path, *, root: Path) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    for line_number, line in enumerate(_read_text(path).splitlines(), start=1):
        for kind, pattern in _CONFIG_MARKERS:
            if pattern.search(line) is None:
                continue
            findings.append(
                Finding(
                    path=_relative(path, root),
                    line=line_number,
                    kind=kind,
                    text=line.strip(),
                )
            )
            break
    return tuple(findings)


def scan(
    *,
    root: Path,
    code_roots: Iterable[Path],
    config_paths: Iterable[Path],
) -> tuple[Finding, ...]:
    root = root.resolve()
    findings: list[Finding] = []
    seen: set[Path] = set()

    for code_root in code_roots:
        resolved_root = code_root if code_root.is_absolute() else root / code_root
        if not resolved_root.is_dir():
            continue
        for path in sorted(resolved_root.rglob("*.py")):
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            findings.extend(scan_python_file(path, root=root))

    for config_path in config_paths:
        resolved = config_path if config_path.is_absolute() else root / config_path
        if resolved.is_file():
            findings.extend(scan_config_file(resolved, root=root))

    return tuple(sorted(findings, key=lambda item: (item.path, item.line, item.kind)))


def classify(
    findings: Iterable[Finding],
    *,
    informational_coded_ignore_prefixes: Iterable[str] = (),
) -> tuple[ClassifiedFinding, ...]:
    prefixes = tuple(
        prefix.replace("\\", "/").lstrip("./")
        for prefix in informational_coded_ignore_prefixes
        if prefix
    )
    classified: list[ClassifiedFinding] = []
    for finding in findings:
        normalized = finding.path.replace("\\", "/").lstrip("./")
        informational = (
            finding.kind == "type_ignore"
            and _CODED_TYPE_IGNORE.search(finding.text) is not None
            and any(normalized.startswith(prefix) for prefix in prefixes)
        )
        classified.append(ClassifiedFinding(finding=finding, blocking=not informational))
    return tuple(classified)


def payload(classified: Iterable[ClassifiedFinding]) -> dict[str, object]:
    items = tuple(classified)
    blocking = sum(1 for item in items if item.blocking)
    return {
        "passed": blocking == 0,
        "finding_count": len(items),
        "blocking_finding_count": blocking,
        "informational_finding_count": len(items) - blocking,
        "findings": [
            {**asdict(item.finding), "blocking": item.blocking}
            for item in items
        ],
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Inventory Python typing suppressions and fail on findings that are "
            "not explicitly classified as informational."
        )
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--code-root",
        action="append",
        default=None,
        help="Directory below --root to scan recursively for *.py; repeatable.",
    )
    parser.add_argument(
        "--config",
        action="append",
        default=None,
        help="Mypy-capable config file below --root; repeatable.",
    )
    parser.add_argument(
        "--informational-coded-ignore-prefix",
        action="append",
        default=[],
        help=(
            "Treat coded '# type: ignore[code]' comments below this repository "
            "path prefix as informational instead of blocking; repeatable."
        ),
    )
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    root = args.root.resolve()
    code_roots = tuple(Path(value) for value in (args.code_root or _DEFAULT_CODE_ROOTS))
    config_paths = tuple(Path(value) for value in (args.config or _DEFAULT_CONFIG_PATHS))

    try:
        findings = scan(root=root, code_roots=code_roots, config_paths=config_paths)
    except RuntimeError as error:
        if args.json:
            print(json.dumps({"passed": False, "error": str(error)}, ensure_ascii=False))
        else:
            print(f"typing suppression audit failed: {error}")
        return 2

    classified = classify(
        findings,
        informational_coded_ignore_prefixes=args.informational_coded_ignore_prefix,
    )
    report = payload(classified)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif classified:
        for item in classified:
            finding = item.finding
            severity = "BLOCK" if item.blocking else "INFO"
            print(
                f"{severity} {finding.path}:{finding.line}: "
                f"{finding.kind}: {finding.text}"
            )
    else:
        print("Typing suppression audit passed: no suppressions found.")

    return 1 if report["blocking_finding_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
