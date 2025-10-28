import os
import subprocess
import time
import argparse
import json
import shlex
from pathlib import Path

BASELINE_ROOT = "/home/junghanbee/다운로드/SMART-LLM-master"
IMPROVED_ROOT = "/home/junghanbee/바탕화면/hanbee/SMART-LLM-master/SMART-LLM"

def run_cmd(cmd, cwd=None):
    start = time.time()
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    end = time.time()
    return proc.returncode, proc.stdout, proc.stderr, end - start

def run_cmd_heartbeat(cmd, cwd=None, tag="task", interval_sec=5, status_dir=None):
    """Run a command with periodic heartbeat and status.json updates.
    Stdout/stderr are redirected to files to avoid pipe blocking; returned as strings.
    """
    start = time.time()
    os.makedirs(status_dir or cwd or ".", exist_ok=True)
    out_path = Path(status_dir or cwd or ".") / f"{tag.replace(':','_')}.out"
    err_path = Path(status_dir or cwd or ".") / f"{tag.replace(':','_')}.err"
    status_path = Path(status_dir or cwd or ".") / f"{tag.replace(':','_')}.status.json"

    with open(out_path, 'w') as fout, open(err_path, 'w') as ferr:
        proc = subprocess.Popen(cmd, cwd=cwd, stdout=fout, stderr=ferr)
        last = -1
        try:
            while True:
                rc = proc.poll()
                elapsed = int(time.time() - start)
                if interval_sec > 0 and elapsed % interval_sec == 0 and elapsed != last:
                    print(f"[CMP][{tag}] alive | elapsed={elapsed}s | pid={proc.pid}")
                    # write status
                    try:
                        with open(status_path, 'w') as f:
                            json.dump({
                                "tag": tag,
                                "pid": proc.pid,
                                "alive": rc is None,
                                "elapsed_sec": elapsed,
                                "updated_at": int(time.time())
                            }, f)
                    except Exception:
                        pass
                    last = elapsed
                if rc is not None:
                    total = int(time.time() - start)
                    print(f"[CMP][{tag}] finished | elapsed={total}s | exit_code={rc}")
                    break
                time.sleep(1)
        except KeyboardInterrupt:
            proc.terminate()
            print(f"[CMP][{tag}] terminated by user")

    # read outputs
    stdout = Path(out_path).read_text() if Path(out_path).exists() else ""
    stderr = Path(err_path).read_text() if Path(err_path).exists() else ""
    end = time.time()
    return proc.returncode if 'proc' in locals() else -1, stdout, stderr, end - start

def discover_latest_log(root):
    logs_dir = Path(root) / "logs"
    if not logs_dir.exists():
        return None
    entries = sorted([p for p in logs_dir.iterdir() if p.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True)
    return entries[0].name if entries else None

def parse_metrics(executable_stdout: str):
    sr = tc = gcr = exec_ratio = ru = None
    for line in executable_stdout.splitlines():
        if line.startswith("SR:") or " SR:" in line:
            # 예: SR:0, TC:1, GCR:1.0, Exec:1.0, RU:2.0
            try:
                parts = line.replace(" ", "").split(",")
                sr = float(parts[0].split(":")[1])
                tc = float(parts[1].split(":")[1])
                gcr = float(parts[2].split(":")[1])
                exec_ratio = float(parts[3].split(":")[1])
                ru = float(parts[4].split(":")[1])
            except Exception:
                pass
    return dict(sr=sr, tc=tc, gcr=gcr, exec=exec_ratio, ru=ru)

def run_pipeline(root: str, floor_plan: int, model: str, disable_critic: bool, hb_interval: int, status_dir: str, prefix: str):
    # Use improved venv to satisfy dependencies for both roots
    venv_activate = f"source {IMPROVED_ROOT}/unified/bin/activate"

    # Snapshot logs before generation
    logs_dir = Path(root) / "logs"
    before = set([p.name for p in logs_dir.iterdir()]) if logs_dir.exists() else set()

    base_cmd = ["python3", "scripts/run_llm.py", "--floor-plan", str(floor_plan), "--model", model]
    if disable_critic:
        base_cmd.append("--disable-critic")
    shell_cmd = ["bash", "-lc", f"{venv_activate} && {shlex.join(base_cmd)}"]
    rc, out, err, gen_sec = run_cmd_heartbeat(shell_cmd, cwd=root, tag=f"{prefix}:gen", interval_sec=hb_interval, status_dir=status_dir)

    # Fallback: remove --disable-critic if baseline doesn't support it
    if rc != 0 and disable_critic and ("unrecognized arguments" in err or "unrecognized" in out.lower() or "usage:" in out.lower()):
        fallback_cmd = ["python3", "scripts/run_llm.py", "--floor-plan", str(floor_plan), "--model", model]
        shell_cmd_fb = ["bash", "-lc", f"{venv_activate} && {shlex.join(fallback_cmd)}"]
        rc, out, err, gen_sec = run_cmd_heartbeat(shell_cmd_fb, cwd=root, tag=f"{prefix}:gen", interval_sec=hb_interval, status_dir=status_dir)

    # Determine newly created log folder
    after = set([p.name for p in logs_dir.iterdir()]) if logs_dir.exists() else set()
    new_logs = sorted(list(after - before))
    latest = new_logs[-1] if new_logs else discover_latest_log(root)
    exe_out = ""
    exe_sec = None
    if latest:
        exec_cmd = ["bash", "-lc", f"{venv_activate} && python3 scripts/execute_plan.py --command {shlex.quote(latest)}"]
        rc2, out2, err2, exe_sec = run_cmd_heartbeat(exec_cmd, cwd=root, tag=f"{prefix}:exec", interval_sec=hb_interval, status_dir=status_dir)
        exe_out = out2 + "\n" + err2
    return {
        "log_folder": latest,
        "gen_sec": gen_sec,
        "exe_sec": exe_sec,
        "exe_metrics": parse_metrics(exe_out),
        "gen_stdout_head": "\n".join(out.splitlines()[:80])
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--floor-plan", type=int, default=21)
    parser.add_argument("--model", type=str, default="ollama:llama3")
    parser.add_argument("--disable-critic", action="store_true")
    parser.add_argument("--heartbeat-interval", type=int, default=5, help="heartbeat seconds (0 to disable)")
    parser.add_argument("--status-dir", type=str, default=None, help="directory to write comparison status files")
    args = parser.parse_args()

    status_dir = args.status_dir or (Path(IMPROVED_ROOT) / "logs").as_posix()

    print("[Baseline] Running at", BASELINE_ROOT)
    base = run_pipeline(BASELINE_ROOT, args.floor_plan, args.model, args.disable_critic, args.heartbeat_interval, status_dir, prefix="baseline")
    print("[Improved] Running at", IMPROVED_ROOT)
    imp = run_pipeline(IMPROVED_ROOT, args.floor_plan, args.model, args.disable_critic, args.heartbeat_interval, status_dir, prefix="improved")

    def fmt(m):
        return f"SR={m.get('sr')}, TC={m.get('tc')}, GCR={m.get('gcr')}, Exec={m.get('exec')}, RU={m.get('ru')}"

    print("\n===== COMPARISON =====")
    print(f"Baseline log: {base['log_folder']} | gen={base['gen_sec']:.1f}s, exe={base['exe_sec'] and round(base['exe_sec'],1)}s, metrics: {fmt(base['exe_metrics'])}")
    print(f"Improved log: {imp['log_folder']} | gen={imp['gen_sec']:.1f}s, exe={imp['exe_sec'] and round(imp['exe_sec'],1)}s, metrics: {fmt(imp['exe_metrics'])}")

if __name__ == "__main__":
    main()


