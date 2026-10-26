"""Example: CCRP vs capacity-unaware Dijkstra on the illustrative example floor.

Run from the repository root:
    python routing/examples/run_example.py            # prints the results table
    python routing/examples/run_example.py --plot     # also writes docs/figures/ccrp_vs_dijkstra_example.png

The example floor (data/examples/) is ILLUSTRATIVE: layout, dimensions and
occupancy are invented, not surveyed.
"""
import csv
import json
import os
import sys

import networkx as nx

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "routing"))
import ccrp  # noqa: E402

GRAPH = os.path.join(ROOT, "data", "examples", "ornek_kat_grafigi_v2.json")
OCCUPANCY = os.path.join(ROOT, "data", "examples", "ornek_doluluk.json")
EXITS = ["EXIT_W", "EXIT_E"]          # student context: staff-only EXIT_S is not reachable
SCENARIOS = {
    "A: all edges normal": {},
    "B: small stair blocked + c7-c8 uncertain": {
        ("S_small_F1", "S_small_F0"): "blocked",
        ("c7", "c8"): "uncertain",
    },
}


def main(plot=False):
    G = nx.node_link_graph(json.load(open(GRAPH, encoding="utf-8")), edges="edges")
    occ = {k: v["count"] for k, v in json.load(open(OCCUPANCY, encoding="utf-8"))["occupancy"].items()}
    results, rows = {}, []
    for name, states in SCENARIOS.items():
        H = ccrp.apply_context(G, states, role="student")
        for method in ["dijkstra", "ccrp"]:
            groups = ccrp.run(H, occ, EXITS, method)
            s = ccrp.summarize(groups)
            results[(name, method)] = groups
            row = [name, method, round(s["last_s"]), round(s["mean_s"], 1),
                   round(s["per_exit"].get("EXIT_W", 0)), round(s["per_exit"].get("EXIT_E", 0))]
            rows.append(row)
            print(f"{name:42s} {method:8s} last={row[2]:4d} s  mean={row[3]:5.1f} s  "
                  f"EXIT_W={row[4]:3d}  EXIT_E={row[5]:3d}")
    out_csv = os.path.join(ROOT, "routing", "examples", "results.csv")
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["scenario", "method", "last_s", "mean_s", "exit_w_people", "exit_e_people"])
        w.writerows(rows)
    print(f"wrote {out_csv}")
    if plot:
        make_plot(results, occ)


def make_plot(results, occ):
    import matplotlib.pyplot as plt
    import numpy as np

    sn = "A: all edges normal"
    col = {"dijkstra": "#969696", "ccrp": "#2166ac"}
    exc = {"EXIT_W": "#e08214", "EXIT_E": "#542788"}
    total = sum(occ.values())
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw=dict(width_ratios=[1.15, 1]))
    for m in ["dijkstra", "ccrp"]:
        g = sorted(results[(sn, m)], key=lambda r: r[3])
        t = np.array([0] + [r[3] for r in g])
        c = np.cumsum([0] + [r[2] for r in g])
        a1.step(t, c, where="post", color=col[m], lw=2.4, label=f"{m} (last person {t[-1]:.0f} s)")
    a1.axhline(total, color="#d9d9d9", lw=0.8)
    a1.set_xlabel("Time after shaking stops (s)")
    a1.set_ylabel("People out of the building (cumulative)")
    a1.set_title("Scenario A: cumulative evacuation", loc="left")
    a1.legend(frameon=False, loc="upper left")
    rooms = list(occ)
    y = np.arange(len(rooms))
    h = 0.36
    for k, m in enumerate(["dijkstra", "ccrp"]):
        per = {r: {e: 0.0 for e in exc} for r in rooms}
        for s, ex, q, _, _ in results[(sn, m)]:
            per[s][ex] += q
        left = np.zeros(len(rooms))
        yy = y + (h / 2 + 0.02) * (1 if k == 0 else -1)
        for ex in exc:
            v = np.array([per[r][ex] for r in rooms])
            a2.barh(yy, v, h, left=left, color=exc[ex], alpha=0.45 if m == "dijkstra" else 1,
                    label=ex if m == "ccrp" else None)
            left += v
    a2.set_yticks(y)
    a2.set_yticklabels(rooms)
    a2.invert_yaxis()
    a2.set_xlabel("People")
    a2.set_title("Exit assignment per room (light = Dijkstra, dark = CCRP)", loc="left")
    a2.set_xlim(0, max(occ.values()) * 1.45)
    a2.legend(frameon=False, fontsize=8, loc="upper right")
    out = os.path.join(ROOT, "docs", "figures", "ccrp_vs_dijkstra_example.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    fig.tight_layout()
    fig.savefig(out, dpi=200)
    print(f"wrote {out}")


if __name__ == "__main__":
    main(plot="--plot" in sys.argv)
