import argparse
import gzip
import io
import json
import os
import sys
import zipfile
from pathlib import Path


def _looks_like_zip(data: bytes) -> bool:
    return data[:4] == b"PK\x03\x04"


def _looks_like_gzip(data: bytes) -> bool:
    return data[:2] == b"\x1f\x8b"


def _looks_like_json(data: bytes) -> bool:
    head = data.lstrip()[:1]
    return head in (b"{", b"[")


def _load_wasm(wasm_path: Path):
    try:
        from wasmtime import Store, Module, Instance, Memory, MemoryType, Limits
    except Exception as exc:
        raise RuntimeError(
            "wasmtime is required. Install with: python -m pip install wasmtime"
        ) from exc

    store = Store()
    module = Module.from_file(store.engine, str(wasm_path))
    memory = Memory(store, MemoryType(Limits(256, 256)))
    instance = Instance(store, module, [memory])
    exports = instance.exports(store)

    ctx = {
        "store": store,
        "memory": memory,
        "ofb": exports["a"],
        "func_d": exports["d"],
        "func_e": exports["e"],
        "func_f": exports["f"],
    }

    ctx["func_e"](store, 0, 0, 256)
    ctx["func_f"](store, 0, 0, 256)
    ctx["func_d"](store, 0, 0, 128)

    return ctx


def _ofb_decrypt(data: bytes, ctx) -> bytes:
    import ctypes

    store = ctx["store"]
    memory = ctx["memory"]
    ofb = ctx["ofb"]
    func_d = ctx["func_d"]

    block_ptr = 1 << 14
    ptr = memory.data_ptr(store)
    base_addr = ctypes.addressof(ptr.contents)
    byte_len = memory.data_len(store)
    array_type = ctypes.c_ubyte * byte_len
    mem_view = array_type.from_address(base_addr)

    orig_len = len(data)
    pad = (16 - (orig_len % 16)) % 16
    if pad == 0:
        pad = 16
    padded = data + b"\x00" * pad

    mem_view[block_ptr : block_ptr + len(padded)] = padded
    ofb(store, block_ptr, len(padded))
    func_d(store, 0, 0, 128)
    out = bytes(mem_view[block_ptr : block_ptr + len(padded)])[:orig_len]
    return out


def _write_file(path: Path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _extract_zip(data: bytes, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        zf.extractall(out_dir)
    return out_dir


def main():
    parser = argparse.ArgumentParser(
        description="Decrypt .sgs files (Sanguosha web) using resc wasm."
    )
    parser.add_argument("input", help="Path to .sgs file")
    parser.add_argument(
        "--wasm",
        default="resc",
        help="Path to resc wasm file (default: ./resc)",
    )
    parser.add_argument(
        "-o",
        "--out",
        default="",
        help="Output file path (default: <input>.dec or <input>.unzipped)",
    )
    parser.add_argument(
        "--no-gunzip",
        action="store_true",
        help="Do not auto-gunzip after decrypt",
    )
    parser.add_argument(
        "--extract-zip",
        action="store_true",
        help="If output is ZIP, extract to <input>_zip/",
    )
    parser.add_argument(
        "--keep-intermediate",
        action="store_true",
        help="Write intermediate decrypt files",
    )
    args = parser.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        print(f"Input not found: {in_path}", file=sys.stderr)
        return 2

    wasm_path = Path(args.wasm)
    if not wasm_path.exists():
        print(f"WASM not found: {wasm_path}", file=sys.stderr)
        return 2

    raw = in_path.read_bytes()

    # If already readable
    if _looks_like_zip(raw) or _looks_like_gzip(raw) or _looks_like_json(raw):
        candidate = raw
        stage = "plain"
    else:
        ctx = _load_wasm(wasm_path)
        dec1 = _ofb_decrypt(raw, ctx)
        if _looks_like_zip(dec1) or _looks_like_gzip(dec1) or _looks_like_json(dec1):
            candidate = dec1
            stage = "ofb"
        else:
            dec2 = _ofb_decrypt(dec1, ctx)
            candidate = dec2
            stage = "double-ofb"
            if args.keep_intermediate:
                _write_file(in_path.with_suffix(in_path.suffix + ".dec1"), dec1)
                _write_file(in_path.with_suffix(in_path.suffix + ".dec2"), dec2)

    # Optionally gunzip
    final = candidate
    gunzipped = False
    if _looks_like_gzip(final) and not args.no_gunzip:
        final = gzip.decompress(final)
        gunzipped = True

    # Determine output path
    if args.out:
        out_path = Path(args.out)
    else:
        suffix = ".unzipped" if gunzipped else ".dec"
        out_path = in_path.with_suffix(in_path.suffix + suffix)

    _write_file(out_path, final)
    print(f"stage: {stage}")
    print(f"output: {out_path} ({len(final)} bytes)")

    # Optional zip extraction
    if _looks_like_zip(final) and args.extract_zip:
        out_dir = in_path.with_suffix(in_path.suffix + "_zip")
        _extract_zip(final, out_dir)
        print(f"zip extracted to: {out_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
