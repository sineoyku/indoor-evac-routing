# quake-evac

Earthquake-first indoor evacuation system (İzmir University of Economics senior design project).
See `routing/README.md` for the current routing prototype.

```
data/examples/     illustrative example floor graph + occupancy snapshot
graph-builder/     capacities.py – adds width, flow_capacity, travel_time_s to a graph
routing/           ccrp.py – CCRP + Dijkstra baseline; examples/run_example.py
docs/figures/      figures produced by the examples
```

Quick start (from this folder): `pip install networkx matplotlib && python routing/examples/run_example.py`
