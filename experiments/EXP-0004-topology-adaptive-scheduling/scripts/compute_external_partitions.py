#!/usr/bin/env python3
"""
External Graph Partitioner Helper (METIS k-way via pymetis & Leiden via python-igraph).
Reads a directed CSR graph edge list or generates the exact modular SBM topology via C++ dump,
computes undirected symmetrized partitions using:
  1. METIS multilevel k-way (`pymetis.part_graph`)
  2. Leiden modularity optimization (`igraph.Graph.community_leiden`)
and writes one-integer-per-line partition label files for C++ benchmark consumption.
"""

import sys
import os
import argparse
from typing import List, Tuple
import pymetis
import igraph as ig

def read_edge_list(edge_file: str) -> Tuple[int, List[Tuple[int, int]]]:
    edges = []
    num_nodes = 0
    with open(edge_file, "r", encoding="utf-8") as f:
        header = f.readline().strip().split()
        num_nodes = int(header[0])
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 2:
                u, v = int(parts[0]), int(parts[1])
                if u != v:
                    edges.append((u, v))
    return num_nodes, edges

def compute_metis_partition(num_nodes: int, edges: List[Tuple[int, int]], num_parts: int) -> List[int]:
    adj = [set() for _ in range(num_nodes)]
    for u, v in edges:
        adj[u].add(v)
        adj[v].add(u)
    adjacency_list = [sorted(list(s)) for s in adj]
    _, membership = pymetis.part_graph(num_parts, adjacency=adjacency_list)
    return [int(m) for m in membership]

def compute_leiden_partition(num_nodes: int, edges: List[Tuple[int, int]], num_parts: int) -> List[int]:
    g = ig.Graph(n=num_nodes, edges=edges, directed=False)
    g.simplify(multiple=True, loops=True)
    # Run Leiden modularity optimization (or CPM) and map clusters to num_parts balanced buckets
    part = g.community_leiden(objective_function="modularity", n_iterations=5)
    membership = list(part.membership)
    # If Leiden produces more than num_parts clusters, assign clusters greedily by size to num_parts buckets
    cluster_counts = {}
    for m in membership:
        cluster_counts[m] = cluster_counts.get(m, 0) + 1
    sorted_clusters = sorted(cluster_counts.keys(), key=lambda c: cluster_counts[c], reverse=True)
    bucket_loads = [0] * num_parts
    cluster_to_bucket = {}
    for c in sorted_clusters:
        lightest_b = min(range(num_parts), key=lambda b: bucket_loads[b])
        cluster_to_bucket[c] = lightest_b
        bucket_loads[lightest_b] += cluster_counts[c]
    return [cluster_to_bucket[m] for m in membership]

def write_partition_file(path: str, labels: List[int]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for lbl in labels:
            f.write(f"{lbl}\n")

def main():
    parser = argparse.ArgumentParser(description="Compute METIS and igraph-Leiden partitions")
    parser.add_argument("--edges", required=True, help="Path to input edge list file")
    parser.add_argument("--parts", type=int, default=6, help="Number of partitions")
    parser.add_argument("--out-metis", required=True, help="Output file for METIS k-way partition")
    parser.add_argument("--out-leiden", required=True, help="Output file for igraph Leiden partition")
    args = parser.parse_args()

    num_nodes, edges = read_edge_list(args.edges)
    metis_labels = compute_metis_partition(num_nodes, edges, args.parts)
    write_partition_file(args.out_metis, metis_labels)

    leiden_labels = compute_leiden_partition(num_nodes, edges, args.parts)
    write_partition_file(args.out_leiden, leiden_labels)

if __name__ == "__main__":
    main()
