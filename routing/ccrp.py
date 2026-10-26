"""Capacity-constrained evacuation routing (prototype).

CCRP - Capacity Constrained Route Planner (Lu, George & Shekhar, 2005):
repeatedly find the earliest-arrival path from any occupied source to any exit,
given the capacity still free on each edge at each time step; send as many people
as that path can take; reserve the capacity; repeat until everyone is routed.

Baseline ("dijkstra"): everyone takes their own capacity-unaware shortest path,
evaluated with the SAME capacity / queue reservation model, so the difference
between methods comes only from route choice.

Inputs (three layers, joined by node id):
  1. static graph  - edges with flow_capacity [p/s] and travel_time_s [s]
  2. occupancy     - {node_id: number of people}
  3. edge states   - {(u, v): "blocked" | "uncertain"} plus user role

See README.md for the list of simplifications.
"""
import heapq
import math

import networkx as nx

UNCERTAIN_PENALTY = 5   # travel-time multiplier for "uncertain" edges (prototype choice)
HORIZON_S = 5000        # give up searching for free capacity after this many seconds


def apply_context(G, states=None, role="student"):
    """Return the routable graph for this situation.

    Hard constraints remove edges (elevator, blocked, staff_only for non-staff).
    Soft constraints change cost (uncertain -> travel time x UNCERTAIN_PENALTY).
    The routing cost used below is the edge attribute `tt` (seconds).
    """
    states = states or {}
    H = nx.DiGraph()
    H.add_nodes_from(G.nodes(data=True))
    for u, v, e in G.edges(data=True):
        st = states.get((u, v), states.get((v, u), "normal"))
        if e["type"] == "elevator" or e.get("emergency_use") is False or st == "blocked":
            continue
        if e.get("access") == "staff_only" and role != "staff":
            continue
        e2 = dict(e)
        e2["state"] = st
        e2["tt"] = e["travel_time_s"] * (UNCERTAIN_PENALTY if st == "uncertain" else 1)
        H.add_edge(u, v, **e2)
    return H


class Reservations:
    """Capacity already used on each edge at each departure second."""

    def __init__(self, H):
        self.H = H
        self.used = {}

    def avail(self, u, v, t):
        return self.H.edges[u, v]["flow_capacity"] - self.used.get((u, v, t), 0.0)

    def earliest_dep(self, u, v, t):
        """First second >= t at which edge (u, v) still has free capacity (waiting allowed)."""
        while t < HORIZON_S:
            if self.avail(u, v, t) > 1e-9:
                return t
            t += 1
        return None

    def reserve(self, legs, q):
        for u, v, t in legs:
            self.used[(u, v, t)] = self.used.get((u, v, t), 0.0) + q


def earliest_arrival(H, R, sources, exits):
    """Earliest-arrival path from a super-source (all occupied sources at t=0) to any exit.

    Returns (arrival_time, source, legs) where legs = [(u, v, departure_second), ...].
    """
    best = {s: 0 for s in sources}
    parent = {}
    pq = [(0, s) for s in sources]
    heapq.heapify(pq)
    while pq:
        a, u = heapq.heappop(pq)
        if a > best.get(u, math.inf):
            continue
        if u in exits:
            legs, n = [], u
            while n in parent:
                p, dep = parent[n]
                legs.append((p, n, dep))
                n = p
            return a, n, legs[::-1]
        for v in H.successors(u):
            dep = R.earliest_dep(u, v, a)
            if dep is None:
                continue
            arr = dep + H.edges[u, v]["tt"]
            if arr < best.get(v, math.inf):
                best[v] = arr
                parent[v] = (u, dep)
                heapq.heappush(pq, (arr, v))
    return None


def _fixed_path_arrival(H, R, path):
    t, legs = 0, []
    for u, v in zip(path, path[1:]):
        dep = R.earliest_dep(u, v, t)
        legs.append((u, v, dep))
        t = dep + H.edges[u, v]["tt"]
    return t, legs


def shortest_paths_to_exits(H, exits):
    """Capacity-unaware best path from every node to its nearest exit (reverse multi-source Dijkstra)."""
    _, paths = nx.multi_source_dijkstra(H.reverse(copy=True), exits, weight="tt")
    return {n: p[::-1] for n, p in paths.items()}


def run(H, occupancy, exits, method="ccrp"):
    """Route everyone in `occupancy` to `exits`.

    method: "ccrp" or "dijkstra" (baseline).
    Returns a list of groups: (source, exit, people, arrival_s, path).
    """
    R = Reservations(H)
    remaining = {n: float(c) for n, c in occupancy.items() if c > 0}
    exits_set = set(exits)
    fixed = shortest_paths_to_exits(H, exits) if method == "dijkstra" else None
    unreachable = [s for s in remaining if fixed is not None and s not in fixed]
    if unreachable:
        raise ValueError(f"no route to any exit from: {unreachable}")
    groups = []
    while any(q > 1e-9 for q in remaining.values()):
        srcs = [s for s, q in remaining.items() if q > 1e-9]
        if method == "ccrp":
            found = earliest_arrival(H, R, srcs, exits_set)
            if found is None:
                raise ValueError(f"no route to any exit from: {srcs}")
            a, s, legs = found
        elif method == "dijkstra":
            cand = [(_fixed_path_arrival(H, R, fixed[s]), s) for s in srcs]
            (a, legs), s = min(cand, key=lambda c: c[0][0])
        else:
            raise ValueError(f"unknown method {method!r}")
        q = min([remaining[s]] + [R.avail(u, v, t) for u, v, t in legs])
        R.reserve(legs, q)
        remaining[s] -= q
        groups.append((s, legs[-1][1], q, a, [legs[0][0]] + [leg[1] for leg in legs]))
    return groups


def summarize(groups):
    """Last arrival, mean arrival (person-weighted) and people per exit."""
    total = sum(g[2] for g in groups)
    per_exit = {}
    for _, ex, q, _, _ in groups:
        per_exit[ex] = per_exit.get(ex, 0.0) + q
    return {
        "last_s": max(g[3] for g in groups),
        "mean_s": sum(g[2] * g[3] for g in groups) / total,
        "per_exit": per_exit,
    }
