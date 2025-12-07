# AFL vs AFL-PPO for Fuzzing binutils

이 저장소는 **vanilla AFL**과 **PPO 기반 스케줄러를 적용한 AFL-PPO**를
`binutils-2.26` 타깃(`readelf`, `objdump`)에 대해 비교 실험하기 위한 작은 프레임워크다.

모든 실험은 Docker 컨테이너 내부에서 수행된다.
호스트에서는 Docker와 Python만 설치되어 있으면 된다.

⭐⭐⭐ 잘 모르겠으면 **1.사전준비, 2.리포지토리 클론** 단계 수행 후 **6.주요 실험 재현 방법** 을 그대로 따라하면 된다⭐⭐⭐

---

## 📁 Repository 구조

```text
experiment-tools/
├── AFL/                     # AFL (git submodule)
├── AFL-PPO/                 # AFL-PPO (git submodule, RL 기능 추가 버전)
├── Dockerfile               # 실험용 Docker 이미지 빌드 파일
├── README.md                # 이 문서
├── build.sh                 # Docker 이미지 빌드 스크립트
├── reproduce.py             # Docker 컨테이너에서 실험 실행
├── script/
│   ├── analyze_results.py            # fuzzer_stats / PPO 로그 집계 → summary.json / ppo_summary.json
│   ├── compare_multi_from_summary.py # summary.json 기반 aggregate metric bar plot + Markdown 테이블 출력
│   ├── compare_time_series.py        # plot_data 기반 coverage / execs/sec time-series 평균 커브 비교
│   ├── plot_ppo_stats.py             # PPO action / steps / reward 통계 플롯
│   ├── entry.sh                      # 컨테이너 내부 실행 entrypoint
│   └── ppo_server.py                 # PPO 에이전트(PyTorch)
└── setup/
    ├── binutils-2.26.tar.gz          # 벤치마크 소스
    ├── build_afl_binutils.sh         # AFL용 binutils 빌드
    ├── build_ppo_binutils.sh         # AFL-PPO용 binutils 빌드
    └── install_fuzzer.sh             # AFL / AFL-PPO 빌드
```

## 1. 사전 준비

### ✔ 호스트 OS

- Linux, macOS, 또는 Windows WSL2
- 본 프로젝트는 전부 Docker 안에서 돌아가기 때문에 먼저 Docker를 설치해야한다.

### ✔ 필요한 소프트웨어

- **Docker** (혹은 Docker Desktop)
- **Python 3**
- `git`

---

## 1.1 Docker 설치하기 (없을 경우)

#### 🔹 Ubuntu / Debian

설치 방법 (링크 참고할 것):
https://donotfear.tistory.com/106#google_vignette


---

#### 🔹 macOS

설치 방법 (링크 참고할 것):
https://gabrielyj.tistory.com/223#google_vignette


---

#### 🔹 Windows 10/11 (+WSL2)

설치 방법 (링크 참고할 것):
https://boksup.tistory.com/96


---

설치 확인:

```bash
docker run hello-world
```

---

## 2. 리포지토리 클론

이 프로젝트는 `AFL`과 `AFL-PPO`가 git submodule 로 포함되어 있다.

```bash
git clone --recursive <THIS_REPO_URL> experiment-tools
cd experiment-tools
```

만약 `--recursive`를 깜빡했다면:

```bash
git submodule update --init --recursive
```

## 3. Docker 이미지 빌드

### 3.1 이미지 빌드

리포지토리 루트에서 실행:

```bash
cd experiment-tools
./build.sh
```

`build.sh`는 내부적으로 다음 명령을 실행한다:

```bash
docker build \
  --build-arg UID=$(id -u) \
  --build-arg GID=$(id -g) \
  -t rl-project -f Dockerfile .
```

---

### 3.2 Dockerfile에서 수행하는 작업 요약

- 베이스 이미지: `ubuntu:20.04`
- 필수 패키지 설치:
  - build-essential, clang, llvm, python3, python3-pip, zlib1g-dev 등
- Python 패키지 설치:
  - torch, numpy (CPU 버전)
- 코드/스크립트 복사:
  - AFL → `/fuzzer/AFL`
  - AFL-PPO → `/fuzzer/AFL-PPO`
  - setup/ → `/setup`
  - script/ → `/script`
- 빌드 스크립트 실행:
  - `/setup/install_fuzzer.sh` → AFL 및 AFL-PPO 빌드
  - `/setup/build_afl_binutils.sh`
  - `/setup/build_ppo_binutils.sh`

이미지가 성공적으로 빌드되면 이름은 **rl-project**이며, 이후 모든 실험은 이 이미지를 기반으로 수행된다.

---

## 4. 실험 실행

실험 실행은 `reproduce.py`가 Docker 컨테이너를 자동으로 띄워서 진행한다.
컨테이너 내부에서는 `/script/entry.sh`가 실험을 실제로 수행한다.

---

### 4.1 기본 실행 예시

```bash
./reproduce.py \
  --fuzzer AFL \
  --prog readelf \
  --num-runs 5 \
  --max-parallel 2 \
  --time-sec 3600 \
  --output output/AFL_readelf
```

#### 주요 인자 설명

- `--fuzzer`
  - AFL, AFL-PPO, 또는 both
- `--prog`
  - readelf 또는 objdump
- `--num-runs`
  - 동일 설정을 seed만 다르게 반복 실행
- `--max-parallel`
  - 동시에 몇 개의 컨테이너를 띄울지
- `--time-sec`
  - 각 run 의 퍼징 시간(초)
- `--output`
  - 결과 저장 위치 (컨테이너에서는 `/output` 으로 마운트됨)

---

### 4.2 AFL-PPO 실행 (하이퍼파라미터 포함)

```bash
./reproduce.py \
  --fuzzer AFL-PPO \
  --prog readelf \
  --num-runs 5 \
  --max-parallel 2 \
  --time-sec 3600 \
  --output output/AFL-PPO_readelf_lr1e-4_g0.99_c0.2 \
  --lr 1e-4 \
  --gamma 0.99 \
  --clip 0.2
```

#### 전달되는 환경변수

- `--lr` → `RL_LR`
- `--gamma` → `RL_GAMMA`
- `--clip` → `RL_CLIP`

**중요:**
각 fuzzer / prog / hyperparameter 조합마다 다른 output 디렉토리를 주어야 분석이 깔끔하다.

예:

- output/AFL_readelf
- output/AFL-PPO_readelf_lr1e-4_g0.99_c0.2
- output/AFL-PPO_readelf_lr5e-5_g0.99_c0.3

---

### 4.3 컨테이너 내부 실행 흐름 (entry.sh)

`reproduce.py`는 다음과 같이 컨테이너를 띄운다:

```bash
docker run \
  -d --rm \
  -v <HOST_OUTPUT_DIR>:/output \
  -e RL_LR=... -e RL_GAMMA=... -e RL_CLIP=... \
  rl-project \
  /script/entry.sh <FUZZER> <PROG> <RUN_ID> <TIME_SEC>
```

컨테이너 내부에서 수행되는 작업:

1. AFL 공통 환경 변수 설정

```bash
export AFL_SKIP_CPUFREQ=1
export AFL_NO_UI=1
export AFL_NO_AFFINITY=1
export AFL_SKIP_CRASHES=1
export AFL_SEED=$((1234 + RUN_ID))
```

2. 입력 corpus 준비
   `/fuzzer/AFL/testcases/others/elf`

3. 타깃 선택

- AFL → `/setup/bin/AFL/readelf` or `/setup/bin/AFL/objdump`
- AFL-PPO → `/setup/bin/AFL-PPO/readelf` or `/setup/bin/AFL-PPO/objdump`

4. AFL-PPO일 경우 PPO 서버 실행:

- `ppo_server.py` 동작
- 로그 생성:
  - ppo_log.csv
  - ppo_server.log

5. 퍼징 실행:

```bash
timeout "${TIME_SEC}" \
  "${AFL_BIN}" -m none -d -i "${INPUT_DIR}" -o "${OUTDIR}" -- \
  "${TARGET_BIN}" ${TARGET_ARGS} \
  >"${OUTDIR}/afl_fuzz.log" 2>&1 || true
```

6. 종료 시 PPO 프로세스 정리

---

### 4.4 Output 디렉토리 구조

예시:

```
output/
  AFL-PPO_readelf_lr1e-4_g0.99_c0.2/
    AFL-PPO_readelf_0/
      fuzzer_stats
      plot_data
      afl_fuzz.log
      ppo_log.csv
      ppo_server.log
    AFL-PPO_readelf_1/
    AFL-PPO_readelf_2/
```

AFL은 동일한 구조지만 PPO 관련 로그는 없다.

---

## 5. 분석 스크립트

모든 분석 스크립트는 `script/` 에 있다.

---

### 5.1 analyze_results.py — aggregate fuzzer_stats & PPO logs

각 실험 디렉토리(예: `output/AFL_readelf`) 아래 run별 디렉토리에서:

- `fuzzer_stats`를 읽어서 metric별 통계를 계산하고 `summary.json` 생성
- AFL-PPO의 경우 `ppo_log.csv`, `ppo_server.log`를 읽어서 PPO 통계를 `ppo_summary.json`에 저장한다.

사용법 예시:

```bash
# AFL 결과 요약
./script/analyze_results.py --dir output/AFL_readelf

# AFL-PPO 결과 요약 (예: 기본 설정)
./script/analyze_results.py --dir output/AFL-PPO_readelf_lr1e-4_g0.99_c0.2
```

`summary.json`에는 다음 형식으로 avg / median / min / max / raw 가 들어간다:

```json
{
  "paths_total": {
    "avg": 1234.5,
    "median": 1200.0,
    "min": 900.0,
    "max": 1600.0,
    "raw": [ ... ]
  },
  ...
}
```

AFL-PPO의 경우 `ppo_summary.json` 에는 대략 이런 정보가 들어간다:

- `steps_per_run`: 각 run별 PPO step 수
- `avg_action_hist`: 액션 histogram의 평균
- `final_action_hists`: run별 최종 action histogram 등

---

### 5.2 compare_multi_from_summary.py – 여러 실험의 aggregate metric을 한 번에 비교 (bar plot + Markdown 테이블)

각 실험 디렉토리(`summary.json` 존재)를 모아서:

- metric별 평균값을 bar chart로 그리고 (`<metric>.png`)
- 동일한 내용을 **Markdown 테이블로 stdout에 출력**해 준다
  (논문/리포트에 그대로 복붙해서 쓸 수 있음).

가정:

- `summary.json` 구조는 5.1에서 설명한 것과 동일
- 첫 번째 디렉토리가 baseline (보통 AFL) 이고, 나머지는 비교 대상

사용 예시:

```bash
./script/compare_multi_from_summary.py \
  --dirs output/AFL_readelf \
         output/AFL-PPO_readelf_lr1e-4_g0.99_c0.2 \
         output/AFL-PPO_readelf_lr5e-5_g0.99_c0.3 \
  --labels AFL \
          PPO-base \
          PPO-tuned \
  --outdir plots_readelf \
  --title-prefix readelf
```

주요 옵션:

- `--dirs` : `summary.json` 이 들어 있는 실험 디렉토리들
- `--labels` : 각 디렉토리에 대응하는 라벨 (그래프 legend / 테이블 헤더용)
- `--metrics` : 비교할 metric 이름 목록 (기본: paths_total, bitmap_cvg, execs_per_sec, execs_done, pending_total, pending_favs, unique_crashes, unique_hangs)
- `--outdir` : PNG 저장 디렉토리 (없으면 생성됨)
- `--title-prefix` : 플롯 제목에 앞에 붙일 문자열 (예: readelf, objdump)

출력 예시:

- `plots_readelf/paths_total.png`
- `plots_readelf/bitmap_cvg.png`
- `plots_readelf/execs_per_sec.png`
- …

각 bar 위에는:

- 해당 설정의 평균값 (`v`)
- baseline(AFL) 대비 Δ% (`(v - baseline) / baseline * 100`)

이 두 줄이 텍스트로 같이 표시된다.

터미널에는 metric마다 이런 형식의 Markdown 테이블이 찍힌다:

```markdown
| metric | AFL (avg) | PPO-base (avg) | PPO-tuned (avg) |
| --- | --- | --- | --- |
| paths_total | 1200.00 | 1350.00 | 1400.00 |
| Δ vs AFL (%) |  | +12.5% | +16.7% |
```

---

### 5.3 compare_time_series.py – coverage / execs/sec time-series 비교 (plot_data 기반)

여러 실험의 `plot_data` 파일들을 모아서:

- run별 time-series 를 공통 시간축으로 보간하고 평균을 낸 뒤
- coverage / execs/sec 에 대해 시간에 따른 변화를 한 눈에 비교할 수 있는 플롯을 만든다.

가정:

- 각 실험 디렉토리 구조가 다음과 같음:
  - `output/AFL_readelf/AFL_readelf_0/plot_data`
  - `output/AFL_readelf/AFL_readelf_1/plot_data`
  - …
- `plot_data` 포맷은 AFL 기본 형식:
  - `unix_time, cycles_done, cur_path, paths_total, pending_total, pending_favs, map_size, unique_crashes, unique_hangs, max_depth, execs_per_sec`

사용 예시:

```bash
./script/compare_time_series.py \
  --cfg output/AFL_readelf \
        output/AFL-PPO_readelf_lr1e-4_g0.99_c0.2 \
        output/AFL-PPO_readelf_lr5e-5_g0.99_c0.3 \
  --labels AFL \
          PPO-base \
          PPO-tuned \
  --out timeseries_readelf \
  --title-prefix readelf \
  --bin-sec 5
```

주요 옵션:

- `--cfg` : 실험 루트 디렉토리들 (각각 여러 run 하위 디렉토리를 포함)
- `--labels` : 각 실험에 대한 라벨 (legend에 쓰임, `--cfg` 개수와 동일해야 함)
- `--out` : PNG를 저장할 디렉토리
- `--title-prefix` : 플롯 제목 앞에 붙일 prefix (예: readelf, objdump)
- `--bin-sec` : time axis 보간 간격(초). 기본 5초로 샘플링해서 평균 커브를 그림.

출력 예시 (`--out timeseries_readelf`):

- `timeseries_readelf/coverage_full.png`
  - 전체 시간 구간에서 coverage 시간변화 (모든 설정 한 그래프에)
- `timeseries_readelf/coverage_zoom_0_800.png`
  - 초기 0~800초 구간 확대
- `timeseries_readelf/coverage_zoom_2000_end.png`
  - 후반부 2000초 이후 구간 확대
- `timeseries_readelf/execs_per_sec_over_time.png`
  - execs/sec vs time (평균 커브)

---

### 5.4 plot_ppo_stats.py – PPO action / steps / reward 통계 시각화

PPO 기반 실험들에 대해서:

- action histogram (모든 variant를 한 그래프에)
- steps_per_run boxplot (variant별 step 분포)
- reward curve (time-series 평균 + moving average)
- run별 average reward boxplot

을 그려주는 스크립트다.

필요한 입력:

- 각 PPO 실험 디렉토리 루트에 `ppo_summary.json` 이 있어야 함
- 그 아래 run 디렉토리 안에 `ppo_log.csv` 가 있어야 함

사용 예시:

```bash
./script/plot_ppo_stats.py \
  --dirs base=output/AFL-PPO_readelf_lr1e-4_g0.99_c0.2 \
         tuned=output/AFL-PPO_readelf_lr5e-5_g0.99_c0.3 \
  --outdir ppo_readelf \
  --reward-window 50
```

옵션:

- `--dirs` : `label=dir` 형식으로 여러 개 전달
  - `label` 은 그래프 legend / 축 라벨 등에 사용됨
  - `dir` 은 해당 PPO 실험의 루트 디렉토리 (`ppo_summary.json`, `ppo_log.csv` 들이 들어 있음)
- `--outdir` : PNG 저장 디렉토리
- `--reward-window` : reward curve smoothing을 위한 moving average window 크기 (기본 50 step)

출력 예시 (`--outdir ppo_readelf`):

- `ppo_readelf/ppo_action_hist_all.png`
  - x축: A0/A1/A2/A3 (4개 action)
  - 막대: variant별 평균 action count (모든 run 평균)
- `ppo_readelf/ppo_steps_boxplot.png`
  - variant별 steps_per_run 분포 boxplot
- `ppo_readelf/ppo_reward_curve.png`
  - 각 variant에 대해 run별 reward 시퀀스를 잘라 global_min 길이 맞춘 뒤, 평균 내고 moving average 적용한 reward curve
- `ppo_readelf/ppo_reward_boxplot.png`
  - run별 average reward 분포 boxplot

---

## 6. 주요 실험 재현 방법

### 6.1 Docker 이미지 빌드

```bash
./build.sh
```

---

### 6.2 AFL baseline 실행

```bash
./reproduce.py \
  --fuzzer AFL \
  --prog readelf \
  --num-runs 5 \
  --max-parallel 5 \
  --time-sec 3600 \
  --output output/AFL_readelf
```

---

### 6.3 AFL-PPO 기본 설정 실행

```bash
./reproduce.py \
  --fuzzer AFL-PPO \
  --prog readelf \
  --num-runs 5 \
  --max-parallel 5 \
  --time-sec 3600 \
  --output output/AFL-PPO_readelf_lr1e-4_g0.99_c0.2 \
  --lr 1e-4 --gamma 0.99 --clip 0.2
```

---

### 6.4 summary / PPO summary 생성

```bash
./script/analyze_results.py --dir output/AFL_readelf
./script/analyze_results.py --dir output/AFL-PPO_readelf_lr1e-4_g0.99_c0.2
./script/analyze_results.py --dir output/AFL-PPO_readelf_lr5e-5_g0.99_c0.3
```

각 디렉토리에:

- `summary.json`
- (PPO의 경우) `ppo_summary.json`

이 생성된다.

---

### 6.5 aggregate metric 비교 (bar plot + Markdown 테이블)

```bash
./script/compare_multi_from_summary.py \
  --dirs output/AFL_readelf \
         output/AFL-PPO_readelf_lr1e-4_g0.99_c0.2 \
         output/AFL-PPO_readelf_lr5e-5_g0.99_c0.3 \
  --labels AFL \
          PPO-base \
          PPO-tuned \
  --outdir plots_readelf \
  --title-prefix readelf
```

결과:

- `plots_readelf/*.png` : metric별 bar plot
- 터미널 출력: Markdown 테이블 (리포트에 그대로 복붙 가능)

---

### 6.6 time-series 비교 (coverage / execs/sec)

```bash
./script/compare_time_series.py \
  --cfg output/AFL_readelf \
        output/AFL-PPO_readelf_lr1e-4_g0.99_c0.2 \
        output/AFL-PPO_readelf_lr5e-5_g0.99_c0.3 \
  --labels AFL \
          PPO-base \
          PPO-tuned \
  --out timeseries_readelf \
  --title-prefix readelf \
  --bin-sec 5
```

결과:

- `timeseries_readelf/coverage_full.png`
- `timeseries_readelf/coverage_zoom_0_800.png`
- `timeseries_readelf/coverage_zoom_2000_end.png`
- `timeseries_readelf/execs_per_sec_over_time.png`

---

### 6.7 PPO 통계 시각화 (action / steps / reward)

```bash
./script/plot_ppo_stats.py \
  --dirs base=output/AFL-PPO_readelf_lr1e-4_g0.99_c0.2 \
         tuned=output/AFL-PPO_readelf_lr5e-5_g0.99_c0.3 \
  --outdir ppo_readelf \
  --reward-window 50
```

결과:

- `ppo_readelf/ppo_action_hist_all.png`
- `ppo_readelf/ppo_steps_boxplot.png`
- `ppo_readelf/ppo_reward_curve.png`
- `ppo_readelf/ppo_reward_boxplot.png`

까지 한 번에 얻을 수 있다.

---

## 7. Notes / 제한 사항

- 현재 타깃은 `binutils-2.26` 의 `readelf`, `objdump` 두 개뿐이다.
- 입력 corpus는 AFL 기본 제공 ELF 테스트 케이스를 사용한다.
- PPO 에이전트는 단순한 MLP 기반 정책/가치 함수이며 대규모 실험 최적화는 되어 있지 않다.
- 연구/수업용 프로토타입이며, 산업 환경 적용은 권장되지 않는다.
- Docker, WSL2, macOS 등 환경에 따라 동작이 달라질 수 있다.
