# filecrypt

> Secure AES-256 file encryption and decryption — single-file Python CLI

`filecrypt.py` is a self-contained command-line tool for encrypting, decrypting, and securely deleting files. It uses AES-256-CBC encryption with a strong key derivation function and is designed with security best practices throughout.

---

## Features

- **AES-256-CBC encryption** via the [AES Crypt v2](https://www.aescrypt.com/aes_file_format.html) file format (`.aes`)
- **Strong key derivation** — PBKDF2-HMAC-SHA256 with 600,000 iterations
- **Per-file random salt** — a unique 32-byte salt is generated and stored per encrypted file
- **Secure password prompts** — passwords are never echoed to the terminal (`getpass`)
- **Password confirmation** required when encrypting to prevent typo-induced data loss
- **Atomic writes** — a temp file is written first, renamed only on full success
- **Guaranteed cleanup** — partial or failed output files are always removed
- **Overwrite protection** — will not silently clobber existing files without `--overwrite`
- **Secure shred** — multi-pass random overwrite before deletion
- **Legacy file support** — can attempt decryption of old `.aes` files without the filecrypt header
- **Single file, no GUI** — zero external dependencies beyond `pyaescrypt`
- **Cross-platform** — works on Linux, macOS, and Windows

---

## Requirements

- Python 3.10 or newer
- [`pyaescrypt`](https://pypi.org/project/pyaescrypt/)

```bash
pip install pyaescrypt
```

---

## Installation

Download the single script and make it executable:

```bash
# Download
curl -O https://raw.githubusercontent.com/sak110/filecrypt/master/filecrypt.py

# (Optional) Make executable
chmod +x filecrypt.py
```

No virtual environment required. The only dependency is `pyaescrypt`.

---

## Usage

```
python filecrypt.py COMMAND [FILE] [OPTIONS]
```

### Commands

| Command | Aliases | Description |
|---|---|---|
| `encrypt` | `enc`, `e` | Encrypt a file |
| `decrypt` | `dec`, `d` | Decrypt an `.aes` file |
| `shred` | `wipe`, `s` | Securely overwrite and delete a file |

### Global Flags

| Flag | Description |
|---|---|
| `-v`, `--verbose` | Show detailed progress (salt, file sizes, timings) |
| `-q`, `--quiet` | Suppress all output except errors |
| `--version` | Print version and exit |
| `-h`, `--help` | Show help message |

---

## Commands in Detail

### `encrypt`

Encrypts a file using AES-256. Output file will have the `.aes` extension appended.

```
python filecrypt.py encrypt FILE [-o PATH] [--overwrite] [--password PASS]
```

| Argument | Description |
|---|---|
| `FILE` | Path to the file to encrypt |
| `-o`, `--output PATH` | Custom path for the encrypted output file |
| `--overwrite` | Overwrite the output file if it already exists |
| `--password PASS` | Supply passphrase inline *(not recommended — see Security Notes)* |

**Example:**

```bash
# Interactive (recommended — password is hidden)
python filecrypt.py encrypt report.pdf

# Custom output path
python filecrypt.py encrypt report.pdf --output /secure/report.pdf.aes

# Overwrite if the .aes file already exists
python filecrypt.py encrypt report.pdf --overwrite
```

When run interactively, you will be prompted twice to enter and confirm your passphrase. The passphrase must be at least 8 characters.

---

### `decrypt`

Decrypts an `.aes` file produced by filecrypt (or legacy pyAesCrypt files).

```
python filecrypt.py decrypt FILE [-o PATH] [--overwrite] [--password PASS]
```

| Argument | Description |
|---|---|
| `FILE` | Path to the `.aes` encrypted file |
| `-o`, `--output PATH` | Custom path for the decrypted output file |
| `--overwrite` | Overwrite the output file if it already exists |
| `--password PASS` | Supply passphrase inline *(not recommended)* |

**Example:**

```bash
# Decrypt to report.pdf (strips .aes extension automatically)
python filecrypt.py decrypt report.pdf.aes

# Decrypt to a specific path
python filecrypt.py decrypt report.pdf.aes --output ~/Documents/report.pdf

# Verbose — shows salt, sizes, and timing
python filecrypt.py decrypt report.pdf.aes --verbose
```

If decryption fails due to a wrong passphrase or a corrupted file, the partial output is automatically deleted and an error is reported. No corrupted files are ever left behind.

---

### `shred`

Securely overwrites a file with random data multiple times before deleting it.

```
python filecrypt.py shred FILE [--passes N] [--yes]
```

| Argument | Description |
|---|---|
| `FILE` | Path to the file to shred |
| `--passes N` | Number of overwrite passes (default: 3) |
| `--yes`, `-y` | Skip the confirmation prompt |

**Example:**

```bash
# Shred with confirmation prompt
python filecrypt.py shred original_secret.pdf

# Shred with 7 passes, no prompt (useful in scripts)
python filecrypt.py shred original_secret.pdf --passes 7 --yes
```

> **Important:** Shredding is best-effort. On SSDs with wear-levelling, copy-on-write filesystems (APFS, btrfs), or network/cloud-backed storage, some copies of data may survive. For maximum security on SSDs, combine shredding with full-disk encryption at the OS level.

---

## Typical Workflow

```bash
# 1. Encrypt a sensitive file
python filecrypt.py encrypt taxes_2024.pdf
#    → taxes_2024.pdf.aes  (enter passphrase when prompted)

# 2. Securely delete the original
python filecrypt.py shred taxes_2024.pdf

# 3. Later, decrypt it
python filecrypt.py decrypt taxes_2024.pdf.aes
#    → taxes_2024.pdf  (enter passphrase when prompted)
```

---

## File Format

Encrypted `.aes` files produced by filecrypt v2 have the following structure:

```
┌─────────────────────────────────────────────┐
│  8 bytes  │  Magic header: "FCRYPT\x02\x00"  │
├─────────────────────────────────────────────┤
│ 32 bytes  │  Random per-file salt            │
├─────────────────────────────────────────────┤
│ variable  │  AES Crypt v2 encrypted payload  │
└─────────────────────────────────────────────┘
```

The magic header allows filecrypt to identify its own files and extract the salt. Files not matching this header are treated as legacy pyAesCrypt files and decryption is attempted without a salt.

---

## Security Design

### Key Derivation

The passphrase is never used directly as an encryption key. Instead, it is run through **PBKDF2-HMAC-SHA256** with:

- **600,000 iterations** (OWASP 2023 recommendation for PBKDF2-SHA256)
- **32-byte random salt**, unique per file
- **32-byte derived key** (256 bits)

This makes brute-force attacks against captured `.aes` files computationally expensive.

### Passphrase Handling

- Passphrases are read using `getpass.getpass()` — they are never displayed or echoed
- Passphrases are confirmed on encryption to prevent typo-caused data loss
- After use, the passphrase variable is overwritten with null bytes as a best-effort memory wipe
- The `--password` flag is provided for scripting but is **not recommended** — it may be visible in shell history, process listings (`ps aux`), or system logs

### Atomic Writes

All file writes go to a temporary file in the same directory as the intended output. The file is renamed to its final name only after a complete, successful write. This means:

- Power failures or errors cannot produce partial/corrupt output files
- The rename is atomic on POSIX systems (Linux, macOS)
- Temporary files are always cleaned up on any failure path

### Overwrite Protection

filecrypt will refuse to overwrite an existing file unless `--overwrite` is explicitly passed. This prevents accidental data loss.

---

## Exit Codes

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | Interrupted (Ctrl+C) or bad input |
| `2` | Input file not found |
| `3` | Output file already exists (use `--overwrite`) |
| `4` | Decryption failed — wrong passphrase or corrupted file |
| `5` | Permission denied |
| `6` | I/O or filesystem error |
| `99` | Unexpected internal error |

Exit codes make filecrypt easy to use in shell scripts:

```bash
python filecrypt.py decrypt backup.aes.enc --password "$PASS" --quiet
if [ $? -eq 4 ]; then
    echo "Wrong passphrase!"
fi
```

---

## Security Notes & Limitations

**Do not use `--password` in production scripts.** The passphrase will appear in:
- Your shell history (`~/.bash_history`, `~/.zsh_history`)
- Process listings visible to other users (`ps aux`)
- System audit logs on some configurations

Instead, use a secrets manager, environment variable read via `getpass`, or a key file.

**Shredding is not guaranteed on all storage types:**

| Storage Type | Shred Reliability |
|---|---|
| Traditional HDD | ✅ Generally effective |
| SSD (with wear-levelling) | ⚠️ Best-effort only |
| APFS / btrfs (CoW) | ⚠️ Original blocks may persist |
| Network / cloud storage | ❌ No guarantee |
| Encrypted volume (LUKS, FileVault) | ✅ Deleting the key is sufficient |

**Passphrase strength matters.** The KDF is intentionally slow, but a weak passphrase can still be brute-forced offline given the encrypted file. Use a long, random passphrase or a password manager.

**File metadata is not encrypted.** The filename, size, timestamps, and directory structure remain visible. Only the file contents are protected.

---

## Comparison with Original

This script is a complete rewrite of the original `filecrypt` project. Key differences:

| Aspect | Original | filecrypt v2 |
|---|---|---|
| Interface | Interactive menu (TUI) | `argparse` CLI |
| PBKDF2 iterations | 1,000 | 600,000 |
| Salt | Empty string | Random 32 bytes per file |
| Password input | `input()` — echoed | `getpass()` — hidden |
| Confirm on encrypt | No | Yes |
| Overwrite protection | None | `--overwrite` required |
| Output file on failure | May be left behind | Always cleaned up |
| Key encoding | `base64.b64encode(key).hex()` (double-encoded bug) | `raw_bytes.hex()` |
| Error handling | Recursive function calls | `try/except` with exit codes |
| Dependencies | `pyAesCrypt`, `pycrypto`, `Gooey` | `pyaescrypt` only |
| Files | 5 files across 2 packages | Single `.py` file |

---

## License

MIT License. See source file for full text.

---

## Contributing

Bug reports and pull requests are welcome. When reporting an issue, please include:

- Your operating system and Python version (`python --version`)
- The exact command you ran (with `--password` redacted)
- The full error output (run with `--verbose`)

