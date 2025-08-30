



import os
import re
import subprocess
import tempfile
import sqlite3
import hashlib

class JPuppet:
    def __init__(self):
        self.db_path = os.path.join(tempfile.gettempdir(), "jpuppet_hotspot.db")
        self.cache = {}   # HotSpot-like cache
        self.hot_counts = {}  # Track how many times a class ran
        self._init_db()
        self._load_cache()

    # DB Initialization
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS jit_cache (
                hash TEXT PRIMARY KEY,
                class_name TEXT,
                java_code TEXT,
                output TEXT
            )
        """)
        conn.commit()
        conn.close()

    # Load DB cache into memory
    def _load_cache(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        for row in c.execute("SELECT hash, class_name, java_code, output FROM jit_cache"):
            self.cache[row[0]] = {
                "class_name": row[1],
                "java_code": row[2],
                "output": row[3]
            }
            self.hot_counts[row[0]] = 0
        conn.close()

    # Hash Java code
    def _hash_code(self, java_code: str) -> str:
        return hashlib.sha256(java_code.encode("utf-8")).hexdigest()

    # Store cache
    def _store_cache(self, code_hash: str, class_name: str, java_code: str, output: str):
        self.cache[code_hash] = {
            "class_name": class_name,
            "java_code": java_code,
            "output": output
        }
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO jit_cache VALUES (?, ?, ?, ?)",
                  (code_hash, class_name, java_code, output))
        conn.commit()
        conn.close()

    # Run Java code (HotSpot-style)
    def Run(self, java_code: str) -> str:
        match = re.search(r'public\s+class\s+(\w+)', java_code)
        if not match:
            return "ERROR: Could not find public class declaration"
        class_name = match.group(1)
        code_hash = self._hash_code(java_code)

        # Increment hot count
        self.hot_counts[code_hash] = self.hot_counts.get(code_hash, 0) + 1

        # First run or cache miss: compile & execute
        if code_hash not in self.cache:
            with tempfile.TemporaryDirectory() as temp_dir:
                java_file = os.path.join(temp_dir, f"{class_name}.java")
                with open(java_file, "w", encoding="utf-8") as f:
                    f.write(java_code)

                # Compile
                compile_proc = subprocess.run(
                    ["javac", java_file],
                    cwd=temp_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                if compile_proc.returncode != 0:
                    return f"Compilation failed:\n{compile_proc.stderr}"

                # Run
                run_proc = subprocess.run(
                    ["java", "-cp", temp_dir, class_name],
                    cwd=temp_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                if run_proc.returncode != 0:
                    return f"Runtime error:\n{run_proc.stderr}"

                output = run_proc.stdout.strip()
                self._store_cache(code_hash, class_name, java_code, output)
                return f"[HOTSPOT JIT] {output} (Run {self.hot_counts[code_hash]})"

        # HotSpot-style optimization: after 2+ runs, return cached instantly
        if self.hot_counts[code_hash] > 1:
            return f"[HOTSPOT JIT - OPTIMIZED] {self.cache[code_hash]['output']} (Run {self.hot_counts[code_hash]})"

        # Otherwise, normal run (first run after compile)
        with tempfile.TemporaryDirectory() as temp_dir:
            java_file = os.path.join(temp_dir, f"{class_name}.java")
            with open(java_file, "w", encoding="utf-8") as f:
                f.write(java_code)
            compile_proc = subprocess.run(
                ["javac", java_file],
                cwd=temp_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            if compile_proc.returncode != 0:
                return f"Compilation failed:\n{compile_proc.stderr}"
            run_proc = subprocess.run(
                ["java", "-cp", temp_dir, class_name],
                cwd=temp_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            if run_proc.returncode != 0:
                return f"Runtime error:\n{run_proc.stderr}"
            output = run_proc.stdout.strip()
            return f"[HOTSPOT JIT] {output} (Run {self.hot_counts[code_hash]})"
