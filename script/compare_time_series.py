#!/usr/bin/env python3
import os
import argparse
import numpy as np
import matplotlib.pyplot as plt

def parse_plot_data(path):
    times = []
    covs = []
    epss = []

    if not os.path.exists(path):
        return times, covs, epss

    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 11:
                continue

            try:
                t_raw = int(parts[0])
                map_size_str = parts[6]
                if map_size_str.endswith("%"):
                    map_size = float(map_size_str[:-1])
                else:
                    map_size = float(map_size_str)
                execs_per_sec = float(parts[10])
            except Exception:
                continue

            times.append(t_raw)
            covs.append(map_size)
            epss.append(execs_per_sec)

    if not times:
        return [], [], []

    t0 = times[0]
    times = [t - t0 for t in times]

    return times, covs, epss


def load_config_series(root_dir, bin_sec=5):
    root_dir = os.path.abspath(root_dir)
    subdirs = sorted(
        d for d in os.listdir(root_dir)
        if os.path.isdir(os.path.join(root_dir, d))
    )

    runs = []
    for sd in subdirs:
        pp = os.path.join(root_dir, sd, "plot_data")
        t, c, e = parse_plot_data(pp)
        if t:
            runs.append((np.array(t, dtype=float),
                         np.array(c, dtype=float),
                         np.array(e, dtype=float)))

    if not runs:
        return None, None, None

    max_t = max(r[0][-1] for r in runs)
    grid = np.arange(0.0, max_t + bin_sec, bin_sec)

    cov_sum = np.zeros_like(grid)
    eps_sum = np.zeros_like(grid)
    cnt = 0

    for t, c, e in runs:
        cov_interp = np.interp(grid, t, c)
        eps_interp = np.interp(grid, t, e)
        cov_sum += cov_interp
        eps_sum += eps_interp
        cnt += 1

    cov_avg = cov_sum / cnt
    eps_avg = eps_sum / cnt

    return grid, cov_avg, eps_avg


def plot_coverage_all(cfgs, labels, outdir, title_prefix, bin_sec=5):
    os.makedirs(outdir, exist_ok=True)

    series = {}
    for cfg, label in zip(cfgs, labels):
        t, cov, eps = load_config_series(cfg, bin_sec=bin_sec)
        if t is not None:
            series[label] = (t, cov)

    if not series:
        print("[WARN] no coverage series found.")
        return

    def smooth(y, k=5):
        if k <= 1:
            return y
        kernel = np.ones(k) / k
        return np.convolve(y, kernel, mode="same")

    def draw_plot(xmin, xmax, filename_suffix):
        plt.figure()

        for label, (t, cov) in series.items():
            mask = (t >= xmin) & (t <= xmax)
            t_slice = t[mask]
            cov_slice = cov[mask]

            plt.plot(t_slice, cov_slice, linewidth=2.3, label=label)

        plt.xlabel("time (sec)")
        plt.ylabel("bitmap coverage (%)")
        plt.title(f"{title_prefix} – Coverage over time {filename_suffix}")
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()

        out_path = os.path.join(outdir, f"coverage{filename_suffix}.png")
        plt.savefig(out_path)
        plt.close()
        print(f"[INFO] saved {out_path}")


    max_t = max(v[0][-1] for v in series.values())
    draw_plot(0, max_t, "_full")

    draw_plot(0, 800, "_zoom_0_800")

    draw_plot(2000, max_t, "_zoom_2000_end")


def plot_execs_all(cfgs, labels, outdir, title_prefix, bin_sec=5):
    os.makedirs(outdir, exist_ok=True)

    series = {}
    for cfg, label in zip(cfgs, labels):
        t, cov, eps = load_config_series(cfg, bin_sec=bin_sec)
        if t is None:
            print(f"[WARN] no valid runs under {cfg}, skip")
            continue
        series[label] = (t, eps)

    if not series:
        print("[WARN] no series to plot for execs/sec")
        return

    plt.figure()

    for label, (t, eps) in series.items():
        plt.plot(t, eps, label=label, linewidth=1.0)

    max_t = max(v[0][-1] for v in series.values())
    xticks = np.arange(0, max_t + 1, 500)
    plt.xticks(xticks)

    plt.xlabel("time (sec)")
    plt.ylabel("execs/sec")
    plt.title(f"{title_prefix} – Execs/sec over time (avg across runs)")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()

    out_path = os.path.join(outdir, "execs_per_sec_over_time.png")
    plt.savefig(out_path)
    plt.close()
    print(f"[INFO] saved {out_path}")


def main():
    ap = argparse.ArgumentParser(
        description="Compare coverage / execs/sec over time across configs (AFL vs PPO)."
    )
    ap.add_argument(
        "--cfg",
        nargs="+",
        required=True,
        help="실험 루트 디렉토리 리스트 (각각 여러 run 하위 디렉토리를 포함).",
    )
    ap.add_argument(
        "--labels",
        nargs="+",
        required=True,
        help="각 cfg에 대응하는 라벨 (그래프 legend에 사용).",
    )
    ap.add_argument(
        "--out",
        required=True,
        help="출력 디렉토리 (PNG 저장 위치).",
    )
    ap.add_argument(
        "--title-prefix",
        default="",
        help="그래프 제목 앞에 붙일 prefix (예: readelf, objdump).",
    )
    ap.add_argument(
        "--bin-sec",
        type=int,
        default=5,
        help="시간축 보간 간격 (초 단위, 기본 5초).",
    )

    args = ap.parse_args()

    if len(args.cfg) != len(args.labels):
        raise SystemExit("cfg 개수와 labels 개수가 다르다.")

    title_prefix = args.title_prefix if args.title_prefix else "Coverage/Execs"

    plot_coverage_all(args.cfg, args.labels, args.out, title_prefix, bin_sec=args.bin_sec)
    plot_execs_all(args.cfg, args.labels, args.out, title_prefix, bin_sec=args.bin_sec)


if __name__ == "__main__":
    main()
