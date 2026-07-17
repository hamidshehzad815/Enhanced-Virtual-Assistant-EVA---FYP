"""
EXPERIMENT (branch: experiment/gemini-clf1)

Head-to-head: Gemini vs CLF1 on input-type classification, on the same inputs.

Run:
    # .env needs GEMINI_API_KEY and USE_GEMINI_CLF1=true
    python Eva_AI_Server/testModels/test_gemini_clf1.py

Prints, per input: the expected label, what CLF1 said (+ its confidence), what
Gemini said, and the text Gemini cleaned it to. Then accuracy for each, and the
average Gemini latency — because latency is the whole argument against putting
Gemini on the front of every request.

The cases below are the real failures collected during testing, not templates.
"""
import sys
import time
from pathlib import Path

AI_SERVER_DIR = Path(__file__).resolve().parent.parent
if str(AI_SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(AI_SERVER_DIR))

from pipeline.classifier1 import classifier1  # noqa: E402
from pipeline.gemini_classifier import gemini_input_classifier  # noqa: E402

# (message, expected_label)
CASES = [
    # --- known CLF1 failures -------------------------------------------------
    ("how to add a roadmap", "help"),            # CLF1: out_of_scope @ 0.913
    ("need help!", "help"),                      # CLF1: general @ 0.546
    ("hi eva, what u can do?", "help"),          # CLF1: general @ 0.990
    ("what are the quite horus", "help"),        # CLF1: general (typo'd)
    # --- help phrasings ------------------------------------------------------
    ("where do i start", "help"),
    ("guide me please", "help"),
    ("teach me how to use", "help"),
    ("how i delete a task", "help"),
    ("how i can increase the session?", "help"),
    ("what languages you support", "help"),
    ("how to create a roadmap", "help"),
    ("how i can update the roadmap schedule?", "help"),
    # --- commands ------------------------------------------------------------
    ("add study block on 17july 8am", "command"),
    ("create python basics road map from moday", "command"),
    ("delete physics exam on monday", "command"),
    ("show my tasks tomorrow", "command"),
    ("update math exam to 5pm", "command"),
    ("delete a task", "command"),
    ("when am i most productive", "command"),
    # --- confirmation --------------------------------------------------------
    ("yes", "confirmation"),
    ("don't do it", "confirmation"),             # must NOT read as yes
    ("cancel", "confirmation"),
    # --- general -------------------------------------------------------------
    ("how are you?", "general"),
    ("what's going on", "general"),
    ("thanks", "general"),
    # --- out of scope --------------------------------------------------------
    ("order a pizza", "out_of_scope"),
    ("what's the weather tomorrow", "out_of_scope"),
    ("how do i cook pasta", "out_of_scope"),
    # --- multiple command ----------------------------------------------------
    ("add math exam on monday and delete physics lab", "multiple_command"),
]


def main() -> None:
    classifier1.load()

    print(f"Gemini CLF1 enabled : {gemini_input_classifier.enabled}")
    if not gemini_input_classifier.enabled:
        print("  -> set USE_GEMINI_CLF1=true and GEMINI_API_KEY in .env")
        print("  -> also needs: pip install google-generativeai")
        return
    print(f"Model               : {gemini_input_classifier.model_name}\n")

    clf_ok = gem_ok = 0
    latencies = []
    disagreements = []

    for message, expected in CASES:
        clf = classifier1.predict(message.lower())
        clf_label, clf_conf = clf["label"], clf["confidence"]

        start = time.perf_counter()
        gem = gemini_input_classifier.predict(message, user_name="Hamid")
        latencies.append((time.perf_counter() - start) * 1000)

        gem_label = gem["label"] if gem else "FALLBACK"
        cleaned = gem.get("cleaned_text", message) if gem else message
        reply = gem.get("response_text", "") if gem else ""

        clf_hit = clf_label == expected
        gem_hit = gem_label == expected
        clf_ok += clf_hit
        gem_ok += gem_hit
        if clf_hit != gem_hit:
            disagreements.append((message, expected, clf_label, gem_label))

        print(f"{message!r}")
        print(f"   expected : {expected}")
        print(f"   CLF1     : {clf_label:16s} {clf_conf:.3f}  {'OK' if clf_hit else 'X'}")
        print(f"   Gemini   : {gem_label:16s}        {'OK' if gem_hit else 'X'}")
        if cleaned.strip().lower() != message.strip().lower():
            print(f"   cleaned  : {cleaned!r}")
        if reply:
            print(f"   reply    : {reply[:160]}")
        elif gem and gem_label != "command":
            print("   reply    : (MISSING - would need a 2nd Gemini call)")

    total = len(CASES)
    print("\n" + "=" * 62)
    print(f"CLF1   : {clf_ok}/{total} = {clf_ok/total*100:.1f}%")
    print(f"Gemini : {gem_ok}/{total} = {gem_ok/total*100:.1f}%")
    print(f"Gemini latency: avg {sum(latencies)/len(latencies):.0f} ms  "
          f"min {min(latencies):.0f}  max {max(latencies):.0f}")

    if disagreements:
        print("\nDisagreements (where exactly one was right):")
        for message, expected, c, g in disagreements:
            winner = "Gemini" if g == expected else "CLF1"
            print(f"  {winner:6s} wins  {message!r}  expected={expected} "
                  f"clf1={c} gemini={g}")


if __name__ == "__main__":
    main()
