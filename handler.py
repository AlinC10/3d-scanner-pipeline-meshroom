import runpod
from main import run_pipeline

if __name__ == "__main__":
    runpod.serverless.start({"handler": run_pipeline})