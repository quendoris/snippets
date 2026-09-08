from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tempfile
import tomllib
from typing import Iterable
from urllib.parse import urlparse
from urllib.request import Request, urlopen


@dataclass(frozen=True, slots=True)
class AssetSpec:
    name: str
    source_url: str
    destination: str
    size: int
    sha256: str
    git_blob_sha1: str | None = None


@dataclass(frozen=True, slots=True)
class VendorManifest:
    user_agent: str
    assets: tuple[AssetSpec, ...]


@dataclass(frozen=True, slots=True)
class AssetResult:
    name: str
    destination: str
    size: int
    sha256: str
    git_blob_sha1: str
    action: str


class VendorConfigurationError(RuntimeError):
    pass


class AssetIntegrityError(RuntimeError):
    pass


def git_blob_sha1(data: bytes) -> str:
    payload = f"blob {len(data)}\0".encode("ascii") + data
    return hashlib.sha1(payload, usedforsecurity=False).hexdigest()


def _valid_hex(value: str, length: int) -> bool:
    return len(value) == length and all(char in "0123456789abcdef" for char in value)


def _safe_relative_path(value: str, context: str) -> str:
    if not value or "\\" in value:
        raise VendorConfigurationError(f"{context} must be a non-empty POSIX relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise VendorConfigurationError(f"{context} must not be absolute or traverse parents")
    return path.as_posix()


def _https_url(value: object, context: str) -> str:
    if not isinstance(value, str) or not value:
        raise VendorConfigurationError(f"{context} must be a non-empty HTTPS URL")
    parsed = urlparse(value)
    if parsed.scheme.lower() != "https" or not parsed.netloc:
        raise VendorConfigurationError(f"{context} must use an absolute HTTPS URL")
    if parsed.username is not None or parsed.password is not None:
        raise VendorConfigurationError(f"{context} must not embed URL credentials")
    return value


def load_manifest(path: Path) -> VendorManifest:
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise VendorConfigurationError(f"cannot read asset manifest: {path}") from error
    except tomllib.TOMLDecodeError as error:
        raise VendorConfigurationError(f"cannot parse asset manifest: {error}") from error

    if raw.get("schema") != 1:
        raise VendorConfigurationError("asset manifest requires schema = 1")
    user_agent = raw.get("user_agent", "pinned-asset-vendor/0.1")
    if not isinstance(user_agent, str) or not user_agent.strip():
        raise VendorConfigurationError("user_agent must be a non-empty string")

    raw_assets = raw.get("asset")
    if not isinstance(raw_assets, list) or not raw_assets:
        raise VendorConfigurationError("asset manifest requires at least one [[asset]]")

    assets: list[AssetSpec] = []
    names: set[str] = set()
    destinations: set[str] = set()
    for index, raw_asset in enumerate(raw_assets, start=1):
        context = f"asset[{index}]"
        if not isinstance(raw_asset, dict):
            raise VendorConfigurationError(f"{context} must be a TOML table")

        name = raw_asset.get("name")
        if not isinstance(name, str) or not name.strip():
            raise VendorConfigurationError(f"{context}.name must be a non-empty string")
        name = name.strip()
        if name in names:
            raise VendorConfigurationError(f"duplicate asset name: {name}")
        names.add(name)

        source_url = _https_url(raw_asset.get("source_url"), f"{context}.source_url")
        destination = _safe_relative_path(
            str(raw_asset.get("destination", "")),
            f"{context}.destination",
        )
        if destination in destinations:
            raise VendorConfigurationError(f"duplicate destination: {destination}")
        destinations.add(destination)

        size = raw_asset.get("size")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise VendorConfigurationError(f"{context}.size must be an integer >= 0")

        sha256 = raw_asset.get("sha256")
        if not isinstance(sha256, str) or not _valid_hex(sha256, 64):
            raise VendorConfigurationError(
                f"{context}.sha256 must be a lowercase 64-character hex digest"
            )

        git_sha = raw_asset.get("git_blob_sha1")
        if git_sha is not None:
            if not isinstance(git_sha, str) or not _valid_hex(git_sha, 40):
                raise VendorConfigurationError(
                    f"{context}.git_blob_sha1 must be lowercase 40-character hex when present"
                )

        assets.append(
            AssetSpec(
                name=name,
                source_url=source_url,
                destination=destination,
                size=size,
                sha256=sha256,
                git_blob_sha1=git_sha,
            )
        )

    return VendorManifest(user_agent=user_agent.strip(), assets=tuple(assets))


def verify_bytes(data: bytes, spec: AssetSpec) -> AssetResult:
    if len(data) != spec.size:
        raise AssetIntegrityError(
            f"{spec.name}: size mismatch: {len(data)} != {spec.size}"
        )
    actual_sha256 = hashlib.sha256(data).hexdigest()
    if actual_sha256 != spec.sha256:
        raise AssetIntegrityError(
            f"{spec.name}: SHA-256 mismatch: {actual_sha256} != {spec.sha256}"
        )
    actual_git_sha = git_blob_sha1(data)
    if spec.git_blob_sha1 is not None and actual_git_sha != spec.git_blob_sha1:
        raise AssetIntegrityError(
            f"{spec.name}: Git blob SHA-1 mismatch: "
            f"{actual_git_sha} != {spec.git_blob_sha1}"
        )
    return AssetResult(
        name=spec.name,
        destination=spec.destination,
        size=len(data),
        sha256=actual_sha256,
        git_blob_sha1=actual_git_sha,
        action="verified",
    )


def verify_file(root: Path, spec: AssetSpec) -> AssetResult:
    path = root / PurePosixPath(spec.destination)
    try:
        data = path.read_bytes()
    except OSError as error:
        raise AssetIntegrityError(f"{spec.name}: missing/unreadable asset: {path}") from error
    return verify_bytes(data, spec)


def _download(url: str, *, user_agent: str, timeout: float) -> bytes:
    request = Request(url, headers={"User-Agent": user_agent})
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - HTTPS validated in manifest
        final = urlparse(response.geturl())
        if final.scheme.lower() != "https":
            raise AssetIntegrityError("asset download redirected away from HTTPS")
        return response.read()


def vendor_asset(
    root: Path,
    spec: AssetSpec,
    *,
    user_agent: str,
    timeout: float,
) -> AssetResult:
    destination = root / PurePosixPath(spec.destination)
    if destination.is_file():
        try:
            existing = verify_file(root, spec)
        except AssetIntegrityError:
            pass
        else:
            return AssetResult(**{**asdict(existing), "action": "already-verified"})

    data = _download(spec.source_url, user_agent=user_agent, timeout=timeout)
    verified = verify_bytes(data, spec)
    destination.parent.mkdir(parents=True, exist_ok=True)

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=destination.name + ".",
        suffix=".tmp",
        dir=destination.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        # Verify bytes as published to disk, not only the in-memory response.
        disk = temporary.read_bytes()
        verify_bytes(disk, spec)
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()

    return AssetResult(**{**asdict(verified), "action": "vendored"})


def run(
    *,
    root: Path,
    manifest: VendorManifest,
    check_only: bool,
    timeout: float,
) -> tuple[AssetResult, ...]:
    root = root.resolve()
    results: list[AssetResult] = []
    for spec in manifest.assets:
        if check_only:
            result = verify_file(root, spec)
        else:
            result = vendor_asset(
                root,
                spec,
                user_agent=manifest.user_agent,
                timeout=timeout,
            )
        results.append(result)
    return tuple(results)


def report_payload(results: Iterable[AssetResult], *, check_only: bool) -> dict[str, object]:
    items = tuple(results)
    return {
        "passed": True,
        "mode": "check" if check_only else "vendor",
        "asset_count": len(items),
        "assets": [asdict(item) for item in items],
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Vendor or offline-verify exact-byte pinned HTTPS assets.",
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if not (args.timeout > 0.0):
        print("Pinned asset vendor configuration error: --timeout must be > 0")
        return 2
    root = args.root.resolve()
    manifest_path = args.manifest if args.manifest.is_absolute() else root / args.manifest
    try:
        manifest = load_manifest(manifest_path)
        results = run(
            root=root,
            manifest=manifest,
            check_only=args.check,
            timeout=args.timeout,
        )
    except VendorConfigurationError as error:
        if args.json:
            print(json.dumps({"passed": False, "error": str(error)}, ensure_ascii=False))
        else:
            print(f"Pinned asset vendor configuration error: {error}")
        return 2
    except (AssetIntegrityError, OSError) as error:
        if args.json:
            print(json.dumps({"passed": False, "error": str(error)}, ensure_ascii=False))
        else:
            print(f"Pinned asset vendor failed: {error}")
        return 1

    payload = report_payload(results, check_only=args.check)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for result in results:
            print(
                f"{result.action.upper()} {result.name}: "
                f"{result.destination} size={result.size} "
                f"sha256={result.sha256} git_blob_sha1={result.git_blob_sha1}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
