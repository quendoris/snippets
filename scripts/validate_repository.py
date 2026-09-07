from __future__ import annotations

import json
from pathlib import Path
import re
import sys
import tomllib


ROOT = Path(__file__).resolve().parents[1]
SEMVER = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-[0-9A-Za-z.-]+)?$")
ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
STATUSES = {"experimental", "stable", "deprecated"}
PLATFORMS = {"linux", "windows", "macos"}
REQUIRED_FIELDS = (
    "id",
    "name",
    "version",
    "status",
    "category",
    "language",
    "entrypoint",
    "network_required",
    "platforms",
    "outputs",
)
REQUIRED_DOCS = (
    "README.md",
    "docs/architecture.md",
    "docs/specification.md",
    "docs/limitations.md",
)


def _error(errors: list[str], path: Path, message: str) -> None:
    try:
        shown = path.relative_to(ROOT).as_posix()
    except ValueError:
        shown = str(path)
    errors.append(f"{shown}: {message}")


def _validate_string_list(
    errors: list[str],
    manifest_path: Path,
    manifest: dict[str, object],
    field: str,
    *,
    allowed: set[str] | None = None,
    nonempty: bool = True,
) -> None:
    value = manifest.get(field)
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        _error(errors, manifest_path, f"{field} must be an array of non-empty strings")
        return
    if nonempty and not value:
        _error(errors, manifest_path, f"{field} must not be empty")
    if len(value) != len(set(value)):
        _error(errors, manifest_path, f"{field} must not contain duplicates")
    if allowed is not None:
        unexpected = sorted(set(value) - allowed)
        if unexpected:
            _error(errors, manifest_path, f"{field} contains unsupported values: {unexpected}")


def validate_snippet(directory: Path) -> tuple[str | None, list[str]]:
    errors: list[str] = []
    manifest_path = directory / "snippet.toml"
    try:
        manifest = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        _error(errors, manifest_path, f"cannot parse manifest: {exc}")
        return None, errors

    if not isinstance(manifest, dict):
        _error(errors, manifest_path, "manifest root must be a TOML table")
        return None, errors

    missing = [field for field in REQUIRED_FIELDS if field not in manifest]
    if missing:
        _error(errors, manifest_path, f"missing required fields: {missing}")

    known = set(REQUIRED_FIELDS) | {"requires"}
    unexpected_fields = sorted(set(manifest) - known)
    if unexpected_fields:
        _error(errors, manifest_path, f"unknown fields not covered by repository contract: {unexpected_fields}")

    snippet_id = manifest.get("id")
    if not isinstance(snippet_id, str) or ID_PATTERN.fullmatch(snippet_id) is None:
        _error(errors, manifest_path, "id must be lowercase kebab-case")
        normalized_id: str | None = None
    else:
        normalized_id = snippet_id
        if snippet_id != directory.name:
            _error(errors, manifest_path, f"id {snippet_id!r} must match directory name {directory.name!r}")

    for field in ("name", "category", "language", "entrypoint"):
        value = manifest.get(field)
        if not isinstance(value, str) or not value.strip():
            _error(errors, manifest_path, f"{field} must be a non-empty string")

    version = manifest.get("version")
    if not isinstance(version, str) or SEMVER.fullmatch(version) is None:
        _error(errors, manifest_path, "version must use the repository SemVer-like format")

    status = manifest.get("status")
    if status not in STATUSES:
        _error(errors, manifest_path, f"status must be one of {sorted(STATUSES)}")

    if not isinstance(manifest.get("network_required"), bool):
        _error(errors, manifest_path, "network_required must be boolean")

    _validate_string_list(errors, manifest_path, manifest, "platforms", allowed=PLATFORMS)
    _validate_string_list(errors, manifest_path, manifest, "outputs")
    if "requires" in manifest:
        _validate_string_list(errors, manifest_path, manifest, "requires", nonempty=False)

    entrypoint = manifest.get("entrypoint")
    if isinstance(entrypoint, str) and entrypoint.strip():
        entrypoint_path = directory / entrypoint
        if not entrypoint_path.is_file():
            _error(errors, manifest_path, f"entrypoint does not exist: {entrypoint}")

    for relative in REQUIRED_DOCS:
        path = directory / relative
        if not path.is_file():
            _error(errors, directory, f"required documentation file is missing: {relative}")
        elif not path.read_text(encoding="utf-8").strip():
            _error(errors, path, "required documentation file is empty")

    tests = directory / "tests"
    if not tests.is_dir():
        _error(errors, directory, "tests/ directory is missing")
    elif not any(path.is_file() for path in tests.rglob("*")):
        _error(errors, tests, "tests/ directory is empty")

    src = directory / "src"
    if not src.is_dir():
        _error(errors, directory, "src/ directory is missing")

    return normalized_id, errors


def main() -> int:
    errors: list[str] = []

    schema_path = ROOT / "snippet.schema.json"
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _error(errors, schema_path, f"cannot parse repository schema: {exc}")
        schema = None
    if isinstance(schema, dict) and schema.get("title") != "Engineering Snippet Manifest":
        _error(errors, schema_path, "unexpected schema title")

    snippet_dirs = tuple(
        sorted(
            path
            for path in ROOT.iterdir()
            if path.is_dir() and (path / "snippet.toml").is_file()
        )
    )
    if not snippet_dirs:
        _error(errors, ROOT, "repository contains no snippet.toml manifests")

    seen_ids: dict[str, Path] = {}
    for directory in snippet_dirs:
        snippet_id, snippet_errors = validate_snippet(directory)
        errors.extend(snippet_errors)
        if snippet_id is not None:
            previous = seen_ids.get(snippet_id)
            if previous is not None:
                _error(errors, directory / "snippet.toml", f"duplicate snippet id also used by {previous.name}")
            else:
                seen_ids[snippet_id] = directory

    readme_path = ROOT / "README.md"
    try:
        readme = readme_path.read_text(encoding="utf-8")
    except OSError as exc:
        _error(errors, readme_path, f"cannot read root README: {exc}")
        readme = ""
    for snippet_id in sorted(seen_ids):
        if f"]({snippet_id}/)" not in readme:
            _error(errors, readme_path, f"current snippet is not linked from root README: {snippet_id}")

    if errors:
        print("Snippet repository validation: FAIL", file=sys.stderr)
        for item in errors:
            print(f"- {item}", file=sys.stderr)
        return 1

    print("Snippet repository validation: PASS")
    print(f"Snippets: {len(seen_ids)}")
    for snippet_id in sorted(seen_ids):
        print(f"- {snippet_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
