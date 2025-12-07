#!/bin/bash
set -euo pipefail

FUZZER_ROOT="/fuzzer"

echo "[*] Building AFL..."
cd "${FUZZER_ROOT}/AFL"

if [ -x /usr/bin/llvm-config-10 ]; then
  export LLVM_CONFIG=/usr/bin/llvm-config-10
else
  export LLVM_CONFIG=/usr/bin/llvm-config
fi

if [ -d /usr/lib/llvm-10/bin ]; then
  export PATH=/usr/lib/llvm-10/bin:$PATH
fi

make -j
cd llvm_mode
make -j

echo "[*] Building AFL-PPO..."
cd "${FUZZER_ROOT}/AFL-PPO"
export CFLAGS="${CFLAGS:-} -std=gnu99"
make -j
cd llvm_mode
make -j

echo "[*] Done building AFL and AFL-PPO."