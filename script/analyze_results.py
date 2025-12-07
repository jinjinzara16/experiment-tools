#!/usr/bin/env python3
import os
import re
import json
import statistics
from glob import glob

def parse_fuzzer_stats(path):
    data = {}
    if not os.path.exists(path):
        return None

    with open(path) as f:
        for line in f:
            if ":" not in line:
                continue
            k, v = line.split(":", 1)
            key = k.strip()
            val = v.strip()

            if key == "bitmap_cvg":
                val = val.rstrip("%").strip()

            data[key] = val

    return data


def parse_ppo_log(path):
    if not os.path.exists(path):
        return None

    steps = []
    rewards = []
    probs = []

    with open(path) as f:
        header = f.readline().strip().split(",")
        for line in f:
            cols = line.strip().split(",")
            if len(cols) < 2:
                continue

            try:
                step = int(cols[0])
                reward = float(cols[1])
            except ValueError:
                continue

            steps.append(step)
            rewards.append(reward)

            if len(cols) >= 2 + 4:
                try:
                    p = [float(x) for x in cols[2:6]]
                except ValueError:
                    p = []
            else:
                p = []
            probs.append(p)

    return {
        "steps": steps,
        "rewards": rewards,
        "probs": probs,
    }


def parse_ppo_server_log(path):
    if not os.path.exists(path):
        return None

    last_hist = None
    with open(path) as f:
        for line in f:
            if "actions=" in line:
                m = re.search(r"actions=\[([0-9,\s]+)\]", line)
                if m:
                    arr = m.group(1)
                    hist = [int(x) for x in arr.split(",")]
                    last_hist = hist
    return last_hist


IMPORTANT_STATS = [
    "execs_done",
    "execs_per_sec",
    "paths_total",
    "unique_crashes",
    "unique_hangs",
    "bitmap_cvg",
    "cycles_done",
    "pending_total",
    "pending_favs",
]

def safe_float(s):
    if s is None:
        return None
    s = s.strip()
    if s.endswith("%"):
        s = s[:-1].strip()
    try:
        return float(s)
    except:
        return None

def safe_int(s):
    try:
        return int(s)
    except:
        return None


def aggregate_runs(stats_list):
    result = {}

    for k in IMPORTANT_STATS:
        vals = []
        for st in stats_list:
            if st is None:
                continue
            if k not in st:
                continue
            v = safe_float(st[k])
            if v is not None:
                vals.append(v)

        if vals:
            result[k] = {
                "avg": sum(vals) / len(vals),
                "median": statistics.median(vals),
                "min": min(vals),
                "max": max(vals),
                "raw": vals,
            }

    return result

def analyze_result_dir(base_dir):

    runs = sorted(glob(os.path.join(base_dir, "*")))

    all_stats = []
    ppo_logs = []
    ppo_server_logs = []

    for run_path in runs:
        if not os.path.isdir(run_path):
            continue

        name = os.path.basename(run_path)

        print(f"\n=== Parsing {name} ===")

        st_path = os.path.join(run_path, "fuzzer_stats")
        stats = parse_fuzzer_stats(st_path)
        all_stats.append(stats)

        if stats:
            print("  fuzzer_stats OK")
        else:
            print("  fuzzer_stats missing")

        ppo_csv = os.path.join(run_path, "ppo_log.csv")
        ppo_data = parse_ppo_log(ppo_csv)
        if ppo_data:
            print("  ppo_log.csv OK")
            ppo_logs.append(ppo_data)

        ppo_srv = os.path.join(run_path, "ppo_server.log")
        hist = parse_ppo_server_log(ppo_srv)
        if hist:
            print("  ppo_server.log OK")
            ppo_server_logs.append(hist)

    print("\n==============================")
    print("Aggregate Fuzzer Stats")
    print("==============================")
    agg = aggregate_runs(all_stats)
    for k, v in agg.items():
        print(f"{k}: avg={v['avg']:.2f}, median={v['median']:.2f}, min={v['min']:.2f}, max={v['max']:.2f}")

    with open(os.path.join(base_dir, "summary.json"), "w") as f:
        json.dump(agg, f, indent=2)

    if ppo_logs:
        print("\n==============================")
        print("PPO Log Analysis")
        print("==============================")

        steps_len = [len(x["steps"]) for x in ppo_logs]
        print(f"steps per run: {steps_len}")

        final_hists = ppo_server_logs
        print("Final action histograms:", final_hists)

        if final_hists:
            dim = len(final_hists[0])
            avg_hist = [sum(h[i] for h in final_hists) / len(final_hists) for i in range(dim)]
            print(f"Average action distribution: {avg_hist}")

            with open(os.path.join(base_dir, "ppo_summary.json"), "w") as f:
                json.dump({
                    "steps_per_run": steps_len,
                    "final_action_hists": final_hists,
                    "avg_action_hist": avg_hist,
                }, f, indent=2)

    print("\n[OK] Done. summary.json and ppo_summary.json generated.")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="Base directory containing run subdirectories")
    args = ap.parse_args()

    analyze_result_dir(args.dir)
