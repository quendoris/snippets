#!/usr/bin/env python3
"""Build a portable, deterministic batch of page assets and aligned evidence files."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import shutil
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

SAFE_ID = re.compile(r"^[A-Za-z0-9._-]+$")
SCHEMA = "page-evidence-batcher-v1"


class BatchError(RuntimeError):
    """User-facing contract failure."""


@dataclass(frozen=True)
class EvidenceSpec:
    name: str
    template: str


@dataclass(frozen=True)
class PlannedPage:
    record: Mapping[str, Any]
    page_id: str
    index: int
    source: Path
    source_sha256: str
    source_suffix: str
    evidence: Mapping[str, Path]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_evidence_specs(values: Iterable[str]) -> list[EvidenceSpec]:
    specs: list[EvidenceSpec] = []
    seen: set[str] = set()
    for value in values:
        if "=" not in value:
            raise BatchError(f"invalid --evidence {value!r}; expected NAME=PATH_TEMPLATE")
        name, template = value.split("=", 1)
        name = name.strip()
        template = template.strip()
        if not name or not SAFE_ID.fullmatch(name):
            raise BatchError(f"invalid evidence name {name!r}")
        if name in seen:
            raise BatchError(f"duplicate evidence name {name!r}")
        if not template:
            raise BatchError(f"empty evidence template for {name!r}")
        seen.add(name)
        specs.append(EvidenceSpec(name=name, template=template))
    return specs


def load_manifest(path: Path, records_key: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise BatchError(f"cannot read JSON manifest {path}: {exc}") from exc
    records = manifest.get(records_key)
    if not isinstance(records, list):
        raise BatchError(f"manifest key {records_key!r} must contain an array")
    if not all(isinstance(item, dict) for item in records):
        raise BatchError(f"manifest key {records_key!r} must contain only objects")
    return manifest, records


def resolve_template(template: str, record: Mapping[str, Any], *, base: Path) -> Path:
    try:
        rendered = template.format_map(record)
    except KeyError as exc:
        raise BatchError(f"evidence template references missing field {exc.args[0]!r}") from exc
    path = Path(rendered)
    return path if path.is_absolute() else base / path


def _regular_file(path: Path, label: str) -> None:
    if not path.exists():
        raise BatchError(f"missing {label}: {path}")
    if path.is_symlink():
        raise BatchError(f"symlink {label} is not supported: {path}")
    if not path.is_file():
        raise BatchError(f"{label} is not a regular file: {path}")


def plan_batch(
    *,
    records: list[dict[str, Any]],
    start: int,
    count: int,
    id_field: str,
    index_field: str,
    source_field: str,
    sha256_field: str | None,
    source_base: Path,
    evidence_base: Path,
    evidence_specs: list[EvidenceSpec],
) -> list[PlannedPage]:
    if count < 1:
        raise BatchError("--count must be >= 1")

    by_index: dict[int, dict[str, Any]] = {}
    for record in records:
        try:
            index = int(record[index_field])
        except (KeyError, TypeError, ValueError) as exc:
            raise BatchError(f"record has invalid {index_field!r}: {record!r}") from exc
        if index in by_index:
            raise BatchError(f"duplicate page index {index}")
        by_index[index] = record

    selected: list[dict[str, Any]] = []
    for index in range(start, start + count):
        record = by_index.get(index)
        if record is None:
            if not selected:
                raise BatchError(f"no page record at index {index}")
            break
        selected.append(record)

    if not selected:
        raise BatchError("empty selection")

    planned: list[PlannedPage] = []
    seen_ids: set[str] = set()
    for record in selected:
        raw_id = record.get(id_field)
        if not isinstance(raw_id, str) or not SAFE_ID.fullmatch(raw_id):
            raise BatchError(f"unsafe or missing page id {raw_id!r}")
        if raw_id in seen_ids:
            raise BatchError(f"duplicate page id {raw_id!r}")
        seen_ids.add(raw_id)

        index = int(record[index_field])
        raw_source = record.get(source_field)
        if not isinstance(raw_source, str) or not raw_source:
            raise BatchError(f"{raw_id}: missing source field {source_field!r}")
        source = Path(raw_source)
        if not source.is_absolute():
            source = source_base / source
        _regular_file(source, f"source page for {raw_id}")

        actual_sha = sha256_file(source)
        if sha256_field:
            expected = record.get(sha256_field)
            if expected is not None and expected != actual_sha:
                raise BatchError(
                    f"{raw_id}: source SHA-256 mismatch: manifest={expected} actual={actual_sha}"
                )

        evidence: dict[str, Path] = {}
        for spec in evidence_specs:
            path = resolve_template(spec.template, record, base=evidence_base)
            _regular_file(path, f"{spec.name} evidence for {raw_id}")
            evidence[spec.name] = path

        planned.append(
            PlannedPage(
                record=record,
                page_id=raw_id,
                index=index,
                source=source,
                source_sha256=actual_sha,
                source_suffix=source.suffix.lower(),
                evidence=evidence,
            )
        )

    return planned


def _copy_file(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def build_directory(
    *,
    root: Path,
    planned: list[PlannedPage],
    source_manifest: Path,
    evidence_specs: list[EvidenceSpec],
    carry_fields: list[str],
) -> dict[str, Any]:
    (root / "pages").mkdir(parents=True)
    for spec in evidence_specs:
        (root / "evidence" / spec.name).mkdir(parents=True)

    out_records: list[dict[str, Any]] = []
    for page in planned:
        page_name = f"{page.page_id}{page.source_suffix}"
        _copy_file(page.source, root / "pages" / page_name)

        evidence_paths: dict[str, str] = {}
        for spec in evidence_specs:
            source = page.evidence[spec.name]
            suffix = source.suffix.lower()
            target = root / "evidence" / spec.name / f"{page.page_id}{suffix}"
            _copy_file(source, target)
            evidence_paths[spec.name] = target.relative_to(root).as_posix()

        carried = {field: page.record.get(field) for field in carry_fields}
        out_records.append(
            {
                "id": page.page_id,
                "index": page.index,
                "source_sha256": page.source_sha256,
                "page_file": f"pages/{page_name}",
                "evidence": evidence_paths,
                "metadata": carried,
            }
        )

    output_manifest = {
        "schema": SCHEMA,
        "source_manifest": str(source_manifest),
        "range": {
            "start": planned[0].index,
            "end": planned[-1].index,
            "count": len(planned),
        },
        "evidence": [spec.name for spec in evidence_specs],
        "records": out_records,
    }
    (root / "manifest.json").write_text(
        json.dumps(output_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (root / "README.txt").write_text(
        "Page evidence batch\n\n"
        "Each record contains one source page asset and zero or more page-aligned "
        "evidence files. Evidence is packaged for review; this format does not "
        "declare any evidence layer canonical.\n",
        encoding="utf-8",
    )
    return output_manifest


def _normalized_tarinfo(path: Path, arcname: str) -> tarfile.TarInfo:
    info = tarfile.TarInfo(arcname)
    st = path.stat()
    info.size = st.st_size if path.is_file() else 0
    info.type = tarfile.REGTYPE if path.is_file() else tarfile.DIRTYPE
    info.mode = 0o644 if path.is_file() else 0o755
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    info.mtime = 0
    return info


def write_deterministic_tar_gz(root: Path, archive: Path, arcroot: str) -> None:
    archive.parent.mkdir(parents=True, exist_ok=True)
    with archive.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode="w") as tf:
                dirs = [root] + sorted((p for p in root.rglob("*") if p.is_dir()), key=lambda p: p.as_posix())
                files = sorted((p for p in root.rglob("*") if p.is_file()), key=lambda p: p.as_posix())
                for path in dirs + files:
                    rel = path.relative_to(root).as_posix()
                    arcname = arcroot if rel == "." else f"{arcroot}/{rel}"
                    info = _normalized_tarinfo(path, arcname)
                    if path.is_file():
                        with path.open("rb") as fh:
                            tf.addfile(info, fh)
                    else:
                        tf.addfile(info)


def publish_batch(
    *,
    out_dir: Path,
    name_prefix: str,
    planned: list[PlannedPage],
    source_manifest: Path,
    evidence_specs: list[EvidenceSpec],
    carry_fields: list[str],
) -> tuple[Path, Path, dict[str, Any]]:
    if not SAFE_ID.fullmatch(name_prefix):
        raise BatchError(f"unsafe --name-prefix {name_prefix!r}")
    first, last = planned[0].index, planned[-1].index
    name = f"{name_prefix}-{first:04d}-{last:04d}"
    out_dir.mkdir(parents=True, exist_ok=True)
    final_root = out_dir / name
    final_archive = out_dir / f"{name}.tar.gz"

    with tempfile.TemporaryDirectory(prefix=f".{name}.", dir=out_dir) as tmp:
        tmp_path = Path(tmp)
        staging_root = tmp_path / name
        manifest = build_directory(
            root=staging_root,
            planned=planned,
            source_manifest=source_manifest,
            evidence_specs=evidence_specs,
            carry_fields=carry_fields,
        )
        staging_archive = tmp_path / f"{name}.tar.gz"
        write_deterministic_tar_gz(staging_root, staging_archive, name)

        if final_root.exists():
            shutil.rmtree(final_root)
        os.replace(staging_root, final_root)
        os.replace(staging_archive, final_archive)

    return final_root, final_archive, manifest


def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--records-key", default="records")
    ap.add_argument("--start", type=int, required=True)
    ap.add_argument("--count", type=int, default=20)
    ap.add_argument("--id-field", default="id")
    ap.add_argument("--index-field", default="physical_index")
    ap.add_argument("--source-field", default="path")
    ap.add_argument("--sha256-field", default="sha256")
    ap.add_argument("--source-base", type=Path, default=Path("."))
    ap.add_argument("--evidence-base", type=Path, default=Path("."))
    ap.add_argument(
        "--evidence",
        action="append",
        default=[],
        metavar="NAME=PATH_TEMPLATE",
        help="repeatable; template may reference manifest fields, e.g. rus=ocr/rus/{id}.txt",
    )
    ap.add_argument("--carry-field", action="append", default=[])
    ap.add_argument("--out-dir", type=Path, default=Path("work/page-evidence-batches"))
    ap.add_argument("--name-prefix", default="page-evidence")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        _, records = load_manifest(args.manifest, args.records_key)
        evidence_specs = parse_evidence_specs(args.evidence)
        planned = plan_batch(
            records=records,
            start=args.start,
            count=args.count,
            id_field=args.id_field,
            index_field=args.index_field,
            source_field=args.source_field,
            sha256_field=args.sha256_field or None,
            source_base=args.source_base,
            evidence_base=args.evidence_base,
            evidence_specs=evidence_specs,
        )
        root, archive, manifest = publish_batch(
            out_dir=args.out_dir,
            name_prefix=args.name_prefix,
            planned=planned,
            source_manifest=args.manifest,
            evidence_specs=evidence_specs,
            carry_fields=args.carry_field,
        )
    except BatchError as exc:
        print(f"error: {exc}", file=os.sys.stderr)
        return 2

    r = manifest["range"]
    print(f"Pages: {r['start']}-{r['end']} ({r['count']})")
    print(f"Directory: {root}")
    print(f"Archive: {archive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
