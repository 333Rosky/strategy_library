import json
import re
from pathlib import Path

NOTEBOOK = Path(r"\\wsl.localhost\Ubuntu\home\romai\strategy_library\High Frequency Trading\GLFT.ipynb")

BAD_PATTERNS = [
    r"add_variance_ratio",
    r"add_variance_ratio_robust",
    r"\brun_vrt_maker_corrected\b",
    r"\bVRT_THRESHOLD\b",
    r"\bsignal_strength\b",
    r"min_trade_price",
    r"max_trade_price",
    r"bid_close",
    r"ask_close",
]


def main() -> None:
    nb = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    cells = nb.get("cells", [])

    # Clear execution outputs (also removes embedded images)
    for c in cells:
        if c.get("cell_type") == "code":
            c["execution_count"] = None
            c["outputs"] = []

    keep: list[dict] = []
    for c in cells:
        txt = "".join(c.get("source", []) or "")

        # Always keep the GLFT paper implementation cell(s)
        if "run_glft_paper" in txt or "glft_asymptotic_deltas" in txt:
            keep.append(c)
            continue

        if any(re.search(pat, txt) for pat in BAD_PATTERNS):
            continue

        keep.append(c)

    # Keep only up to the backtest call (inclusive), if it exists
    last_idx = None
    for i, c in enumerate(keep):
        txt = "".join(c.get("source", []) or "")
        if "run_glft_paper(" in txt:
            last_idx = i
    if last_idx is not None:
        keep = keep[: last_idx + 1]

    nb["cells"] = keep
    NOTEBOOK.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
