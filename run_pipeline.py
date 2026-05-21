"""
Run Phases 1–4 end-to-end (collection → analysis → report → Gmail draft).

Prerequisites:
  - .env configured (GROQ_API_KEY, MCP_SERVER_URL, EMAIL_RECIPIENT, GOOGLE_DOC_ID)
  - saksham-mcp-server running: uvicorn server:app --host 127.0.0.1 --port 8000
"""
import subprocess
import sys


def run(script: str) -> None:
    print(f"\n>>> Running {script}\n")
    result = subprocess.run([sys.executable, script], check=False)
    if result.returncode != 0:
        raise SystemExit(f"{script} failed with exit code {result.returncode}")


def main():
    run("run_gp_collect.py")
    run("run_phase2.py")
    run("run_phase3.py")
    run("run_phase4.py")
    print("\nPipeline complete.")


if __name__ == "__main__":
    main()
