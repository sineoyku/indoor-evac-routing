"""Add flow capacities and travel times to a navigation graph.

Last step of the graph-building pipeline: takes a graph whose edges have
`length` and `type` (and optionally `width`) and adds

    width          [m]         usable width of the edge
    flow_capacity  [persons/s] specific flow x width
    travel_time_s  [s]         ceil(length / free walking speed)

The output is the *static* graph file: no live states, no occupancy.

PROTOTYPE VALUES - verify before using in the report:
  specific flow ~1.3 persons/m/s (corridor, door), ~1.1 (stair) - approximate
  SFPE-type values; full width is used, not SFPE effective width.

Usage:
    python graph-builder/capacities.py input_graph.json output_graph.json
"""
import json
import math
import sys

import networkx as nx

SPEC_FLOW = {"corridor": 1.3, "door": 1.3, "stair": 1.1, "elevator": 1.3}  # persons / s / m
SPEED = {"corridor": 1.2, "door": 1.2, "stair": 0.6, "elevator": 1.2}      # m / s
DEFAULT_WIDTH = {"corridor": 2.0, "door": 0.9, "stair": 1.5, "elevator": 1.0}
ROOM_INTERIOR_WIDTH = 3.0   # walking inside a room towards its door: not the bottleneck


def edge_width(G, u, v, e):
    """Pick the usable width of edge (u, v)."""
    tu, tv = G.nodes[u]["type"], G.nodes[v]["type"]
    if "room" in (tu, tv):                       # room <-> door: inside the room
        return ROOM_INTERIOR_WIDTH
    if "door" in (tu, tv):                       # door <-> corridor: the door's clear width
        d = u if tu == "door" else v
        return G.nodes[d].get("width", DEFAULT_WIDTH["door"])
    if "width" in e:                             # measured / extracted width
        return e["width"]
    return DEFAULT_WIDTH.get(e["type"], DEFAULT_WIDTH["corridor"])


def add_capacities(G):
    for u, v, e in G.edges(data=True):
        t = e["type"]
        e["width"] = edge_width(G, u, v, e)
        e["flow_capacity"] = round(SPEC_FLOW.get(t, 1.3) * e["width"], 2)
        e["travel_time_s"] = math.ceil(e["length"] / SPEED.get(t, 1.2))
        e["state"] = "normal"                    # static file never carries live states
    G.graph.setdefault("units", {"length": "m", "width": "m",
                                 "flow_capacity": "persons/s", "travel_time_s": "s"})
    G.graph["capacity_assumptions"] = ("specific flow 1.3 p/m/s corridor & door, 1.1 stair; "
                                       "speeds 1.2 / 0.6 m/s; approximate, verify (SFPE)")
    return G


def load_graph(path):
    return nx.node_link_graph(json.load(open(path, encoding="utf-8")), edges="edges")


def save_graph(G, path):
    data = nx.node_link_data(G, edges="edges")
    for e in data["edges"]:
        for k in [k for k, val in e.items() if val is None]:
            del e[k]
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    save_graph(add_capacities(load_graph(src)), dst)
    print(f"wrote {dst}")
