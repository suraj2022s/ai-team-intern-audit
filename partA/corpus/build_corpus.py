#!/usr/bin/env python3
"""
build_corpus.py -- fetch FLORES-200 devtest and extract a parallel
6-language eval corpus for the tokenizer audit (A1).

Why the public tarball and not `datasets.load_dataset`: as of 2026-08-04,
both `facebook/flores` and `openlanguagedata/flores_plus` on the HF Hub
are gated (require an authenticated HF account), and the `Muennighoff/flores200`
mirror uses a loading script format the installed `datasets==5.0.1` refuses
to run. The original FBAI-hosted tarball is public, unauthenticated, and is
the same underlying release. See NOTEBOOK.md for the dead ends that led here.

Usage:
    python build_corpus.py
Downloads to ./_download/flores200_dataset.tar.gz (cached if already present),
extracts devtest files for the languages below, and writes one plain-text
file per language (one sentence per line, parallel across files) into
./flores200/.
"""

import hashlib
import io
import os
import tarfile
import urllib.request

URL = "https://dl.fbaipublicfiles.com/nllb/flores200_dataset.tar.gz"
DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "_download")
TARBALL_PATH = os.path.join(DOWNLOAD_DIR, "flores200_dataset.tar.gz")
OUT_DIR = os.path.join(os.path.dirname(__file__), "flores200")

# FLORES-200 language codes for our 6 languages.
LANGS = {
    "eng": "eng_Latn",
    "hin": "hin_Deva",
    "kan": "kan_Knda",
    "tam": "tam_Taml",
    "tel": "tel_Telu",
    "mal": "mal_Mlym",
}

SPLIT = "devtest"  # devtest = 1012 sentences/lang; dev = 997 sentences/lang


def download():
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    if os.path.exists(TARBALL_PATH):
        print(f"[cache] {TARBALL_PATH} already present, skipping download")
        return
    print(f"[download] {URL} -> {TARBALL_PATH}")
    urllib.request.urlretrieve(URL, TARBALL_PATH)
    size = os.path.getsize(TARBALL_PATH)
    print(f"[download] done, {size} bytes")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def extract():
    os.makedirs(OUT_DIR, exist_ok=True)
    with tarfile.open(TARBALL_PATH, "r:gz") as tar:
        names = tar.getnames()
        for short, code in LANGS.items():
            # inside the tarball: ./flores200_dataset/devtest/{code}.devtest
            suffix = f"flores200_dataset/{SPLIT}/{code}.{SPLIT}"
            matches = [n for n in names if n.endswith(suffix)]
            if not matches:
                raise FileNotFoundError(
                    f"expected a member ending in {suffix!r}, none found; "
                    f"nearby names: {[n for n in names if code in n][:5]}"
                )
            member = tar.getmember(matches[0])
            f = tar.extractfile(member)
            raw = f.read().decode("utf-8")
            lines = [ln for ln in raw.split("\n") if ln.strip() != ""]
            out_path = os.path.join(OUT_DIR, f"{short}.txt")
            with open(out_path, "w", encoding="utf-8", newline="\n") as out:
                out.write("\n".join(lines) + "\n")
            print(f"[extract] {short} ({code}): {len(lines)} lines -> {out_path}")


def main():
    download()
    print(f"[checksum] sha256={sha256(TARBALL_PATH)}")
    extract()

    counts = {}
    for short in LANGS:
        with open(os.path.join(OUT_DIR, f"{short}.txt"), encoding="utf-8") as f:
            counts[short] = sum(1 for _ in f)
    print("\nline counts:", counts)
    assert len(set(counts.values())) == 1, "corpora are not parallel (line count mismatch)!"
    print(f"OK: all {len(LANGS)} languages have {list(counts.values())[0]} parallel lines.")


if __name__ == "__main__":
    main()
