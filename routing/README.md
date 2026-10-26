# routing/

> **Prototype.** Algorithm logic is complete; physical parameters and the
> example floor are illustrative. Do not quote the example times as predictions.

## What is here

| File | Purpose |
|---|---|
| `ccrp.py` | Capacity-constrained routing (CCRP) and the Dijkstra baseline |
| `examples/run_example.py` | Scenario A/B comparison on the example floor; writes `examples/results.csv` (and a figure with `--plot`) |

Related: `graph-builder/capacities.py` adds `width`, `flow_capacity` and
`travel_time_s` to a graph; `data/examples/` holds the example graph and
occupancy snapshot.

## How the layers fit together

1. **Static graph** (`data/.../*_graph.json`) – nodes, edges, lengths, widths,
   flow capacities, access rules. Never contains live data.
2. **Occupancy** (`*_doluluk.json` / live feed) – `{node_id: count}`, keyed by the
   same node ids.
3. **Edge states + context** – `{(u, v): "blocked" | "uncertain"}`, user role.

`apply_context(G, states, role)` builds the routable graph (removes blocked,
elevator and staff-only edges for students; multiplies travel time of uncertain
edges by 5). `run(H, occupancy, exits, method)` routes everyone:

- `method="ccrp"` – repeat: earliest-arrival path from any occupied room to any
  exit, given free capacity per edge per second → send as many people as the path
  can take → reserve that capacity.
- `method="dijkstra"` – baseline: everyone on their own capacity-unaware shortest
  path, evaluated with the **same** capacity/queue model.

The output is a list of groups `(room, exit, people, arrival_s, path)`;
`summarize()` gives last arrival, mean arrival and people per exit.

## Quick start

```bash
pip install networkx matplotlib
python routing/examples/run_example.py          # from the repository root
```

Expected output (example floor, 175 people):

| Scenario | Method | Last person | Mean exit time | EXIT_W / EXIT_E |
|---|---|---|---|---|
| A: all edges normal | Dijkstra | 104 s | 72.4 s | 32 / 143 |
| A: all edges normal | CCRP | 89 s | 68.4 s | 68 / 107 |
| B: small stair blocked + c7–c8 uncertain | Dijkstra | 133 s | 98.1 s | 0 / 175 |
| B: small stair blocked + c7–c8 uncertain | CCRP | 132 s | 97.8 s | 0 / 175 |

## Simplifications (to fix before real use)

1. **1 s time steps**; travel times rounded up.
2. **Unlimited waiting at nodes** – no node capacity, no queue spillback
   (CCRP as published supports node capacities: add `max_occupancy`).
3. **Constant walking speed** – no density–speed relation inside CCRP; validate
   plans in a pedestrian simulator (JuPedSim / Vadere).
4. **Approximate specific flow** (1.3 p/m/s corridor & door, 1.1 stair) and full
   width instead of SFPE effective width – verify values.
5. **People are divisible** (float flows) – round to persons/groups for the app.
6. **No pre-movement time** – everyone starts at t = 0.
7. **100 % compliance** – everyone follows the plan.
8. **Occupancy treated as exact** – `confidence` is ignored (use Monte Carlo).
9. **CCRP is a heuristic** – compare against an LP min-cost-flow optimum.
10. **Uncertain penalty inflates time** – the ×5 multiplier mixes risk with real
    travel time; keep them separate in the final version.

## Reference

Lu, Q., George, B., & Shekhar, S. (2005). Capacity Constrained Routing Algorithms
for Evacuation Planning: A Summary of Results. *SSTD 2005*, LNCS 3633.
