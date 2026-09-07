from __future__ import annotations

import argparse
import ast
from collections import defaultdict
from dataclasses import asdict, dataclass
import fnmatch
import json
from pathlib import Path
import subprocess
import sys
import tokenize
import tomllib
from typing import Iterable


LANGUAGE_BY_SUFFIX = {
    ".py": "Python",
    ".rs": "Rust",
    ".c": "C",
    ".h": "C/C++ Header",
    ".cc": "C++",
    ".cpp": "C++",
    ".cxx": "C++",
    ".hpp": "C++ Header",
    ".cs": "C#",
    ".java": "Java",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".swift": "Swift",
    ".go": "Go",
    ".js": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".sh": "Shell",
    ".bash": "Shell",
    ".zsh": "Shell",
    ".ps1": "PowerShell",
    ".rb": "Ruby",
    ".lua": "Lua",
    ".sql": "SQL",
    ".md": "Markdown",
    ".rst": "reStructuredText",
    ".adoc": "AsciiDoc",
    ".toml": "TOML",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".json": "JSON",
    ".jsonl": "JSONL",
    ".ini": "INI",
    ".cfg": "Config",
    ".xml": "XML",
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".qss": "QSS",
    ".scss": "SCSS",
    ".svg": "SVG",
    ".txt": "Text",
}

LANGUAGE_BY_NAME = {
    "Dockerfile": "Dockerfile",
    "Makefile": "Makefile",
    "CMakeLists.txt": "CMake",
}

EXACT_CODE_LANGUAGES = {"Python"}
APPROXIMATE_CODE_LANGUAGES = {
    "Rust",
    "C",
    "C/C++ Header",
    "C++",
    "C++ Header",
    "C#",
    "Java",
    "Kotlin",
    "Swift",
    "Go",
    "JavaScript",
    "TypeScript",
    "Shell",
    "PowerShell",
    "Ruby",
    "Lua",
    "SQL",
}

DOC_LANGUAGES = {"Markdown", "reStructuredText", "AsciiDoc"}
CONFIG_LANGUAGES = {"TOML", "YAML", "JSON", "JSONL", "INI", "Config", "XML"}
ASSET_LANGUAGES = {"SVG"}

C_STYLE_LANGUAGES = {
    "Rust",
    "C",
    "C/C++ Header",
    "C++",
    "C++ Header",
    "C#",
    "Java",
    "Kotlin",
    "Swift",
    "Go",
    "JavaScript",
    "TypeScript",
}

HASH_COMMENT_LANGUAGES = {"Shell", "PowerShell", "Ruby"}
DOUBLE_DASH_COMMENT_LANGUAGES = {"SQL"}
LUA_COMMENT_LANGUAGES = {"Lua"}

DEFAULT_IGNORES = (
    ".git/**",
    ".venv/**",
    "venv/**",
    "node_modules/**",
    "dist/**",
    "build/**",
    "__pycache__/**",
)


@dataclass(slots=True, frozen=True)
class SemanticGroup:
    name: str
    include: tuple[str, ...]
    exclude: tuple[str, ...] = ()
    description: str = ""


@dataclass(slots=True, frozen=True)
class FileStats:
    path: str
    language: str
    role: str
    physical_lines: int
    nonblank_lines: int
    code_lines: int | None
    code_method: str | None
    bytes_count: int
    groups: tuple[str, ...]


def _run_git(root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _git_root(root: Path) -> Path | None:
    completed = _run_git(root, "rev-parse", "--show-toplevel")
    if completed.returncode != 0:
        return None
    try:
        return Path(completed.stdout.decode("utf-8").strip()).resolve()
    except UnicodeDecodeError:
        return None


def _git_text(root: Path, *args: str) -> str | None:
    completed = _run_git(root, *args)
    if completed.returncode != 0:
        return None
    return completed.stdout.decode("utf-8", errors="replace").strip()


def _is_ignored(relative: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatch(relative, pattern) for pattern in patterns)


def _tracked_paths(root: Path, ignores: tuple[str, ...]) -> tuple[Path, ...] | None:
    completed = _run_git(root, "ls-files", "-z")
    if completed.returncode != 0:
        return None
    result: list[Path] = []
    for item in completed.stdout.split(b"\0"):
        if not item:
            continue
        relative = item.decode("utf-8")
        if _is_ignored(relative, ignores):
            continue
        result.append(root / relative)
    return tuple(result)


def _filesystem_paths(root: Path, ignores: tuple[str, ...]) -> tuple[Path, ...]:
    result: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if _is_ignored(relative, ignores):
            continue
        result.append(path)
    return tuple(sorted(result))


def _language(path: Path) -> str | None:
    if path.name in LANGUAGE_BY_NAME:
        return LANGUAGE_BY_NAME[path.name]
    return LANGUAGE_BY_SUFFIX.get(path.suffix.casefold())


def _role(relative: str, language: str) -> str:
    path = Path(relative)
    parts = {part.casefold() for part in path.parts}
    name = path.name.casefold()

    if language in DOC_LANGUAGES or "docs" in parts or "documentation" in parts:
        return "documentation"
    if "tests" in parts or "test" in parts or name.startswith("test_") or name.endswith("_test.py"):
        return "tests"
    if "tools" in parts or "scripts" in parts or ".github" in parts:
        return "engineering-support"
    if language in CONFIG_LANGUAGES or path.name in {"Dockerfile", "Makefile", "CMakeLists.txt"}:
        return "configuration"
    if language in EXACT_CODE_LANGUAGES or language in APPROXIMATE_CODE_LANGUAGES:
        return "production-code"
    if language in ASSET_LANGUAGES or language in {"CSS", "QSS", "SCSS", "HTML"}:
        return "asset-or-presentation"
    return "other-text"


def _docstring_lines(source: str) -> set[int]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()

    result: set[int] = set()

    def collect(body: list[ast.stmt]) -> None:
        if not body:
            return
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            end = getattr(first, "end_lineno", first.lineno)
            result.update(range(first.lineno, end + 1))

    collect(tree.body)
    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            collect(node.body)
    return result


def _python_code_lines(source: str) -> int:
    meaningful: set[int] = set()
    docstrings = _docstring_lines(source)
    ignored = {
        tokenize.ENCODING,
        tokenize.ENDMARKER,
        tokenize.INDENT,
        tokenize.DEDENT,
        tokenize.NEWLINE,
        tokenize.NL,
        tokenize.COMMENT,
    }
    try:
        for token in tokenize.generate_tokens(iter(source.splitlines(keepends=True)).__next__):
            if token.type in ignored:
                continue
            start, end = token.start[0], token.end[0]
            meaningful.update(
                line for line in range(start, end + 1) if line not in docstrings
            )
    except (IndentationError, tokenize.TokenError):
        return sum(1 for line in source.splitlines() if line.strip())
    return len(meaningful)


def _approximate_code_lines(source: str, language: str) -> int:
    """Return a conservative comment-stripped line estimate.

    This intentionally does not parse string literals. It is an engineering-size
    metric, not a language parser or complexity metric.
    """

    in_block_comment = False
    count = 0

    for raw_line in source.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if language in C_STYLE_LANGUAGES:
            remaining = line
            while remaining:
                if in_block_comment:
                    end = remaining.find("*/")
                    if end < 0:
                        remaining = ""
                        break
                    remaining = remaining[end + 2 :].lstrip()
                    in_block_comment = False
                    continue

                block = remaining.find("/*")
                line_comment = remaining.find("//")
                if line_comment >= 0 and (block < 0 or line_comment < block):
                    remaining = remaining[:line_comment].rstrip()
                    break
                if block >= 0:
                    before = remaining[:block].rstrip()
                    end = remaining.find("*/", block + 2)
                    if end < 0:
                        remaining = before
                        in_block_comment = True
                        break
                    remaining = (before + " " + remaining[end + 2 :]).strip()
                    continue
                break
            if remaining.strip():
                count += 1
            continue

        if language in HASH_COMMENT_LANGUAGES:
            if line.startswith("#"):
                continue
            count += 1
            continue

        if language in DOUBLE_DASH_COMMENT_LANGUAGES:
            if in_block_comment:
                end = line.find("*/")
                if end < 0:
                    continue
                line = line[end + 2 :].strip()
                in_block_comment = False
                if not line:
                    continue
            if line.startswith("/*"):
                end = line.find("*/", 2)
                if end < 0:
                    in_block_comment = True
                    continue
                line = line[end + 2 :].strip()
                if not line:
                    continue
            if line.startswith("--"):
                continue
            count += 1
            continue

        if language in LUA_COMMENT_LANGUAGES:
            if line.startswith("--"):
                continue
            count += 1
            continue

        count += 1

    return count


def _semantic_groups(relative: str, groups: tuple[SemanticGroup, ...]) -> tuple[str, ...]:
    matched: list[str] = []
    for group in groups:
        included = any(fnmatch.fnmatch(relative, pattern) for pattern in group.include)
        excluded = any(fnmatch.fnmatch(relative, pattern) for pattern in group.exclude)
        if included and not excluded:
            matched.append(group.name)
    return tuple(matched)


def _load_config(path: Path | None) -> tuple[tuple[str, ...], tuple[SemanticGroup, ...]]:
    if path is None or not path.exists():
        return DEFAULT_IGNORES, ()

    data = tomllib.loads(path.read_text(encoding="utf-8"))
    settings = data.get("settings", {})
    configured_ignores = tuple(str(item) for item in settings.get("ignore", []))

    groups: list[SemanticGroup] = []
    for raw in data.get("group", []):
        name = str(raw.get("name", "")).strip()
        include = tuple(str(item) for item in raw.get("include", []))
        exclude = tuple(str(item) for item in raw.get("exclude", []))
        description = str(raw.get("description", ""))
        if not name:
            raise ValueError("semantic group requires a non-empty name")
        if not include:
            raise ValueError(f"semantic group {name!r} requires at least one include pattern")
        groups.append(
            SemanticGroup(
                name=name,
                include=include,
                exclude=exclude,
                description=description,
            )
        )

    return DEFAULT_IGNORES + configured_ignores, tuple(groups)


def _file_stats(root: Path, path: Path, groups: tuple[SemanticGroup, ...]) -> FileStats | None:
    relative = path.relative_to(root).as_posix()
    language = _language(path)
    if language is None:
        return None

    try:
        raw = path.read_bytes()
        source = raw.decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    physical = source.splitlines()
    if language == "Python":
        code_lines: int | None = _python_code_lines(source)
        method: str | None = "python-tokenize-minus-ast-docstrings"
    elif language in APPROXIMATE_CODE_LANGUAGES:
        code_lines = _approximate_code_lines(source, language)
        method = "comment-stripped-estimate"
    else:
        code_lines = None
        method = None

    return FileStats(
        path=relative,
        language=language,
        role=_role(relative, language),
        physical_lines=len(physical),
        nonblank_lines=sum(1 for line in physical if line.strip()),
        code_lines=code_lines,
        code_method=method,
        bytes_count=len(raw),
        groups=_semantic_groups(relative, groups),
    )


def _totals(files: Iterable[FileStats]) -> dict[str, int]:
    materialized = tuple(files)
    return {
        "files": len(materialized),
        "physical_lines": sum(item.physical_lines for item in materialized),
        "nonblank_lines": sum(item.nonblank_lines for item in materialized),
        "code_lines": sum(item.code_lines or 0 for item in materialized),
        "bytes": sum(item.bytes_count for item in materialized),
    }


def _group_totals(stats: tuple[FileStats, ...], field: str) -> dict[str, dict[str, int]]:
    names: set[str] = set()
    if field == "groups":
        for item in stats:
            names.update(item.groups)
        return {
            name: _totals(item for item in stats if name in item.groups)
            for name in sorted(names)
        }
    values = sorted({str(getattr(item, field)) for item in stats})
    return {
        value: _totals(item for item in stats if str(getattr(item, field)) == value)
        for value in values
    }


def _metadata(root: Path, source_mode: str) -> dict[str, object]:
    branch = _git_text(root, "branch", "--show-current")
    commit = _git_text(root, "rev-parse", "HEAD")
    dirty_raw = _git_text(root, "status", "--porcelain")
    return {
        "root": str(root),
        "source_mode": source_mode,
        "branch": branch or None,
        "commit": commit or None,
        "dirty": bool(dirty_raw) if dirty_raw is not None else None,
    }


def _payload(
    root: Path,
    stats: tuple[FileStats, ...],
    source_mode: str,
    config_path: Path | None,
    groups: tuple[SemanticGroup, ...],
) -> dict[str, object]:
    return {
        "metadata": _metadata(root, source_mode),
        "methodology": {
            "python_code_lines": "tokenize meaningful tokens excluding AST docstring ranges",
            "other_code_lines": "comment-stripped estimate; not a parser or complexity metric",
            "documentation_and_configuration": "code_lines is null; physical/nonblank lines remain available",
            "semantic_groups": "user-declared path groups; groups may overlap",
            "config": str(config_path) if config_path is not None else None,
        },
        "totals": _totals(stats),
        "roles": _group_totals(stats, "role"),
        "languages": _group_totals(stats, "language"),
        "semantic_groups": _group_totals(stats, "groups"),
        "group_definitions": [asdict(group) for group in groups],
        "files": [asdict(item) for item in stats],
    }


def _fmt(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def _print_section(title: str, rows: dict[str, dict[str, int]]) -> None:
    print(f"\n{title}")
    print("-" * 92)
    print(f"{'Name':<30} {'Files':>8} {'Physical':>12} {'Nonblank':>12} {'Code':>12}")
    for name, total in rows.items():
        print(
            f"{name:<30} {_fmt(total['files']):>8} "
            f"{_fmt(total['physical_lines']):>12} "
            f"{_fmt(total['nonblank_lines']):>12} "
            f"{_fmt(total['code_lines']):>12}"
        )


def _print_human(payload: dict[str, object], top: int) -> None:
    metadata = payload["metadata"]
    assert isinstance(metadata, dict)
    totals = payload["totals"]
    assert isinstance(totals, dict)

    print("Codebase Anatomy")
    print("=" * 92)
    print(f"Root        : {metadata.get('root')}")
    print(f"Source mode : {metadata.get('source_mode')}")
    print(f"Branch      : {metadata.get('branch') or 'n/a'}")
    print(f"Commit      : {metadata.get('commit') or 'n/a'}")
    dirty = metadata.get("dirty")
    print(f"Dirty       : {dirty if dirty is not None else 'n/a'}")
    print(
        "Totals      : "
        f"{_fmt(int(totals['files']))} files, "
        f"{_fmt(int(totals['physical_lines']))} physical, "
        f"{_fmt(int(totals['nonblank_lines']))} nonblank, "
        f"{_fmt(int(totals['code_lines']))} measured/estimated code lines"
    )

    roles = payload["roles"]
    languages = payload["languages"]
    semantic_groups = payload["semantic_groups"]
    assert isinstance(roles, dict)
    assert isinstance(languages, dict)
    assert isinstance(semantic_groups, dict)

    _print_section("Structural roles", roles)
    _print_section("Languages", languages)
    if semantic_groups:
        _print_section("Declared semantic groups (overlap allowed)", semantic_groups)

    files = payload["files"]
    assert isinstance(files, list)
    largest = sorted(files, key=lambda item: int(item["physical_lines"]), reverse=True)[:top]
    if largest:
        print(f"\nLargest {len(largest)} recognized text files")
        print("-" * 92)
        for item in largest:
            print(
                f"{_fmt(int(item['physical_lines'])):>10}  "
                f"{str(item['language']):<18}  {item['path']}"
            )

    print("\nMethodology note")
    print("-" * 92)
    print("Python code lines use tokenize/AST-aware counting. Other supported programming")
    print("languages use a documented comment-stripped estimate and are not parser-exact.")
    print("Semantic groups come from repository configuration and may overlap by design.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Report language-aware codebase size plus explicit semantic repository groups."
        )
    )
    parser.add_argument("path", nargs="?", default=".", help="Repository or directory to analyze.")
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to codebase-anatomy TOML config. Defaults to <root>/codebase-anatomy.toml.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--top", type=int, default=20, help="Show N largest recognized text files.")
    args = parser.parse_args(argv)

    requested_root = Path(args.path).expanduser().resolve()
    if not requested_root.exists() or not requested_root.is_dir():
        parser.error(f"analysis path is not a directory: {requested_root}")

    git_root = _git_root(requested_root)
    root = git_root or requested_root

    config_path = args.config.expanduser().resolve() if args.config else root / "codebase-anatomy.toml"
    if not config_path.exists():
        config_path = None

    try:
        ignores, groups = _load_config(config_path)
    except (OSError, tomllib.TOMLDecodeError, ValueError) as exc:
        print(f"configuration error: {exc}", file=sys.stderr)
        return 2

    paths = _tracked_paths(root, ignores) if git_root is not None else None
    if paths is None:
        paths = _filesystem_paths(root, ignores)
        source_mode = "filesystem"
    else:
        source_mode = "git-tracked"

    stats = tuple(
        item
        for path in paths
        if (item := _file_stats(root, path, groups)) is not None
    )

    payload = _payload(root, stats, source_mode, config_path, groups)
    if args.json:
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return 0

    _print_human(payload, max(0, args.top))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
