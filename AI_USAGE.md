# AI_USAGE.md

## Disclosure up front

This submission was produced using Claude as an advanced pair-programmer and drafting assistant. While I drove the architectural decisions, identified the logical flaws to investigate, and defined the strict evidence requirements, I relied heavily on Claude to write the boilerplate Python scripts, execute the data extraction, and structure the markdown write-ups.

The assignment explicitly states to not pretend I didn't use AI, so I am being radically transparent here: Claude acted as the hands on the keyboard, but I acted as the reviewer. I treated every AI-generated claim, script, and markdown table as untrusted until I could personally verify the math and logic behind it (which led to catching several AI hallucinations and oversights, detailed below). I am prepared to re-derive these numbers and modify this code live during the defense.

## Where AI helped

Code Generation & Formatting: 
Claude wrote the vast majority of the Python scripts (such as the corpus-download script and the fertility.py bug isolation scripts) and handled the tedious markdown table formatting for the writeups.

Recovering from real dead ends without hand-waving them away:
 Both facebook/flores and openlanguagedata/flores_plus turned out to be gated on Hugging Face, and Muennighoff/flores200 used a deprecated dataset-script format the installed datasets version refuses to run. Rather than quietly picking a different corpus, Claude helped me fall back to the original public tarball and document why in NOTEBOOK.md—this is a case where the initial plan didn't work and the fix is visible, not papered over.

Choosing tokenizers/denominators that turned out to matter a lot: The decision to test MuRIL and NLLB-200 (Indic-aware) against gpt2 was an AI judgment call based on general knowledge of what those tokenizers are for—it happened to surface the single biggest finding in the submission (that the report's ×5.89 "property of the script" claim is actually a tokenizer-choice artifact).
## Where AI's first guess was wrong, and got corrected by actually running the code

This is the part of the ground rules worth being specific about — not "AI
made things up," but "AI had a plausible-sounding hypothesis that measurement
overturned," which the notebook captures in real time rather than after the
fact:

1. **Bug 3 (lowercasing) — wrong predicted direction.** The hypothesis was
   that lowercasing would make English look artificially *better*
   (fewer tokens), widening the reported Hindi/English gap. The actual
   measurement showed the opposite: lowercasing *increases* English
   fertility by 3.51%, shrinking the reported ratio. The mechanism guess
   (asymmetric effect on case-sensitive vs. case-less scripts) was right;
   the sign of the effect was not, and there was no way to know that
   without running it.
2. **Flaw 4 (word denominator) — wrong predicted direction.** The
   hypothesis going in was that switching to a meaning-constant denominator
   (tokens/parallel-sentence) would shrink the alarming hin/eng multiplier,
   on the assumption that word-based counting was inflating it. Measured
   result: tokens/sentence gives 7.413x, *larger* than tokens/word's
   6.331x — the "corrected" metric made the picture look worse, not
   better. This directly changed what the A4 memo could honestly claim;
   an earlier draft assumption ("the true multiplier is smaller than
   reported") had to be discarded once the number came back the other way.

Both of these are logged in `NOTEBOOK.md` as they happened, including the
wrong initial guess, not smoothed over in the final writeups. If asked in
the defense "did you expect this result," the honest answer for these two
specific items is no — and that's exactly the kind of thing this document
is supposed to surface.

## Where AI's contribution needs the most scrutiny before defending it

- **Part C (the decision memo)** is pure judgment/reasoning with no
  code to check it against — the arithmetic (data volume, training time,
  reviewer throughput) is order-of-magnitude estimation with stated
  assumptions, not measured fact like Parts A and B. It's the part of this
  submission most worth personally re-deriving and stress-testing before
  the defense, since "why did you pick (b) over (a) or (c)" is an easy
  counterfactual to ask and there's no script to fall back on.
- **The B2 mechanism and B4 recommendation** reason from the given CSV
  columns to a plausible serving-engine explanation (KV-cache exhaustion →
  preemption → recompute) that fits the data well but was not verified
  against an actual running serving stack — it's the most likely reading
  of `preempted_seqs`/`kv_cache_util`/`e2e_ms_p95` moving together, not a
  confirmed root cause from production telemetry.
- **The tokenizer choices in A3** (MuRIL, NLLB-200-distilled-600M) reflect
  what these models are commonly known for; the assistant did not verify
  training-data composition claims against primary sources (e.g. the MuRIL
  or NLLB papers) beyond what's implied by their public model cards, so
  the "Indic-aware" framing rests on general knowledge rather than a
  paper citation checked in this session.

## What was not done

No number in `partA/results/`, `partB/`, or any writeup was hand-typed
without a script producing it first — every claimed figure traces to a
command that's still in the repo and was actually run (not just written to
look plausible). That was a deliberate choice given the assignment's
"fabricated evidence = automatic fail" rule, and it's the one thing worth
double-checking hardest in review: re-run the scripts, don't just trust the
tables.
