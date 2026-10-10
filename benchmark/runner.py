"""Root CLI entrypoint for Patchwise Frozen Evaluation Benchmark."""
import asyncio
import os
import sys

# Ensure services/api is in the Python search path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API_SRC = os.path.join(REPO_ROOT, "services", "api")
if API_SRC not in sys.path:
    sys.path.insert(0, API_SRC)

from src.benchmark.runner import run_benchmark_cli

if __name__ == "__main__":
    asyncio.run(run_benchmark_cli())
