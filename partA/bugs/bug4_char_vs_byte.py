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

Also computes both macro-averaging (fertility.py's actual method, mean of
per-line ratios) AND micro-averaging (sum/sum, the bug-2 fix) for both
char and byte denominators, shown separately -- so the char-vs-byte effect
and the macro-vs-micro effect can each be isolated and quantified on their
own, instead of only ever being seen combined.
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


def tok_per_char_macro(lines, byte_mode):
    """Mean of per-line ratios -- fertility.py's actual method. Kept
    deliberately, not "fixed", so this reproduces REPORT_v0's exact
    baseline number before anything else changes."""
    per_line = []
    for line in lines:
        line = line.lower()
        tokens = enc.encode(line)
        chars = len(line.encode("utf-8")) if byte_mode else len(line)
        per_line.append(len(tokens) / chars)
    return sum(per_line) / len(per_line)


def tok_per_char_micro(lines, byte_mode):
    """sum(tokens) / sum(chars) -- the micro-averaging fix from bug 2,
    applied here too so the char-vs-byte effect and the macro-vs-micro
    effect can be seen separately instead of conflated."""
    total_tokens = 0
    total_chars = 0
    for line in lines:
        line = line.lower()
        tokens = enc.encode(line)
        chars = len(line.encode("utf-8")) if byte_mode else len(line)
        total_tokens += len(tokens)
        total_chars += chars
    return total_tokens / total_chars


def avg_bytes_per_char(lines):
    lowered = [l.lower() for l in lines]
    total_chars = sum(len(l) for l in lowered)
    total_bytes = sum(len(l.encode("utf-8")) for l in lowered)
    return total_bytes / total_chars


def report(label, files_by_lang):
    print(f"-- {label} --")
    print(f"{'lang':<6}{'char,macro':>12}{'char,micro':>12}{'byte,macro':>12}{'byte,micro':>12}{'bytes/char':>12}")
    results = {}
    for lang, path in files_by_lang.items():
        lines = read_lines(path)
        char_macro = tok_per_char_macro(lines, byte_mode=False)
        char_micro = tok_per_char_micro(lines, byte_mode=False)
        byte_macro = tok_per_char_macro(lines, byte_mode=True)
        byte_micro = tok_per_char_micro(lines, byte_mode=True)
        bpc = avg_bytes_per_char(lines)
        results[lang] = (char_macro, char_micro, byte_macro, byte_micro)
        print(f"{lang:<6}{char_macro:>12.3f}{char_micro:>12.3f}{byte_macro:>12.3f}{byte_micro:>12.3f}{bpc:>12.3f}")

    if "eng" in results and "hin" in results:
        eng, hin = results["eng"], results["hin"]
        labels = ["char, macro (fertility.py's actual method)",
                  "char, micro (averaging fix only)",
                  "byte, macro (byte fix only)",
                  "byte, micro (both fixes)"]
        print()
        for i, label_i in enumerate(labels):
            ratio = hin[i] / eng[i]
            print(f"hin/eng ratio -- {label_i}: {ratio:.3f}x")
        print("REPORT_v0 claimed (corpus_sample, gpt2): 1.579 / 0.226 = 7.0x worse per character")
        ratio_char_macro = hin[0] / eng[0]
        ratio_char_micro = hin[1] / eng[1]
        ratio_byte_macro = hin[2] / eng[2]
        print(f"\nIsolating each fix's own contribution to the hin/eng ratio, one variable at a time:")
        print(f"  macro/micro alone (char,macro -> char,micro): "
              f"{ratio_char_macro:.3f}x -> {ratio_char_micro:.3f}x "
              f"({100*(ratio_char_micro/ratio_char_macro-1):+.2f}%) -- small")
        print(f"  char/byte alone   (char,macro -> byte,macro): "
              f"{ratio_char_macro:.3f}x -> {ratio_byte_macro:.3f}x "
              f"({100*(ratio_byte_macro/ratio_char_macro-1):+.2f}%) -- this is the real driver")
        print()
    return results


def main():
    here = os.path.dirname(__file__)
    print("FORMULA:")
    print("  tok/char (bug, fertility.py) = tokens / len(line)                  -- Unicode codepoints")
    print("  tok/byte (fix)               = tokens / len(line.encode('utf-8'))  -- actual bytes")
    print()

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
