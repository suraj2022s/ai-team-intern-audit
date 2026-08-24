#!/usr/bin/env python3
"""
corrected_analysis.py -- A3: corrected cross-language tokenizer comparison.

Fixes applied relative to the original fertility.py (see A2_audit.md):
  - word split uses `str.split()` (any whitespace run), not `split(" ")`
  - micro-averaging (total_tokens / total_denominator), not mean-of-ratios
  - no `.lower()` before encoding -- casing is part of the text, folding it
    is not a neutral operation across scripts (A2, bug 3)

Runs >=2 tokenizers (one Indic-aware) x >=4 denominators on the A1 corpus
(FLORES-200 devtest, 1012 parallel sentences x 6 languages):

  tokenizers: gpt2 (tiktoken), google/muril-base-cased (Indic-aware WordPiece),
              facebook/nllb-200-distilled-600M (multilingual SentencePiece,
              trained across all 200 languages incl. every language here)
  denominators: whitespace word, UTF-8 byte, extended grapheme cluster,
                parallel sentence

Writes partA/results/a3_full_table.csv and prints a summary to stdout.
"""

import csv
import glob
import os

import regex  # for \X extended grapheme clusters -- stdlib `re` can't do this
import tiktoken
from transformers import AutoTokenizer

HERE = os.path.dirname(__file__)
CORPUS_DIR = os.path.join(HERE, "corpus", "flores200")
RESULTS_CSV = os.path.join(HERE, "results", "a3_full_table.csv")


def load_tokenizers():
    gpt2_enc = tiktoken.get_encoding("gpt2")
    muril = AutoTokenizer.from_pretrained("google/muril-base-cased")
    nllb = AutoTokenizer.from_pretrained("facebook/nllb-200-distilled-600M")
    return {
        "gpt2": lambda s: gpt2_enc.encode(s),
        "muril": lambda s: muril.encode(s, add_special_tokens=False),
        "nllb-200-distilled-600M": lambda s: nllb.encode(s, add_special_tokens=False),
    }


def read_lines(path):
    with open(path, encoding="utf-8") as f:
        return [ln.strip() for ln in f if ln.strip()]


def grapheme_count(s):
    return len(regex.findall(r"\X", s))


def word_count(s):
    return len(s.split())


def byte_count(s):
    return len(s.encode("utf-8"))


def main():
    files = sorted(glob.glob(os.path.join(CORPUS_DIR, "*.txt")))
    if not files:
        print("(FLORES corpus not found -- run partA/corpus/build_corpus.py first)")
        return
    langs = {os.path.splitext(os.path.basename(p))[0]: read_lines(p) for p in files}
    n_sentences = len(next(iter(langs.values())))
    assert all(len(v) == n_sentences for v in langs.values()), "corpora not parallel!"

    print("FORMULA (4 denominators, same tokens numerator each time):")
    print("  tok_per_word     = total_tokens / total_words             (words = str.split())")
    print("  tok_per_byte     = total_tokens / total_bytes             (bytes = s.encode('utf-8'))")
    print("  tok_per_grapheme = total_tokens / total_grapheme_clusters (via regex r'\\X')")
    print("  tok_per_sentence = total_tokens / num_parallel_sentences")
    print()
    print("Loading tokenizers (gpt2, MuRIL, NLLB-200)...")
    tokenizers = load_tokenizers()

    rows = []
    for tok_name, encode in tokenizers.items():
        print(f"\nEncoding with {tok_name}...")
        for lang, lines in langs.items():
            total_tokens = 0
            total_words = 0
            total_bytes = 0
            total_graphemes = 0
            for line in lines:
                n_tok = len(encode(line))
                total_tokens += n_tok
                total_words += word_count(line)
                total_bytes += byte_count(line)
                total_graphemes += grapheme_count(line)

            row = {
                "tokenizer": tok_name,
                "lang": lang,
                "sentences": n_sentences,
                "total_tokens": total_tokens,
                "tok_per_word": total_tokens / total_words,
                "tok_per_byte": total_tokens / total_bytes,
                "tok_per_grapheme": total_tokens / total_graphemes,
                "tok_per_sentence": total_tokens / n_sentences,
            }
            rows.append(row)
            print(f"  {lang}: tok/word={row['tok_per_word']:.3f}  "
                  f"tok/byte={row['tok_per_byte']:.4f}  "
                  f"tok/grapheme={row['tok_per_grapheme']:.3f}  "
                  f"tok/sentence={row['tok_per_sentence']:.2f}")

    os.makedirs(os.path.dirname(RESULTS_CSV), exist_ok=True)
    with open(RESULTS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nWrote {RESULTS_CSV}")

    # Summary: hin/eng and each-Dravidian/eng ratio under every (tokenizer, denominator)
    print("\n" + "=" * 78)
    print("SUMMARY: ratio to eng, per tokenizer x denominator")
    print("=" * 78)
    by_key = {(r["tokenizer"], r["lang"]): r for r in rows}
    denominators = ["tok_per_word", "tok_per_byte", "tok_per_grapheme", "tok_per_sentence"]
    for tok_name in tokenizers:
        print(f"\n-- {tok_name} --")
        header = f"{'lang':<6}" + "".join(f"{d:>18}" for d in denominators)
        print(header)
        eng_row = by_key[(tok_name, "eng")]
        for lang in langs:
            row = by_key[(tok_name, lang)]
            cells = "".join(f"{row[d]/eng_row[d]:>18.3f}" for d in denominators)
            print(f"{lang:<6}{cells}")


if __name__ == "__main__":
    main()
