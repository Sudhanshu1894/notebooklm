"""
Routing Analytics Script
Analyzes data/routing_log.jsonl to summarize routing decisions (vector_only vs hybrid).
"""

import json
import os
from collections import Counter
import argparse

def analyze_routing(log_path: str):
    if not os.path.exists(log_path):
        print(f"Log file not found: {log_path}")
        return

    routes = Counter()
    reasons = Counter()
    total_latency = 0.0
    count = 0

    with open(log_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                route = entry.get("route", "unknown")
                reason = entry.get("reason", "unknown")
                latency = entry.get("latency_ms", 0.0)

                routes[route] += 1
                reasons[reason] += 1
                total_latency += latency
                count += 1
            except json.JSONDecodeError:
                pass

    if count == 0:
        print("No valid entries found in routing log.")
        return

    print("=" * 50)
    print("           ROUTING ANALYTICS SUMMARY")
    print("=" * 50)
    print(f"Total queries analyzed : {count}")
    print(f"Average router latency : {total_latency / count:.2f} ms")
    
    print("\n--- Route Distribution ---")
    for r, c in routes.items():
        percentage = (c / count) * 100
        print(f"  {r.upper():<12} : {c} ({percentage:.1f}%)")

    print("\n--- Top Routing Reasons ---")
    for r, c in reasons.most_common(5):
        print(f"  - {r}: {c}")
    print("=" * 50)

def main():
    parser = argparse.ArgumentParser(description="Analyze routing logs.")
    parser.add_argument("--log", type=str, default="data/routing_log.jsonl", help="Path to routing_log.jsonl")
    args = parser.parse_args()
    
    analyze_routing(args.log)

if __name__ == "__main__":
    main()
