# QAR Authenticated Archive

Experimental offline utility for an **authenticated, encrypted archive of one source file** (for example an exported HTML conversation). The input can be HTML, text, JSON, or any regular file. The filename is inside the encrypted ZIP. This module is reusable and has **no connection to a specific ChatGPT session, microscope or DIY project**.

## Installation and invocation

Python 3.11+, `cryptography>=42,<47`, `argon2-cffi>=23.1,<26`. Does not use network during encryption or decryption. Linux tested; other platforms unverified.

```bash
python -m pip install 'cryptography>=42,<47' 'argon2-cffi>=23.1,<26'
python qar-authenticated-archive/src/qar.py encrypt /path/to/export.html /path/to/backup.qar
python qar-authenticated-archive/src/qar.py decrypt /path/to/backup.qar /path/to/recovered.zip
python -m unittest discover -s qar-authenticated-archive/tests -p 'test_qar.py' -v
```

Password is entered interactively with `getpass` (not echoed, not passed through shell args), or supplied with `--password-fd N` as **exact raw bytes** through an existing protected file descriptor. In FD mode, trailing newline characters are not stripped. Interactive input is UTF-8 encoded without Unicode normalization. This is deliberate: arbitrary bytes in a passphrase must not be reinterpreted. Do not put a secret in command arguments, files within Git, environment variables or screenshots.

By default encryption refuses to overwrite any existing output and decryption refuses to overwrite an existing ZIP. Recovery creates an authenticated ZIP but **does not extract it**. The source file is not removed after encryption, so handle plaintext working copies independently. The command prints only its output path.

## Format and security

`.qar` v1 = ASCII magic `QAR1` (4 B), random salt (32 B), random AES-GCM nonce (12 B), then ciphertext and GCM tag (16 B). The header is authenticated as AES-GCM AAD. Argon2id uses 128 MiB, 3 iterations, 2 lanes, 32-byte derived key; payload uses AES-256-GCM. New independent salt and nonce are generated for each archive. A ZIP containing the original file is created in memory before encryption; input bound 64 MiB, ciphertext bound 72 MiB. No plaintext temporary ZIP is written during encryption.

Visible metadata: ciphertext size, QAR magic, file path, filesystem/Git timestamps and number of snapshots. Names and actual file contents inside ZIP remain encrypted.

**Limitations:** This is an experimental script, not a formal audited security product. Compromised endpoints, disclosed passwords, Git metadata, failure to retain a working key, and accidental plaintext commits are outside its protection. Source/export can remain readable on disk. An attacker with both account chat logs and a passphrase recorded in them can decrypt the archive. No per-user access control, hidden volumes, rollback detection, in-place rotation or canonical transcript extraction is provided.

The long passphrase does not extend AES beyond 256-bit key strength, and no security guarantee is made from the encrypted file *looking like noise*. Encryption intentionally uses an identifiable format.

Documentation: [architecture](docs/architecture.md) · [specification](docs/specification.md) · [limitations](docs/limitations.md).

Original prototype was created for LOMO Biolam S-11 archival work in `quendoris/DIY`, later extracted into this project-neutral snippet. No private archive contents or passwords are stored in this repository.
