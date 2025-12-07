#!/usr/bin/env python3
import argparse
import os
import subprocess
from subprocess import CalledProcessError

IMAGE = "rl-project"


def run_cmd(cmd):
    print("[RUN]", " ".join(cmd))
    try:
        return subprocess.run(cmd, check=True)
    except CalledProcessError as e:
        print("[ERR] command failed:", e)
        raise


def start_container(fuzzer, prog, run_id, time_sec, outdir, lr, gamma, clip):
    cname = f"{fuzzer}_{prog}_{run_id}"
    abs_out = os.path.abspath(outdir)

    cmd = [
        "docker", "run",
        "-d", "--rm",
        "--name", cname,
        "-v", f"{abs_out}:/output",

        "-e", f"RL_LR={lr}",
        "-e", f"RL_GAMMA={gamma}",
        "-e", f"RL_CLIP={clip}",
        IMAGE,
        "/script/entry.sh",
        fuzzer,
        prog,
        str(run_id),
        str(time_sec),
    ]

    run_cmd(cmd)
    return cname


def wait_container(cname):
    try:
        run_cmd(["docker", "wait", cname])
    except CalledProcessError:
        print(f"[WARN] docker wait failed for {cname}")


def main():
    ap = argparse.ArgumentParser(
        description="Run AFL / AFL-PPO experiments in Docker."
    )
    ap.add_argument(
        "--fuzzer",
        choices=["AFL", "AFL-PPO", "both"],
        required=True,
        help="Which fuzzer(s) to run",
    )
    ap.add_argument(
        "--prog",
        choices=["readelf", "objdump"],
        required=True,
        help="Target program",
    )
    ap.add_argument(
        "--num-runs",
        type=int,
        default=5,
        help="Number of runs per fuzzer",
    )
    ap.add_argument(
        "--max-parallel",
        type=int,
        default=2,
        help="Max number of containers to run in parallel",
    )
    ap.add_argument(
        "--time-sec",
        type=int,
        required=True,
        help="Time per run in seconds (e.g., 3600 for 1 hour)",
    )
    ap.add_argument(
        "--output",
        type=str,
        required=True,
        help="Result root directory (will be mounted to /output in containers)",
    )

    ap.add_argument(
        "--lr",
        type=float,
        default=1e-4,
        help="PPO learning rate (default: 1e-4)",
    )
    ap.add_argument(
        "--gamma",
        type=float,
        default=0.99,
        help="Discount factor gamma (default: 0.99)",
    )
    ap.add_argument(
        "--clip",
        type=float,
        default=0.2,
        help="PPO clipping epsilon (default: 0.2)",
    )

    args = ap.parse_args()
    os.makedirs(args.output, exist_ok=True)

    if args.fuzzer == "both":
        fuzzers = ["AFL", "AFL-PPO"]
    else:
        fuzzers = [args.fuzzer]

    print(f"[INFO] image={IMAGE}, output={os.path.abspath(args.output)}")
    print(f"[INFO] fuzzers={fuzzers}, prog={args.prog}, num_runs={args.num_runs}")
    print(f"[INFO] max_parallel={args.max_parallel}, time_sec={args.time_sec}")
    print(f"[INFO] PPO hyperparams: lr={args.lr}, gamma={args.gamma}, clip={args.clip}")

    for fuzzer in fuzzers:
        print(f"\n=== Running fuzzer={fuzzer} prog={args.prog} ===")
        running = []

        for run_id in range(args.num_runs):
            if len(running) >= args.max_parallel:
                cname0 = running.pop(0)
                print(f"[INFO] Waiting for {cname0} to finish...")
                wait_container(cname0)

            cname = start_container(
                fuzzer=fuzzer,
                prog=args.prog,
                run_id=run_id,
                time_sec=args.time_sec,
                outdir=args.output,
                lr=args.lr,
                gamma=args.gamma,
                clip=args.clip,
            )
            running.append(cname)

        for cname in running:
            print(f"[INFO] Waiting for {cname} to finish...")
            wait_container(cname)

    print("\n=== All runs finished ===")
    print(f"Results under: {os.path.abspath(args.output)}")


if __name__ == "__main__":
    main()
