from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import zipfile


RESERVED_PREFIX = "_bundle/"
FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)
GENERATOR = "archive-bundler/0.1.0"


class BundleError(RuntimeError):
    pass


@dataclass(slots=True, frozen=True)
class FileRecord:
    path: str
    size: int
    sha256: str


def _is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


def _matches_any(relative: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatch(relative, pattern) for pattern in patterns)


def _source_path(base: Path, source: Path) -> Path:
    expanded = source.expanduser()
    candidate = expanded if expanded.is_absolute() else base / expanded
    if candidate.is_symlink():
        raise BundleError(f"symlink sources are not supported: {source}")
    return candidate.resolve()


def _collect_files(
    *,
    base: Path,
    sources: tuple[Path, ...],
    excludes: tuple[str, ...],
    output: Path,
) -> tuple[Path, ...]:
    selected: dict[str, Path] = {}

    for source in sources:
        resolved = _source_path(base, source)
        if not _is_relative_to(resolved, base):
            raise BundleError(f"source is outside --base: {source}")
        if not resolved.exists():
            raise BundleError(f"source does not exist: {source}")

        candidates = (resolved,) if resolved.is_file() else tuple(sorted(resolved.rglob("*")))
        for path in candidates:
            if path.is_symlink():
                raise BundleError(f"symlink entries are not supported: {path}")
            if not path.is_file():
                continue
            if path.resolve() == output.resolve():
                continue

            relative = path.relative_to(base).as_posix()
            if relative.startswith(RESERVED_PREFIX):
                raise BundleError(
                    f"source path uses reserved archive prefix {RESERVED_PREFIX!r}: {relative}"
                )
            if _matches_any(relative, excludes):
                continue
            selected[relative] = path

    return tuple(selected[key] for key in sorted(selected))


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _inventory(base: Path, files: tuple[Path, ...]) -> tuple[FileRecord, ...]:
    records: list[FileRecord] = []
    for path in files:
        data = path.read_bytes()
        records.append(
            FileRecord(
                path=path.relative_to(base).as_posix(),
                size=len(data),
                sha256=_sha256_bytes(data),
            )
        )
    return tuple(records)


def _manifest(
    records: tuple[FileRecord, ...],
    metadata: dict[str, str],
) -> dict[str, object]:
    return {
        "schema": 1,
        "generator": GENERATOR,
        "metadata": dict(sorted(metadata.items())),
        "totals": {
            "files": len(records),
            "bytes": sum(record.size for record in records),
        },
        "files": [asdict(record) for record in records],
    }


def _manifest_bytes(payload: dict[str, object]) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")


def _summary_bytes(records: tuple[FileRecord, ...], metadata: dict[str, str]) -> bytes:
    lines = [
        "# Artifact bundle",
        "",
        f"Generator: `{GENERATOR}`",
        f"Files: **{len(records)}**",
        f"Bytes: **{sum(record.size for record in records)}**",
    ]
    if metadata:
        lines.extend(("", "## Metadata", ""))
        for key, value in sorted(metadata.items()):
            lines.append(f"- `{key}`: `{value}`")

    lines.extend(("", "## Files", "", "| Path | Bytes | SHA-256 |", "|---|---:|---|"))
    for record in records:
        lines.append(f"| `{record.path}` | {record.size} | `{record.sha256}` |")
    lines.append("")
    return "\n".join(lines).encode("utf-8")


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(filename=name, date_time=FIXED_ZIP_TIME)
    info.compress_type = zipfile.ZIP_STORED
    info.create_system = 3
    info.external_attr = (0o100644 & 0xFFFF) << 16
    info.flag_bits |= 0x800
    return info


def _write_entry(archive: zipfile.ZipFile, name: str, data: bytes) -> None:
    archive.writestr(_zip_info(name), data)


def build_bundle(
    *,
    base: Path,
    sources: tuple[Path, ...],
    output: Path,
    excludes: tuple[str, ...] = (),
    metadata: dict[str, str] | None = None,
) -> dict[str, object]:
    base = base.expanduser().resolve()
    output = output.expanduser().resolve()
    if not base.is_dir():
        raise BundleError(f"--base is not a directory: {base}")

    output.parent.mkdir(parents=True, exist_ok=True)
    metadata = dict(metadata or {})

    files = _collect_files(
        base=base,
        sources=sources,
        excludes=excludes,
        output=output,
    )
    records = _inventory(base, files)
    payload = _manifest(records, metadata)
    summary = _summary_bytes(records, metadata)

    by_relative = {path.relative_to(base).as_posix(): path for path in files}

    handle = tempfile.NamedTemporaryFile(
        prefix=f".{output.name}.",
        suffix=".tmp",
        dir=output.parent,
        delete=False,
    )
    temp_path = Path(handle.name)
    handle.close()

    try:
        with zipfile.ZipFile(temp_path, "w", allowZip64=True) as archive:
            _write_entry(archive, f"{RESERVED_PREFIX}manifest.json", _manifest_bytes(payload))
            _write_entry(archive, f"{RESERVED_PREFIX}summary.md", summary)

            for record in records:
                data = by_relative[record.path].read_bytes()
                if len(data) != record.size or _sha256_bytes(data) != record.sha256:
                    raise BundleError(
                        f"source changed while bundle was being built: {record.path}"
                    )
                _write_entry(archive, record.path, data)

        with temp_path.open("r+b") as stream:
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, output)
    finally:
        if temp_path.exists():
            temp_path.unlink()

    result = dict(payload)
    result["archive"] = {
        "path": str(output),
        "bytes": output.stat().st_size,
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
    }
    return result


def _parse_metadata(items: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise BundleError(f"metadata must be KEY=VALUE: {item!r}")
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise BundleError("metadata key must not be empty")
        if key in result:
            raise BundleError(f"duplicate metadata key: {key}")
        result[key] = value
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a deterministic ZIP artifact bundle with manifest and hashes."
    )
    parser.add_argument("sources", nargs="+", type=Path)
    parser.add_argument("--base", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--metadata", action="append", default=[], metavar="KEY=VALUE")
    parser.add_argument("--json", action="store_true", help="Print result payload as JSON.")
    args = parser.parse_args(argv)

    try:
        metadata = _parse_metadata(args.metadata)
        payload = build_bundle(
            base=args.base,
            sources=tuple(args.sources),
            output=args.output,
            excludes=tuple(args.exclude),
            metadata=metadata,
        )
    except BundleError as error:
        print(f"bundle error: {error}", file=sys.stderr)
        return 2
    except OSError as error:
        print(f"I/O error: {error}", file=sys.stderr)
        return 1

    if args.json:
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        print()
    else:
        archive = payload["archive"]
        assert isinstance(archive, dict)
        totals = payload["totals"]
        assert isinstance(totals, dict)
        print(f"Bundle: {archive['path']}")
        print(f"Files : {totals['files']}")
        print(f"Bytes : {archive['bytes']}")
        print(f"SHA256: {archive['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
