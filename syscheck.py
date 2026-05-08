#!/usr/bin/env python3
"""System health check - run autonomously by Claude Code."""
import subprocess, json, sys, shutil
from pathlib import Path

report = {"status": "ok", "issues": [], "warnings": [], "info": []}

# Disk space
for p in [Path.home(), Path("/")]:
    usage = shutil.disk_usage(p)
    pct = usage.used / usage.total * 100
    report["info"].append(f"{p}: {usage.free//(1024**3)}GB free / {usage.total//(1024**3)}GB total ({pct:.0f}%)")
    if pct > 85:
        report["warnings"].append(f"Disk {p} is {pct:.0f}% full")

# Git repos with uncommitted changes
for root in [Path.home() / "Workspace", Path.home() / "Documents"]:
    if not root.exists():
        continue
    for gitdir in root.rglob(".git"):
        if gitdir.is_dir():
            repo = gitdir.parent
            r = subprocess.run(["git", "-C", str(repo), "status", "--porcelain"], capture_output=True, text=True)
            if r.stdout.strip():
                report["info"].append(f"Dirty repo: {repo}")

# Brew outdated
try:
    r = subprocess.run(["brew", "outdated", "--json"], capture_output=True, text=True, timeout=30)
    outdated = json.loads(r.stdout) if r.stdout.strip() else []
    if len(outdated) > 5:
        report["warnings"].append(f"{len(outdated)} brew packages outdated")
    else:
        report["info"].append(f"{len(outdated)} brew packages outdated")
except:
    pass

# Node/npm version
for cmd, name in [("node", "--version"), ("npm", "--version"), ("python3", "--version")]:
    try:
        r = subprocess.run([cmd, name.split()[-1].lstrip("-")] if " " in name else [cmd, name], capture_output=True, text=True, timeout=5)
        report["info"].append(f"{cmd}: {r.stdout.strip()}")
    except:
        report["info"].append(f"{cmd}: not found")

# Memory pressure (macOS)
try:
    r = subprocess.run(["memory_pressure"], capture_output=True, text=True, timeout=5)
    for line in r.stdout.splitlines():
        if "free" in line.lower():
            report["info"].append(f"Memory: {line.strip()}")
except:
    pass

print(json.dumps(report, indent=2))
