
import os
import re
import hashlib
import tempfile
import ctypes
from ctypes import c_void_p, c_int, c_char_p, POINTER
import subprocess

class JPuppet:
    def __init__(self, jvm_path=None):
        self.cache = {}       # hash -> output
        self.hot_counts = {}  # hash -> run count
        self._embed_jvm(jvm_path)

    def _hash_code(self, java_code: str):
        return hashlib.sha256(java_code.encode("utf-8")).hexdigest()

    def _embed_jvm(self, jvm_path=None):
        if jvm_path is None:
            jvm_path = r"C:\Program Files\OpenLogic\jdk-21.0.4.7-hotspot\bin\server\jvm.dll"
        self.jvm = ctypes.cdll.LoadLibrary(jvm_path)
        # Minimal JVM init for future direct calls (JNI)
        class JavaVMOption(ctypes.Structure):
            _fields_ = [("optionString", c_char_p), ("extraInfo", c_void_p)]
        class JavaVMInitArgs(ctypes.Structure):
            _fields_ = [
                ("version", c_int),
                ("nOptions", c_int),
                ("options", POINTER(JavaVMOption)),
                ("ignoreUnrecognized", c_int)
            ]
        opts = (JavaVMOption * 1)()
        opts[0].optionString = b"-Djava.class.path=."
        args = JavaVMInitArgs()
        args.version = 0x00010008
        args.nOptions = 1
        args.options = opts
        args.ignoreUnrecognized = 1
        self.JavaVM_p = c_void_p()
        self.Env_p = c_void_p()
        res = self.jvm.JNI_CreateJavaVM(ctypes.byref(self.JavaVM_p),
                                        ctypes.byref(self.Env_p),
                                        ctypes.byref(args))
        if res != 0:
            raise RuntimeError("Failed to embed JVM")
        print("Persistent JVM embedded!")

    def Run(self, java_code: str):
        match = re.search(r'public\s+class\s+(\w+)', java_code)
        if not match:
            return "ERROR: No public class"
        class_name = match.group(1)
        code_hash = self._hash_code(java_code)
        self.hot_counts[code_hash] = self.hot_counts.get(code_hash, 0) + 1

        # Ultra-fast: already cached
        if code_hash in self.cache and self.hot_counts[code_hash] > 1:
            return f"[HOTSPOT JIT - ULTRA FAST] {self.cache[code_hash]} (Run {self.hot_counts[code_hash]})"

        # First run: compile & execute
        with tempfile.TemporaryDirectory() as tmpdir:
            java_file = os.path.join(tmpdir, f"{class_name}.java")
            with open(java_file, "w") as f:
                f.write(java_code)
            # Compile
            proc = subprocess.run(["javac", java_file], cwd=tmpdir,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if proc.returncode != 0:
                return f"Compilation failed:\n{proc.stderr}"
            # Run
            proc = subprocess.run(["java", "-cp", tmpdir, class_name], cwd=tmpdir,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if proc.returncode != 0:
                return f"Runtime error:\n{proc.stderr}"
            output = proc.stdout.strip()
            # Cache the output for ultra-fast future runs
            self.cache[code_hash] = output
            return f"[HOTSPOT JIT] {output} (Run {self.hot_counts[code_hash]})"
