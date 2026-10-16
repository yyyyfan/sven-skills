---
name: hf-to-obs-transfer
description: Use when downloading Hugging Face datasets or models and uploading them to Huawei Cloud OBS, or when tuning that pipeline for speed.
---
# Hugging Face → Huawei OBS transfer

Reusable pipeline for downloading from Hugging Face and uploading to OBS with the settings measured fastest on a typical Grok Bot box (HF ~600 MB/s download; OBS ~35 MB/s per `obsutil` process, ~70+ MB/s with 3 parallel upload processes).

## Prerequisites

1. **obsutil** installed and configured (`~/.obsutilconfig` with endpoint, AK, SK). If missing, install the Linux amd64 package from Huawei OBS docs and run `obsutil config`.
2. **hf CLI**: prefer an existing venv (e.g. `/workspace/hfenv`) with `huggingface_hub[cli]`; otherwise `python3 -m venv /workspace/hfenv && /workspace/hfenv/bin/pip install -U "huggingface_hub[cli]"`.
3. Disk: keep free space ≥ 2–3× one shard size if pipelining; delete each local file after its upload succeeds.
4. Confirm with the user: HF repo id + `--repo-type` (dataset/model), include/exclude globs, OBS bucket and prefix (e.g. `obs://bucket/path/`).

## Best settings (from box benchmarks)

| Stage | Setting | Notes |
|---|---|---|
| HF download | `--max-workers 8` | Faster than 4 or 16; `HF_HUB_ENABLE_HF_TRANSFER` / Xet high-perf flags usually do not help on current huggingface_hub |
| OBS single file | `-p=16 -ps=16777216` (16 parts × 16MB) | 24 parts is slower; single-process ceiling ~34 MB/s |
| OBS throughput | **3 parallel `obsutil` processes**, one file each | Beats one process with `-j`; pipeline: start upload as soon as each shard finishes downloading |

Rough capacity: ~26 min per 100GB end-to-end with pipelined parallel uploads; ~50 min/100GB if only one upload process.

## Steps

### 1. Download

```bash
source /workspace/hfenv/bin/activate   # or equivalent
hf download <repo_id> \
  --repo-type <dataset|model> \
  --include "<glob>" \
  --local-dir /workspace/hf-data/<repo_slug> \
  --max-workers 8
```

For gated repos, set `HF_TOKEN` from a secret the user provided (never print it).

### 2. Upload (prefer pipelined parallel)

**Pipelined (best):** as each shard lands, upload it in the background; keep at most 3 uploads in flight; delete local file after success.

```bash
OBS_DEST="obs://<bucket>/<prefix>/"
find /workspace/hf-data/<repo_slug> -type f ! -name '*.incomplete' | \
  xargs -P 3 -I{} sh -c '
    f="$1"
    obsutil cp "$f" "$OBS_DEST" -f -p=16 -ps=16777216 && rm -f "$f"
  ' _ {}
```

**Simple directory upload** (slower ceiling ~34 MB/s):

```bash
obsutil cp /workspace/hf-data/<repo_slug> obs://<bucket>/<prefix>/ -r -f -p=16 -ps=16777216
```

### 3. Verify and clean

```bash
obsutil ls obs://<bucket>/<prefix>/ -d
# confirm object count / bytes match download
rm -rf /workspace/hf-data/<repo_slug>
```

## Progress and reporting

- Log download and upload timings (`date +%s` or Python) and report size, duration, MB/s, and ETA for remaining work.
- Do not stream a live progress bar into chat; give milestone updates (started, N% done, finished with table).
- Never echo AK/SK or tokens in logs or replies.

## Optional: quick re-benchmark

If the box or region changes, re-test with ~2GB shards: HF workers 4/8/16; OBS `-p` 8/16/24 and `-ps` 8MB/16MB; then 2–3 parallel upload processes. Keep the best flags in this skill only if they clearly beat the defaults above.
