# Architecture

`source regular file` → `memory ZIP, one entry, normalized timestamp` → `Argon2id(salt, passphrase)` → `AES-256-GCM(nonce, ZIP, authenticated header)` → `exclusive destination .qar`.

Decryption reverses the encryption pipeline, authenticates before publishing a local ZIP, and **never extracts it**. The passphrase is read from the terminal with `getpass`, or as exact bytes from a caller-owned descriptor. QAR magic, random salt and nonce are not secret.

Input remains on disk; output is produced with a temporary private file (0600) and a no-clobber hard-link publication. Failures remove the temp path. No source-file deletion. Filesystem semantics are tested on Linux. Enforced one-file input and memory limits; intentionally no file streaming.

## Boundaries

Archive core owns encoding, authentication, integrity and publication of local files. It does *not* parse or scrape chats, interact with Git, handle passwords, provide authentication to remote services, check for deleted messages in exports, or determine whether a recovered export is complete.
