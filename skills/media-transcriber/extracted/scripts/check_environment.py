#!/usr/bin/env python3
"""Read-only dependency inventory; does not download models or inspect credentials."""

import argparse
import importlib.util
import json
import os
import platform
import shutil
import sys
from pathlib import Path


def module_present(name):
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def inspect_environment(task):
    # Prefer executables beside the Python used to run this checker (e.g. a venv).
    search_path = str(Path(sys.executable).parent) + os.pathsep + os.environ.get("PATH", "")
    commands = {name: shutil.which(name, path=search_path)
                for name in ("yt-dlp", "ffmpeg", "ffprobe", "lark-cli")}
    packages = {name: module_present(name)
                for name in ("yt_dlp", "faster_whisper", "mlx_whisper")}
    apple_silicon = (platform.system() == "Darwin"
                     and platform.machine().lower() in ("arm64", "aarch64"))
    engines = []
    if packages["faster_whisper"]:
        engines.append("faster-whisper")
    if packages["mlx_whisper"] and apple_silicon and commands["ffmpeg"]:
        engines.append("mlx")

    missing = []
    if task != "text" and sys.version_info < (3, 9):
        missing.append("Python 3.9+ for bundled scripts")
    if task == "url" and not (commands["yt-dlp"] or packages["yt_dlp"]):
        missing.append("yt-dlp for the local download route")
    if task == "local-asr":
        if not engines:
            missing.append("faster-whisper, or mlx-whisper + Apple Silicon + ffmpeg")
        if not commands["ffprobe"]:
            missing.append("ffprobe for media inspection")

    return {
        "status": "inventory_complete",
        "task": task,
        "python": {"version": platform.python_version(), "executable": sys.executable},
        "system": {"os": platform.system(), "machine": platform.machine()},
        "commands": commands,
        "packages_detected_in_this_python": packages,
        "local_asr_candidates_not_execution_tested": engines,
        "missing_for_requested_local_route": missing,
        "host_tools": "Assistant must inspect available file/browser/transcription/Feishu tools separately.",
        "limits": [
            "Presence is not proof of successful import, transcription or platform access.",
            "Model cache, GPU runtime and account permissions were not checked.",
            "No installations, downloads, media uploads or credential reads were performed.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", required=True,
                        choices=("text", "subtitles", "url", "local-asr"))
    args = parser.parse_args()
    print(json.dumps(inspect_environment(args.task), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
