# QAR v1 specification

## Binary layout
```
offset  bytes   field
0       4       ASCII QAR1
4       32      salt, secure RNG
36      12      nonce, secure RNG
48      n       AES-256-GCM ciphertext || 16-byte authentication tag
```

Header 0..47 is authenticated as AAD. Key = Argon2id(input passphrase bytes, salt, time_cost=3, memory_cost=131072 KiB, parallelism=2, hash_len=32). Cipher = AES-256-GCM with random 96-bit nonce.

The plaintext is a ZIP of one file at normalized timestamp 1980-01-01 and file mode 0600; deflate level 6. Encrypted file has recognizable header `QAR1`. ZIP entries retain the source **basename**, but the basename is inaccessible before decryption.

## CLI
`python src/qar.py encrypt SOURCE OUTPUT.qar [--password-fd N]` or `python src/qar.py decrypt SOURCE.qar OUTPUT.zip [--password-fd N]`.
- Existing outputs are rejected, return code 2.
- Invalid source, oversize source, bad passphrase, tampered archive or invalid format return code 2.
- Success returns code 0; output filename printed.
- Other I/O and format errors return code 2; no full traceback by default.
- A source symlink is rejected. Arbitrary symlinks inside source file contents are not relevant.
- A recovered ZIP is **not extracted**.

## Reproducibility
For the same plaintext and password, output files are **intentionally different** (fresh salt and nonce). Successful decryption yields a ZIP containing the source's exact bytes, independently verifiable by content hashing. The ZIP itself may be implementation-dependent in metadata/DEFLATE representation.
