#!/usr/bin/env python3
"""Offline Argon2id + AES-256-GCM authenticated single-file ZIP archiver."""

from __future__ import annotations

import argparse
import getpass
import io
import os
from pathlib import Path
import stat
import sys
import tempfile
import zipfile

from argon2.low_level import Type, hash_secret_raw
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC = b"QAR1"  # Obvious encrypted file header, no pretend obfuscation.
SALT_LEN = 32
NONCE_LEN = 12
HEADER_LEN = len(MAGIC) + SALT_LEN + NONCE_LEN
KDF_TIME = 3
KDF_MEMORY_KIB = 131072  # 128 MiB
KDF_PARALLELISM = 2
MAX_SOURCE_BYTES = 64 * 1024 * 1024
MAX_CIPHERTEXT_BYTES = 72 * 1024 * 1024


def _password(password_fd: int | None) -> bytes:
    if password_fd is None:
        # getpass returns a Unicode string with no added line-feed.
        value = getpass.getpass("Archive passphrase (not displayed): ")
        result = value.encode("utf-8", errors="strict")
    else:
        # Read *exact* bytes, including any trailing newline if supplied.
        # Never silently strip, normalize, or reinterpret Unicode.
        with os.fdopen(os.dup(password_fd), "rb") as stream:
            result = stream.read(64 * 1024 + 1)
    if not result or len(result) > 64 * 1024:
        raise ValueError("Passphrase must contain 1..65536 bytes")
    return result


def _derive(passphrase: bytes, salt: bytes) -> bytes:
    return hash_secret_raw(passphrase, salt, time_cost=KDF_TIME,
                           memory_cost=KDF_MEMORY_KIB,
                           parallelism=KDF_PARALLELISM,
                           hash_len=32, type=Type.ID)


def _write_new_private_file(dest: Path, data: bytes) -> None:
    if dest.exists():
        raise FileExistsError(f"Output already exists: {dest}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    # Named temporary in the same directory for atomic publish, mode 0600.
    fd, tmp_name = tempfile.mkstemp(prefix=".qar-pending-", dir=str(dest.parent))
    try:
        with os.fdopen(fd, "wb") as stream:
            os.fchmod(stream.fileno(), stat.S_IRUSR | stat.S_IWUSR)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        # Never silently clobber a pre-existing encrypted archive or export.
        if dest.exists():
            raise FileExistsError(f"Output appeared while writing: {dest}")
        os.link(tmp_name, dest)  # fails atomically when destination exists
    finally:
        os.unlink(tmp_name)


def _zip_one(src: Path) -> bytes:
    if not src.is_file() or src.is_symlink():
        raise ValueError("Source must be a regular non-symlink file")
    if src.stat().st_size > MAX_SOURCE_BYTES:
        raise ValueError("Source too large for memory-buffered archive")
    name = src.name
    if name in ("", ".", "..") or "/" in name or "\\" in name:
        raise ValueError("Unsafe input filename")
    raw = src.read_bytes()
    if len(raw) > MAX_SOURCE_BYTES:
        raise ValueError("Source grew during reading")
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        info = zipfile.ZipInfo(filename=name, date_time=(1980, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o600 << 16
        archive.writestr(info, raw, compress_type=zipfile.ZIP_DEFLATED, compresslevel=6)
    return out.getvalue()


def encrypt(src: Path, dest: Path, passphrase: bytes) -> None:
    if src.resolve() == dest.resolve():
        raise ValueError("Source and destination cannot be the same path")
    data = _zip_one(src)
    salt = os.urandom(SALT_LEN)
    nonce = os.urandom(NONCE_LEN)
    header = MAGIC + salt + nonce
    ciphertext = AESGCM(_derive(passphrase, salt)).encrypt(nonce, data, header)
    _write_new_private_file(dest, header + ciphertext)


def decrypt(src: Path, dest: Path, passphrase: bytes) -> None:
    if src.resolve() == dest.resolve():
        raise ValueError("Source and destination cannot be the same path")
    if src.stat().st_size > MAX_CIPHERTEXT_BYTES:
        raise ValueError("Encrypted archive exceeds safety limit")
    payload = src.read_bytes()
    if len(payload) < HEADER_LEN + 16 or payload[:len(MAGIC)] != MAGIC:
        raise ValueError("Invalid/unsupported QAR archive header")
    salt = payload[len(MAGIC):len(MAGIC) + SALT_LEN]
    nonce = payload[len(MAGIC) + SALT_LEN:HEADER_LEN]
    try:
        plaintext_zip = AESGCM(_derive(passphrase, salt)).decrypt(
            nonce, payload[HEADER_LEN:], payload[:HEADER_LEN])
    except InvalidTag as err:
        raise ValueError("Authentication failed: wrong key or corrupted archive") from err
    if not zipfile.is_zipfile(io.BytesIO(plaintext_zip)):
        raise ValueError("Authenticated content is not ZIP")
    # No automatic extraction of untrusted ZIP content.
    _write_new_private_file(dest, plaintext_zip)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("encrypt", "decrypt"))
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--password-fd", type=int, default=None,
                        help="read exact UTF-8/byte passphrase from this file descriptor")
    args = parser.parse_args(argv)
    try:
        secret = _password(args.password_fd)
        if args.mode == "encrypt":
            if args.output.suffix.lower() != ".qar":
                raise ValueError("Encrypted archives must end with .qar")
            encrypt(args.source, args.output, secret)
        else:
            if args.output.suffix.lower() != ".zip":
                raise ValueError("Decrypted archive destination must end with .zip")
            decrypt(args.source, args.output, secret)
    except (OSError, ValueError, zipfile.BadZipFile) as err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 2
    print(f"Created: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
