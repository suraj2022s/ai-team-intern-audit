#!/usr/bin/env python3
"""
bug6_char_vs_byte.py -- isolate fertility.py's `chars = len(line)` (line 63)
as the denominator for the tok/char metric: Python's len() on a str counts
Unicode codepoints, not UTF-8 bytes. Devanagari codepoints (U+0900-097F)
encode as 3 bytes each in UTF-8; ASCII encodes 1 byte each. This checks
whether REPORT_v0's tok/char column -- and its "7.0x worse per character"
claim (REPORT_v0.md line 19-20), computed from exactly this line of
fertility.py -- changes when the denominator is switched from codepoint
count to UTF-8 byte count, holding tokenizer, text, lowercasing, and NFC
normalization identical to the original script.

Runs on the ORIGINAL corpus_sample/ (the exact files REPORT_v0 used) so the
"before" number reproduces REPORT_v0's reported 0.226 / 1.579, then on the
FLORES-200 corpus for a larger-scale check.
"""

import glob
import os
import unicodedata
import tiktoken

enc = tiktoken.get_encoding("gpt2")


def read_lines(path):
    lines = []
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            line = unicodedata.normalize("NFC", line)
            lines.append(line)
    return lines


def tok_per_char(lines, byte_mode):
    per_line = []
    for line in lines:
        line = line.lower()
        tokens = enc.encode(line)
        chars = len(line.encode("utf-8")) if byte_mode else len(line)
        per_line.append(len(tokens) / chars)
    return sum(per_line) / len(per_line)


def avg_bytes_per_char(lines):
    lowered = [l.lower() for l in lines]
    total_chars = sum(len(l) for l in lowered)
    total_bytes = sum(len(l.encode("utf-8")) for l in lowered)
    return total_bytes / total_chars


def report(label, files_by_lang):
    print(f"-- {label} --")
    print(f"{'lang':<6}{'tok/char (len)':>16}{'tok/byte (utf8)':>18}{'avg bytes/char':>16}")
    results = {}
    for lang, path in files_by_lang.items():
        lines = read_lines(path)
        tpc_char = tok_per_char(lines, byte_mode=False)
        tpc_byte = tok_per_char(lines, byte_mode=True)
        bpc = avg_bytes_per_char(lines)
        results[lang] = (tpc_char, tpc_byte)
        print(f"{lang:<6}{tpc_char:>16.3f}{tpc_byte:>18.3f}{bpc:>16.3f}")
    if "eng" in results and "hin" in results:
        ratio_char = results["hin"][0] / results["eng"][0]
        ratio_byte = results["hin"][1] / results["eng"][1]
        print(f"\nhin/eng ratio using tok/char (len()):         {ratio_char:.3f}x")
        print(f"hin/eng ratio using tok/byte (utf-8 encode):  {ratio_byte:.3f}x")
        print("REPORT_v0 claimed (corpus_sample, gpt2): 1.579 / 0.226 = 7.0x worse per character\n")
    return results


def main():
    here = os.path.dirname(__file__)

    orig_dir = os.path.join(here, "..", "original", "corpus_sample")
    orig_files = {
        "eng": os.path.join(orig_dir, "eng_sample.txt"),
        "hin": os.path.join(orig_dir, "hin_sample.txt"),
    }
    report("REPORT_v0's exact corpus_sample (10 lines/lang)", orig_files)

    flores_dir = os.path.join(here, "..", "corpus", "flores200")
    flores_files = sorted(glob.glob(os.path.join(flores_dir, "*.txt")))
    if flores_files:
        flores_by_lang = {os.path.splitext(os.path.basename(p))[0]: p for p in flores_files}
        report("FLORES-200 devtest (1012 lines/lang)", flores_by_lang)
    else:
        print("(FLORES corpus not found -- run partA/corpus/build_corpus.py first)")


if __name__ == "__main__":
    main()
