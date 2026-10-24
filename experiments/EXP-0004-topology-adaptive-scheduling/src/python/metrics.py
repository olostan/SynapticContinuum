"""
Graph metrics and cross-validation utilities using NetworkX.
"""

from typing import Dict, Any, List, Tuple
import networkx as nx
import numpy as np


def compute_networkx_graph_metrics(
    num_nodes: int,
    edges: List[Tuple[int, int]],
    partition_map: List[int] = None
) -> Dict[str, Any]:
    """
    Computes graph metrics using NetworkX for cross-validation with C++.
    """
    G = nx.DiGraph()
    G.add_nodes_from(range(num_nodes))
    G.add_edges_from(edges)

    # Undirected projection for clustering
    G_undir = G.to_undirected()
    clustering = float(nx.average_clustering(G_undir))

    # Largest strongly connected component for path length
    sccs = list(nx.strongly_connected_components(G))
    largest_scc = max(sccs, key=len) if sccs else set()
    if len(largest_scc) > 1:
        subG = G.subgraph(largest_scc)
        path_length = float(nx.average_shortest_path_length(subG))
    else:
        path_length = 0.0

    edge_cut = 0.0
    if partition_map and len(partition_map) == num_nodes and len(edges) > 0:
        cuts = sum(1 for u, v in edges if partition_map[u] != partition_map[v])
        edge_cut = cuts / len(edges)

    return {
        "num_nodes": num_nodes,
        "num_edges": len(edges),
        "clustering_coefficient": clustering,
        "path_length_largest_scc": path_length,
        "edge_cut_fraction": edge_cut,
    }
