# scripts/run_realtime_demo.py
import os
import sys

# Make project root importable automatically
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.pipeline.realtime_loop import RealtimePipeline



def main():
    pipeline = RealtimePipeline()
    pipeline.run_forever()


if __name__ == "__main__":
    main()
