#!/usr/bin/env python3
import argparse
import getpass
import hashlib
import io
import os
import platform
import secrets
import shutil
import struct
import sys
import tempfile
import time
from pathlib import Path

try:
    import pyAesCrypt
except ImportError:
    print(
        "[ERROR] pyaescrypt is not installed.\n"
        "Install it with:  pip install pyaescrypt",
        file=sys.stderr,
    )
    sys.exit(1)


VERSION = "2.0.0"
TOOL_NAME = "filecrypt"

AES_EXTENSION = ".aes"
SALT_SIZE = 32          # bytes — stored as header prefix in output file
PBKDF2_ITERATIONS = 600_000
PBKDF2_HASH = "sha256"
DERIVED_KEY_LEN = 32    # 256-bit key for AES-256
BUFFER_SIZE = 64 * 1024  # 64 KiB streaming buffer
SHRED_PASSES = 3         # overwrite passes before deletion

HEADER_MAGIC = b"FCRYPT\x02\x00"  # 8-byte magic + version tag
HEADER_SIZE = len(HEADER_MAGIC) + SALT_SIZE  # 40 bytes total header

# ── Colour helpers (graceful fallback on Windows without ANSI) ────────────────

_USE_COLOR = sys.stdout.isatty() and platform.system() != "Windows"

def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _USE_COLOR else text

def green(t):  return _c("32", t)
def red(t):    return _c("31", t)
def yellow(t): return _c("33", t)
def bold(t):   return _c("1",  t)
def dim(t):    return _c("2",  t)

# ── Logging ───────────────────────────────────────────────────────────────────

_verbose = False
_quiet   = False

def log(msg: str):
    if not _quiet:
        print(msg)

def vlog(msg: str):
    if _verbose and not _quiet:
        print(dim(msg))

def err(msg: str):
    print(red(f"[ERROR] {msg}"), file=sys.stderr)

def warn(msg: str):
    if not _quiet:
        print(yellow(f"[WARN]  {msg}"))

def ok(msg: str):
    if not _quiet:
        print(green(f"[OK]    {msg}"))

# Key derivation

def derive_key(password: str, salt: bytes) -> str:
    vlog(f"Deriving key with {PBKDF2_ITERATIONS:,} PBKDF2 iterations …")
    raw = hashlib.pbkdf2_hmac(
        PBKDF2_HASH,
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
        dklen=DERIVED_KEY_LEN,
    )
    return raw.hex()  # 64-character hex string used as pyAesCrypt passphrase

# Password prompting

def prompt_password_encrypt() -> str:
    """Prompt for a new password with confirmation. Returns password string."""
    while True:
        pw1 = getpass.getpass("Enter passphrase:         ")
        if len(pw1) < 8:
            warn("Passphrase must be at least 8 characters. Try again.")
            continue
        pw2 = getpass.getpass("Confirm passphrase:       ")
        if pw1 != pw2:
            warn("Passphrases do not match. Try again.")
            continue
        return pw1

def prompt_password_decrypt() -> str:
    """Prompt for an existing password. Returns password string."""
    return getpass.getpass("Enter passphrase:         ")

# Secure temp-file helper

def _temp_path_near(target: Path) -> Path:
    """Return a temp file path in the same directory as *target*."""
    fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=f".{TOOL_NAME}_tmp_")
    os.close(fd)
    return Path(tmp)

# Encrypt

def encrypt_file(
    input_path: Path,
    output_path: Path,
    password: str,
    overwrite: bool = False,
) -> None:
    """
    Encrypt *input_path* → *output_path* (.aes).

    File format:
        [8 bytes magic+version] [32 bytes salt] [pyAesCrypt AES payload …]
    """
    # Pre-flight checks
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    if not input_path.is_file():
        raise ValueError(f"Input path is not a regular file: {input_path}")
    if output_path.exists() and not overwrite:
        raise FileExistsError(
            f"Output file already exists: {output_path}\n"
            f"Use --overwrite to replace it."
        )

    salt = secrets.token_bytes(SALT_SIZE)
    key  = derive_key(password, salt)

    vlog(f"Input:  {input_path}  ({input_path.stat().st_size:,} bytes)")
    vlog(f"Output: {output_path}")
    vlog(f"Salt:   {salt.hex()}")

    tmp_path = _temp_path_near(output_path)
    try:
        t0 = time.perf_counter()
        with open(tmp_path, "wb") as tmp_f:
            # Write our header (magic + salt) first
            tmp_f.write(HEADER_MAGIC)
            tmp_f.write(salt)
            tmp_f.flush()

            # Now append the pyAesCrypt encrypted payload
            with open(input_path, "rb") as in_f:
                pyAesCrypt.encryptStream(in_f, tmp_f, key, BUFFER_SIZE)

        elapsed = time.perf_counter() - t0

        # Atomic rename (same filesystem → rename is atomic on POSIX)
        if output_path.exists() and overwrite:
            output_path.unlink()
        tmp_path.rename(output_path)
        tmp_path = None  # prevent cleanup in finally

        size_in  = input_path.stat().st_size
        size_out = output_path.stat().st_size
        ok(f"Encrypted  {input_path.name}  →  {output_path.name}")
        log(f"           {size_in:,} bytes  →  {size_out:,} bytes  in {elapsed:.3f}s")

    except Exception:
        # Clean up partial output
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise

# Decrypt

def decrypt_file(
    input_path: Path,
    output_path: Path,
    password: str,
    overwrite: bool = False,
) -> None:
    """
    Decrypt *input_path* (.aes) → *output_path*.

    Reads our header to extract the salt, derives the key, then
    passes the remainder of the file to pyAesCrypt for decryption.
    """
    # Pre-flight checks
    if not input_path.exists():
        raise FileNotFoundError(f"Encrypted file not found: {input_path}")
    if not input_path.is_file():
        raise ValueError(f"Input path is not a regular file: {input_path}")
    if output_path.exists() and not overwrite:
        raise FileExistsError(
            f"Output file already exists: {output_path}\n"
            f"Use --overwrite to replace it."
        )

    tmp_path = _temp_path_near(output_path)
    try:
        with open(input_path, "rb") as in_f:
            # Read & validate header
            header_magic = in_f.read(len(HEADER_MAGIC))
            if header_magic != HEADER_MAGIC:
                # Might be an old file encrypted without our header
                # (plain pyAesCrypt .aes file) — fall back gracefully.
                warn(
                    "File header not recognised as filecrypt v2 format.\n"
                    "         Attempting legacy decryption (no salt header) …"
                )
                in_f.seek(0)
                salt = b""
                legacy = True
            else:
                salt_bytes = in_f.read(SALT_SIZE)
                if len(salt_bytes) != SALT_SIZE:
                    raise ValueError("Truncated header: could not read salt.")
                salt   = salt_bytes
                legacy = False

            key = derive_key(password, salt)
            vlog(f"Input:  {input_path}  ({input_path.stat().st_size:,} bytes)")
            vlog(f"Output: {output_path}")
            if not legacy:
                vlog(f"Salt:   {salt.hex()}")

            # Decrypt the payload
            # pyAesCrypt needs to know the *full* encrypted stream size.
            # For our format that is: total_file_size - header_size.
            # For legacy it is: total_file_size.
            total_size = input_path.stat().st_size
            payload_size = total_size if legacy else total_size - HEADER_SIZE

            if payload_size <= 0:
                raise ValueError("Encrypted payload is empty.")

            # Wrap the remaining bytes in a sized sub-stream so pyAesCrypt
            # gets the correct size without us having to copy data.
            payload_data = in_f.read()

        # Decrypt from an in-memory buffer (avoids TOCTOU on file size)
        payload_buf = io.BytesIO(payload_data)

        t0 = time.perf_counter()
        try:
            with open(tmp_path, "wb") as out_f:
                pyAesCrypt.decryptStream(
                    payload_buf, out_f, key, BUFFER_SIZE, len(payload_data)
                )
        except ValueError as exc:
            raise ValueError(
                "Decryption failed — wrong passphrase or corrupted file."
            ) from exc

        elapsed = time.perf_counter() - t0

        # Atomic rename
        if output_path.exists() and overwrite:
            output_path.unlink()
        tmp_path.rename(output_path)
        tmp_path = None  # prevent cleanup

        size_in  = input_path.stat().st_size
        size_out = output_path.stat().st_size
        ok(f"Decrypted  {input_path.name}  →  {output_path.name}")
        log(f"           {size_in:,} bytes  →  {size_out:,} bytes  in {elapsed:.3f}s")

    except Exception:
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise

# Secure shred

def shred_file(path: Path, passes: int = SHRED_PASSES) -> None:
    """
    Overwrite *path* with random bytes *passes* times, then delete it.

    NOTE: On copy-on-write filesystems (APFS, btrfs), some SSDs with
    wear-levelling, or network/cloud-backed storage, this cannot guarantee
    all copies of the data are erased. It is a best-effort measure.
    """
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if not path.is_file():
        raise ValueError(f"Not a regular file: {path}")

    size = path.stat().st_size
    warn(
        f"Shredding {path.name} ({size:,} bytes) with {passes} overwrite "
        f"pass{'es' if passes != 1 else ''} …"
    )
    warn("NOTE: shredding is best-effort on SSDs / CoW filesystems.")

    try:
        with open(path, "r+b") as f:
            for p in range(passes):
                f.seek(0)
                remaining = size
                while remaining > 0:
                    chunk = min(remaining, BUFFER_SIZE)
                    f.write(secrets.token_bytes(chunk))
                    remaining -= chunk
                f.flush()
                os.fsync(f.fileno())
                vlog(f"  Pass {p + 1}/{passes} complete.")
    except OSError as exc:
        raise OSError(f"Shred write failed: {exc}") from exc

    path.unlink()
    ok(f"Shredded and deleted: {path}")

# Output path resolution

def resolve_encrypt_output(input_path: Path, output_arg: str | None) -> Path:
    if output_arg:
        return Path(output_arg)
    return input_path.with_suffix(input_path.suffix + AES_EXTENSION)


def resolve_decrypt_output(input_path: Path, output_arg: str | None) -> Path:
    if output_arg:
        return Path(output_arg)
    name = input_path.name
    if name.endswith(AES_EXTENSION):
        return input_path.with_name(name[: -len(AES_EXTENSION)])
    # No .aes suffix — append ".decrypted" to avoid clobbering the source
    warn(
        f"Input file does not end with '{AES_EXTENSION}'. "
        f"Output will be saved as '<input>.decrypted'."
    )
    return input_path.with_suffix(input_path.suffix + ".decrypted")

# CLI argument parser

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=TOOL_NAME,
        description=bold("filecrypt — Secure AES-256 file encryption CLI"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
examples:
  {TOOL_NAME} encrypt secret.pdf
  {TOOL_NAME} encrypt secret.pdf --output safe/secret.pdf.aes
  {TOOL_NAME} decrypt secret.pdf.aes
  {TOOL_NAME} decrypt secret.pdf.aes --output recovered.pdf --overwrite
  {TOOL_NAME} shred   secret.pdf --passes 7

security notes:
  • AES-256-CBC via pyAesCrypt (AES Crypt v2 file format)
  • Key derivation: PBKDF2-HMAC-SHA256, {PBKDF2_ITERATIONS:,} iterations
  • Per-file random 32-byte salt stored in file header
  • Passwords are never echoed to the terminal
  • Temporary files are always cleaned up on failure
  • 'shred' is best-effort on SSDs and CoW filesystems (APFS, btrfs)

version: {VERSION}
""",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")

    verbosity = parser.add_mutually_exclusive_group()
    verbosity.add_argument("-v", "--verbose", action="store_true", help="Show detailed progress")
    verbosity.add_argument("-q", "--quiet",   action="store_true", help="Suppress all output except errors")

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    # encrypt
    enc = sub.add_parser(
        "encrypt", aliases=["enc", "e"],
        help="Encrypt a file",
        description="Encrypt FILE using AES-256. Output: FILE.aes",
    )
    enc.add_argument("file", metavar="FILE", help="File to encrypt")
    enc.add_argument("-o", "--output",    metavar="PATH", help="Custom output file path")
    enc.add_argument("--overwrite",       action="store_true", help="Overwrite existing output file")
    enc.add_argument("--password",        metavar="PASS",
                     help="Passphrase (NOT recommended — use interactive prompt instead)")

    # decrypt
    dec = sub.add_parser(
        "decrypt", aliases=["dec", "d"],
        help="Decrypt a file",
        description="Decrypt FILE.aes using AES-256.",
    )
    dec.add_argument("file", metavar="FILE", help="Encrypted .aes file to decrypt")
    dec.add_argument("-o", "--output",    metavar="PATH", help="Custom output file path")
    dec.add_argument("--overwrite",       action="store_true", help="Overwrite existing output file")
    dec.add_argument("--password",        metavar="PASS",
                     help="Passphrase (NOT recommended — use interactive prompt instead)")

    # shred
    shd = sub.add_parser(
        "shred", aliases=["wipe", "s"],
        help="Securely overwrite and delete a file",
        description="Overwrite FILE with random data multiple times, then delete it.",
    )
    shd.add_argument("file", metavar="FILE", help="File to shred")
    shd.add_argument(
        "--passes", metavar="N", type=int, default=SHRED_PASSES,
        help=f"Number of overwrite passes (default: {SHRED_PASSES})"
    )
    shd.add_argument("--yes", "-y", action="store_true",
                     help="Skip confirmation prompt")

    return parser

# Command handlers

def cmd_encrypt(args: argparse.Namespace) -> int:
    input_path  = Path(args.file).resolve()
    output_path = resolve_encrypt_output(input_path, args.output)

    # Warn if --password used (visible in process list)
    if args.password:
        warn("--password flag used: passphrase may be visible in shell history / process list.")
        password = args.password
    else:
        try:
            password = prompt_password_encrypt()
        except (KeyboardInterrupt, EOFError):
            print()
            err("Interrupted.")
            return 1

    try:
        encrypt_file(input_path, output_path, password, overwrite=args.overwrite)
    except FileNotFoundError as exc:
        err(str(exc))
        return 2
    except FileExistsError as exc:
        err(str(exc))
        return 3
    except ValueError as exc:
        err(str(exc))
        return 4
    except PermissionError as exc:
        err(f"Permission denied: {exc}")
        return 5
    except OSError as exc:
        err(f"I/O error: {exc}")
        return 6
    except Exception as exc:
        err(f"Unexpected error: {exc}")
        if _verbose:
            import traceback; traceback.print_exc()
        return 99
    finally:
        # Best-effort: zero out password in memory
        try:
            password = "\x00" * len(password)
            del password
        except Exception:
            pass

    return 0


def cmd_decrypt(args: argparse.Namespace) -> int:
    input_path  = Path(args.file).resolve()
    output_path = resolve_decrypt_output(input_path, args.output)

    if args.password:
        warn("--password flag used: passphrase may be visible in shell history / process list.")
        password = args.password
    else:
        try:
            password = prompt_password_decrypt()
        except (KeyboardInterrupt, EOFError):
            print()
            err("Interrupted.")
            return 1

    try:
        decrypt_file(input_path, output_path, password, overwrite=args.overwrite)
    except FileNotFoundError as exc:
        err(str(exc))
        return 2
    except FileExistsError as exc:
        err(str(exc))
        return 3
    except ValueError as exc:
        err(str(exc))
        return 4
    except PermissionError as exc:
        err(f"Permission denied: {exc}")
        return 5
    except OSError as exc:
        err(f"I/O error: {exc}")
        return 6
    except Exception as exc:
        err(f"Unexpected error: {exc}")
        if _verbose:
            import traceback; traceback.print_exc()
        return 99
    finally:
        try:
            password = "\x00" * len(password)
            del password
        except Exception:
            pass

    return 0


def cmd_shred(args: argparse.Namespace) -> int:
    path = Path(args.file).resolve()

    if not args.yes:
        try:
            confirm = input(
                yellow(f"[WARN]  This will permanently destroy: {path}\n")
                + "        Type 'yes' to confirm: "
            )
        except (KeyboardInterrupt, EOFError):
            print()
            log("Aborted.")
            return 0
        if confirm.strip().lower() != "yes":
            log("Aborted.")
            return 0

    passes = max(1, args.passes)

    try:
        shred_file(path, passes=passes)
    except FileNotFoundError as exc:
        err(str(exc))
        return 2
    except ValueError as exc:
        err(str(exc))
        return 4
    except PermissionError as exc:
        err(f"Permission denied: {exc}")
        return 5
    except OSError as exc:
        err(f"I/O error: {exc}")
        return 6
    except Exception as exc:
        err(f"Unexpected error: {exc}")
        if _verbose:
            import traceback; traceback.print_exc()
        return 99

    return 0


def main(argv: list[str] | None = None) -> int:
    global _verbose, _quiet

    parser = build_parser()
    args   = parser.parse_args(argv)

    _verbose = args.verbose
    _quiet   = args.quiet

    # Normalise aliases to canonical command names
    cmd = args.command
    if cmd in ("enc", "e"):
        cmd = "encrypt"
    elif cmd in ("dec", "d"):
        cmd = "decrypt"
    elif cmd in ("wipe", "s"):
        cmd = "shred"

    dispatch = {
        "encrypt": cmd_encrypt,
        "decrypt": cmd_decrypt,
        "shred":   cmd_shred,
    }

    return dispatch[cmd](args)


if __name__ == "__main__":
    sys.exit(main())
