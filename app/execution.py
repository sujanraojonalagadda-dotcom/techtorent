import os
import shutil
import subprocess
import tempfile
import time
from threading import Lock


execution_lock = Lock()


def run_code(language, code, stdin_data, timeout_seconds):
    code = (code or "").strip()
    if not code:
        return {"verdict": "Runtime Error", "stdout": "", "stderr": "Empty code is not allowed.", "time": 0.0}

    temp_dir = tempfile.mkdtemp(prefix="codesprint_")
    start = time.perf_counter()

    try:
        with execution_lock:
            if language == "python":
                result = _run_python(temp_dir, code, stdin_data, timeout_seconds)
            elif language == "c":
                result = _run_c(temp_dir, code, stdin_data, timeout_seconds)
            else:
                return {"verdict": "Runtime Error", "stdout": "", "stderr": "Unsupported language", "time": 0.0}

        result["time"] = round(time.perf_counter() - start, 4)
        return result
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _run_python(temp_dir, code, stdin_data, timeout_seconds):
    script_path = os.path.join(temp_dir, "main.py")
    guarded_code = "import sys\nsys.setrecursionlimit(10000)\n" + code
    with open(script_path, "w", encoding="utf-8") as handle:
        handle.write(guarded_code)

    try:
        proc = subprocess.run(
            ["python3", "-u", script_path],
            input=stdin_data,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return {"verdict": "Time Limit Exceeded", "stdout": "", "stderr": "Execution timed out."}

    if proc.returncode != 0:
        return {"verdict": "Runtime Error", "stdout": proc.stdout, "stderr": proc.stderr}
    return {"verdict": "OK", "stdout": proc.stdout, "stderr": proc.stderr}


def _run_c(temp_dir, code, stdin_data, timeout_seconds):
    source_path = os.path.join(temp_dir, "main.c")
    binary_path = os.path.join(temp_dir, "main.out")
    with open(source_path, "w", encoding="utf-8") as handle:
        handle.write(code)

    compile_proc = subprocess.run(
        ["gcc", source_path, "-O2", "-std=c11", "-o", binary_path],
        capture_output=True,
        text=True,
    )
    if compile_proc.returncode != 0:
        return {
            "verdict": "Compilation Error",
            "stdout": compile_proc.stdout,
            "stderr": compile_proc.stderr,
        }

    try:
        proc = subprocess.run(
            [binary_path],
            input=stdin_data,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return {"verdict": "Time Limit Exceeded", "stdout": "", "stderr": "Execution timed out."}

    if proc.returncode != 0:
        return {"verdict": "Runtime Error", "stdout": proc.stdout, "stderr": proc.stderr}

    return {"verdict": "OK", "stdout": proc.stdout, "stderr": proc.stderr}
