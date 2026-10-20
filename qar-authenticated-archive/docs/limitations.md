# Limitations and security caveats

- Linux is the tested platform for atomic no-overwrite publication using `os.link`. Portability to Windows or other filesystems is not established.
- Format v1 is memory-buffered and limited to one regular file with size <=64 MiB. Archive decrypted output must end in .zip.
- KDF parameters are fixed in code, not negotiated in the binary header. Format evolution requires an explicit new magic/format version and compatibility tests.
- Password input can include arbitrary bytes only in file-descriptor mode. Interactive prompts encode entered Unicode to UTF-8 exactly; no normalization is applied.
- Encryption includes original basename inside ZIP; only encrypted metadata protects it. Git paths, timestamps, source filename outside this archive and ciphertext size are **not** hidden.
- An exported browser SingleFile HTML may contain URLs, scripts, asset blobs and account metadata; choose a trusted source export carefully before archiving.
- A very long passphrase is not evidence that it was sampled uniformly. Human-readable SQL-like fragments are aesthetic/format obfuscation, not a substitute for entropy.
- No cryptographic audit or secure secret wiping in Python is claimed. Local plaintext export, decrypted output, swap and process-memory artifacts can remain.
- Authentication detects corrupted ciphertext, but does not prevent rollback from a valid earlier archive or deletion of an archive. Backups/provenance are separately required.
- Directory fsync after publish is not implemented; do not claim full crash-durable storage semantics. For critical backups, verify restored bytes and maintain independent copies.
- Caller must guard against malicious recovered ZIP on extraction by selecting trusted file names and paths. The tool never automatically extracts.
