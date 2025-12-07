#!/bin/bash
set -euo pipefail

if [ "$#" -ne 4 ]; then
  echo "Usage: $0 <FUZZER: AFL|AFL-PPO> <PROG: readelf|objdump> <RUN_ID> <TIME_SEC>"
  exit 1
fi

FUZZER="$1"
PROG="$2"
RUN_ID="$3"
TIME_SEC="$4"

SETUP_DIR="/setup"
SCRIPT_DIR="/script"

OUTDIR="/output/${FUZZER}_${PROG}_${RUN_ID}"
mkdir -p "${OUTDIR}"

echo "[ENTRY] FUZZER=${FUZZER}, PROG=${PROG}, RUN_ID=${RUN_ID}, TIME_SEC=${TIME_SEC}"
echo "[ENTRY] OUTDIR=${OUTDIR}"

export AFL_SKIP_CPUFREQ=1
export AFL_NO_UI=1
export AFL_NO_AFFINITY=1
export AFL_SKIP_CRASHES=1
export AFL_SEED=$((1234 + RUN_ID))

export RL_LR="${RL_LR:-1e-4}"
export RL_GAMMA="${RL_GAMMA:-0.99}"
export RL_CLIP="${RL_CLIP:-0.2}"

echo "[ENTRY] RL_LR=${RL_LR}, RL_GAMMA=${RL_GAMMA}, RL_CLIP=${RL_CLIP}"

INPUT_DIR="/fuzzer/AFL/testcases/others/elf"

case "${PROG}" in
  readelf) TARGET_ARGS="-a @@" ;;
  objdump) TARGET_ARGS="-d @@" ;;
  *) echo "[ENTRY] Unknown PROG=${PROG}"; exit 1 ;;
esac

SERVER_PID=""

if [ "${FUZZER}" = "AFL" ]; then
  AFL_BIN="/fuzzer/AFL/afl-fuzz"
  TARGET_BIN="${SETUP_DIR}/bin/AFL/${PROG}"

elif [ "${FUZZER}" = "AFL-PPO" ]; then
  AFL_BIN="/fuzzer/AFL-PPO/afl-fuzz"
  TARGET_BIN="${SETUP_DIR}/bin/AFL-PPO/${PROG}"

  export AFL_RL_SOCK="/tmp/afl_rl.sock"
  export AFL_RL_EFFECT=1

  echo "[ENTRY] starting PPO server..."
  ORIG_DIR="$(pwd)"
  cd "${OUTDIR}"

  python3 "${SCRIPT_DIR}/ppo_server.py" > "ppo_server.log" 2>&1 &
  SERVER_PID=$!

  cd "${ORIG_DIR}"
  sleep 1
else
  echo "[ENTRY] Unknown FUZZER=${FUZZER}"
  exit 1
fi

echo "[ENTRY] starting afl-fuzz..."
echo "[ENTRY] INPUT_DIR=${INPUT_DIR}"
echo "[ENTRY] TARGET_BIN=${TARGET_BIN} ${TARGET_ARGS}"

timeout "${TIME_SEC}" \
  "${AFL_BIN}" -m none -d -i "${INPUT_DIR}" -o "${OUTDIR}" -- \
  "${TARGET_BIN}" ${TARGET_ARGS} \
  >"${OUTDIR}/afl_fuzz.log" 2>&1 || true

echo "[ENTRY] afl-fuzz finished."

if [ "${FUZZER}" = "AFL-PPO" ] && [ -n "${SERVER_PID}" ]; then
  echo "[ENTRY] stopping PPO server (PID=${SERVER_PID})"
  kill "${SERVER_PID}" 2>/dev/null || true
fi

echo "[ENTRY] done."
