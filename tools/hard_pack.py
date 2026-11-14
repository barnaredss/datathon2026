"""Freeze a hard-mode submission: inject the full-train profiles into agent_hard/agent.py.

Usage: python -m tools.hard_pack <tag>     ->  submissions/<tag>/agent.py  (single file, ready to upload)
"""
import json
import sys
import warnings

from tools.hard import ROOT, compute_profiles, load_hard, load_price_co2

warnings.filterwarnings("ignore")
MARKER = "PROFILES = None  # __PROFILES__"


def main():
    tag = sys.argv[1]
    src = (ROOT / "agent_hard" / "agent.py").read_text(encoding="utf-8")
    assert src.count(MARKER) == 1, "marker not found exactly once"
    prof = compute_profiles(load_hard(), load_price_co2())
    lines = ["# Perfiles calculados con el año de entrenamiento oficial (data/train); ver tools/hard.py",
             "PROFILES = {"]
    for k, v in prof.items():
        lines.append("    %s: %r," % (json.dumps(k), v))
    lines.append("}")
    out = ROOT / "submissions" / tag
    out.mkdir(parents=True, exist_ok=True)
    (out / "agent.py").write_text(src.replace(MARKER, "\n".join(lines)), encoding="utf-8", newline="\n")
    print("wrote", out / "agent.py", "(%.1f KB)" % ((out / "agent.py").stat().st_size / 1024), "lambda", prof["lambda"])


if __name__ == "__main__":
    main()
