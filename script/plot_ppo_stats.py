#!/usr/bin/env python3
import os
import json
import argparse
import numpy as np
import matplotlib.pyplot as plt


def load_summary(path):
    with open(path, "r") as f:
        return json.load(f)


def load_rewards_from_root(root_dir):
    rewards_all_runs = []

    for name in sorted(os.listdir(root_dir)):
        run_dir = os.path.join(root_dir, name)
        if not os.path.isdir(run_dir):
            continue

        csv_path = os.path.join(run_dir, "ppo_log.csv")
        if not os.path.exists(csv_path):
            continue

        rewards = []
        with open(csv_path, "r") as f:
            header = f.readline()
            for line in f:
                cols = line.strip().split(",")
                if len(cols) < 2:
                    continue
                try:
                    r = float(cols[1])
                except ValueError:
                    continue
                rewards.append(r)

        if rewards:
            rewards_all_runs.append(rewards)

    return rewards_all_runs


def moving_average(x, window):
    if window <= 1:
        return x
    if len(x) < window:
        return x
    w = np.ones(window) / float(window)
    return np.convolve(x, w, mode="valid")


def main():
    ap = argparse.ArgumentParser(
        description="Plot PPO stats (action histogram / steps_per_run / reward) from ppo_summary.json + ppo_log.csv"
    )
    ap.add_argument(
        "--dirs",
        nargs="+",
        required=True,
        help="각 항목은 label=dir 형식 (예: ppo_base=AFL-PPO-readelf)",
    )
    ap.add_argument(
        "--outdir",
        required=True,
        help="PNG를 저장할 출력 디렉토리",
    )
    ap.add_argument(
        "--reward-window",
        type=int,
        default=50,
        help="reward curve moving-average window size (default: 50 steps)",
    )
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    labels = []
    all_steps = []
    all_avg_actions = []
    all_rewards = []

    for item in args.dirs:
        if "=" not in item:
            raise SystemExit(f"bad --dirs item: {item} (label=dir 형태로 써라)")
        label, d = item.split("=", 1)
        labels.append(label)

        sum_path = os.path.join(d, "ppo_summary.json")
        if not os.path.exists(sum_path):
            raise SystemExit(f"{sum_path} not found")

        data = load_summary(sum_path)

        steps = data.get("steps_per_run", [])
        steps = [s for s in steps if s > 0]
        all_steps.append(steps)

        avg_hist = data.get("avg_action_hist", None)
        if avg_hist is None:
            hists = data.get("final_action_hists", [])
            if not hists:
                raise SystemExit(f"{sum_path}: no avg_action_hist or final_action_hists")
            avg_hist = list(np.mean(hists, axis=0))
        all_avg_actions.append(np.array(avg_hist, dtype=float))

        rewards_runs = load_rewards_from_root(d)
        all_rewards.append(rewards_runs)

    actions = np.arange(4)
    width = 0.8 / max(len(labels), 1)

    plt.figure(figsize=(6, 4))
    for i, (label, avg_hist) in enumerate(zip(labels, all_avg_actions)):
        plt.bar(actions + i * width, avg_hist, width=width, label=label)

    plt.xticks(actions + width * (len(labels) - 1) / 2, ["A0", "A1", "A2", "A3"])
    plt.ylabel("count (avg over runs)")
    plt.title("PPO action histogram (avg)")
    plt.legend()
    plt.tight_layout()
    out_path = os.path.join(args.outdir, "ppo_action_hist_all.png")
    plt.savefig(out_path)
    plt.close()
    print(f"[INFO] saved {out_path}")

    plt.figure(figsize=(6, 4))
    plt.boxplot(all_steps, labels=labels)
    plt.ylabel("steps per run")
    plt.title("PPO steps per run (per variant)")
    plt.tight_layout()
    out_path = os.path.join(args.outdir, "ppo_steps_boxplot.png")
    plt.savefig(out_path)
    plt.close()
    print(f"[INFO] saved {out_path}")

    if any(len(v) > 0 for v in all_rewards):
        per_variant_min = []
        for rewards_runs in all_rewards:
            if not rewards_runs:
                continue
            lengths = [len(r) for r in rewards_runs]
            per_variant_min.append(min(lengths))

        if per_variant_min:
            global_min = min(per_variant_min)
        else:
            global_min = 0

        if global_min > 0:
            window = args.reward_window
            if global_min <= window:
                window = max(1, global_min // 4)

            plt.figure(figsize=(6, 4))

            for label, rewards_runs in zip(labels, all_rewards):
                if not rewards_runs:
                    continue
                arr = np.array([r[:global_min] for r in rewards_runs], dtype=float)
                mean_reward = arr.mean(axis=0)
                smoothed = moving_average(mean_reward, window)
                xs = np.arange(len(smoothed))
                plt.plot(xs, smoothed, label=label)

            plt.xlabel("step index (truncated, smoothed)")
            plt.ylabel(f"reward (moving avg, window={window})")
            plt.title("PPO reward curve (avg over runs)")
            plt.legend()
            plt.tight_layout()
            out_path = os.path.join(args.outdir, "ppo_reward_curve.png")
            plt.savefig(out_path)
            plt.close()
            print(f"[INFO] saved {out_path}")

            avg_rewards_per_variant = []
            for rewards_runs in all_rewards:
                if not rewards_runs:
                    avg_rewards_per_variant.append([])
                    continue
                avg_per_run = [float(np.mean(r)) for r in rewards_runs]
                avg_rewards_per_variant.append(avg_per_run)

            plt.figure(figsize=(6, 4))
            plt.boxplot(avg_rewards_per_variant, labels=labels)
            plt.ylabel("average reward per run")
            plt.title("PPO reward (per run average)")
            plt.tight_layout()
            out_path = os.path.join(args.outdir, "ppo_reward_boxplot.png")
            plt.savefig(out_path)
            plt.close()
            print(f"[INFO] saved {out_path}")

    print("[INFO] done.")


if __name__ == "__main__":
    main()
