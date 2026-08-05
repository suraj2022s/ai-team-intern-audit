#!/usr/bin/env python3
"""
nonbug_random_seed.py -- fertility.py has, at module scope:

    import random
    ...
    random.seed(1337)  # reproducibility

This LOOKS like it should matter (a seed, commented "reproducibility" --
implies something non-deterministic is happening that the seed pins down).
This script checks whether it actually does anything by grepping the file
for other uses of `random`, then running the original script's core logic
with and without the seed line and diffing the output byte-for-byte.

If `random` is never called anywhere else, the seed call is inert: seeding
an RNG that's never drawn from cannot change any output. That would make
this the "looks suspicious but is actually fine" item -- and per the
assignment's evidence rule, we don't get to just assert that; we have to
show it.
"""

import os
import re
import subprocess
import sys

HERE = os.path.dirname(__file__)
ORIGINAL_SCRIPT = os.path.join(HERE, "..", "original", "fertility.py")
CORPUS_ENG = os.path.join(HERE, "..", "original", "corpus_sample", "eng_sample.txt")
CORPUS_HIN = os.path.join(HERE, "..", "original", "corpus_sample", "hin_sample.txt")
PATCHED_SCRIPT = os.path.join(HERE, "_fertility_no_seed.py")


def main():
    print("Step 1: grep the original script for every use of `random`")
    with open(ORIGINAL_SCRIPT, encoding="utf-8") as f:
        src = f.read()
    uses = [(i + 1, line) for i, line in enumerate(src.splitlines()) if "random" in line]
    for lineno, line in uses:
        print(f"  line {lineno}: {line}")
    calls_other_than_seed = [
        (n, l) for n, l in uses if "random." in l and "random.seed" not in l and "import random" not in l
    ]
    print(f"\n  -> {len(uses)} lines mention `random`; "
          f"{len(calls_other_than_seed)} of those call anything on `random` other than .seed(...)")

    print("\nStep 2: run original vs. a copy with the seed line deleted, diff output")
    with open(ORIGINAL_SCRIPT, encoding="utf-8") as f:
        lines = f.readlines()
    patched = [l for l in lines if "random.seed" not in l]
    with open(PATCHED_SCRIPT, "w", encoding="utf-8") as f:
        f.writelines(patched)

    cmd_base = [
        sys.executable, "-X", "utf8",
        "--", "SCRIPT",
        "--corpus", f"eng={CORPUS_ENG}",
        "--corpus", f"hin={CORPUS_HIN}",
        "--tokenizer", "gpt2",
    ]
    env = dict(os.environ, PYTHONIOENCODING="utf-8")

    def run(script_path):
        cmd = [sys.executable, script_path,
               "--corpus", f"eng={CORPUS_ENG}",
               "--corpus", f"hin={CORPUS_HIN}",
               "--tokenizer", "gpt2"]
        return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", env=env)

    out_original = run(ORIGINAL_SCRIPT)
    out_patched = run(PATCHED_SCRIPT)

    print(f"  original stdout length: {len(out_original.stdout)} chars")
    print(f"  patched  stdout length: {len(out_patched.stdout)} chars")
    identical = out_original.stdout == out_patched.stdout
    print(f"  byte-for-byte identical: {identical}")

    if not identical:
        print("  DIFF FOUND (unexpected -- would mean the seed is NOT inert):")
        import difflib
        diff = difflib.unified_diff(
            out_original.stdout.splitlines(), out_patched.stdout.splitlines(),
            fromfile="original (with seed)", tofile="patched (no seed)", lineterm="",
        )
        print("\n".join(diff))
    else:
        print("\nConclusion: removing `random.seed(1337)` changes NOTHING about the")
        print("output. Combined with step 1 (random is imported and seeded but never")
        print("otherwise called), this confirms the seed line is inert -- suspicious-")
        print("looking, but not a bug. (It IS dead code / a red herring for a reader")
        print("auditing the script, which is presumably the point.)")

    os.remove(PATCHED_SCRIPT)


if __name__ == "__main__":
    main()
