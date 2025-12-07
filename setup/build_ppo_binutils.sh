#!/bin/bash
set -euo pipefail

SETUP_DIR="/setup"
BUILD_ROOT="${SETUP_DIR}/build"
WORKDIR="${BUILD_ROOT}/binutils-ppo"

TARBALL="${SETUP_DIR}/binutils-2.26.tar.gz"
OUTDIR="${SETUP_DIR}/bin/AFL-PPO"

mkdir -p "${OUTDIR}" "${BUILD_ROOT}"
rm -rf "${WORKDIR}"

if [ ! -f "${TARBALL}" ]; then
  echo "[ERROR] ${TARBALL} not found"
  exit 1
fi

export LD=/usr/bin/ld
export AR=/usr/bin/ar
export AS=/usr/bin/as
export NM=/usr/bin/nm
export RANLIB=/usr/bin/ranlib

COMMON_CFLAGS="-g -fno-omit-frame-pointer -Wno-error"

export CC="/fuzzer/AFL-PPO/afl-clang-fast"
export CXX="/fuzzer/AFL-PPO/afl-clang-fast++"
export CFLAGS="${COMMON_CFLAGS}"
export CXXFLAGS="${COMMON_CFLAGS}"

cd "${BUILD_ROOT}"
tar -xzf "${TARBALL}"
mv binutils-2.26 "${WORKDIR}"

cd "${WORKDIR}"

CONFIG_OPTS="
  --disable-shared
  --disable-gdb
  --disable-libdecnumber
  --disable-readline
  --disable-sim
  --disable-ld
"

./configure ${CONFIG_OPTS}
ASAN_OPTIONS=detect_leaks=0 make -j

cp binutils/readelf "${OUTDIR}/"
cp binutils/objdump "${OUTDIR}/"

cd "${BUILD_ROOT}"
rm -rf "${WORKDIR}"

echo "[*] AFL-PPO binutils built into ${OUTDIR}"
