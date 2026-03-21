
import os
import subprocess
import sys

BASE_DIR = os.path.dirname(__file__)


def resolve_python() -> str:
    if sys.platform == "win32":
        venv_py = os.path.join(BASE_DIR, ".venv", "Scripts", "python.exe")
    else:
        venv_py = os.path.join(BASE_DIR, ".venv", "bin", "python")
    return venv_py if os.path.exists(venv_py) else sys.executable


def run_script(script_path: str, py_exe: str) -> bool:
    full_script_path = os.path.join(BASE_DIR, script_path)
    print(f"\n--- Running {script_path} ---")

    if not os.path.exists(full_script_path):
        print(f"Missing script: {full_script_path}")
        return False

    try:
        subprocess.run([py_exe, full_script_path], cwd=BASE_DIR, check=True)
        print(f"--- Finished {script_path} ---")
        return True
    except subprocess.CalledProcessError as e:
        print(f"!!! Error running {script_path} (exit {e.returncode}) !!!")
        return False


def main():
    print(">>> Starting targeted rating enrichment...")
    py_exe = resolve_python()
    print(f">>> Python interpreter: {py_exe}")

    enrichment_scripts = [
        os.path.join("scraper", "enrich_ratings_mangadex.py"),
        os.path.join("scraper", "enrich_ratings_anilist.py"),
        os.path.join("scraper", "enrich_ratings_mal.py"),
        os.path.join("scraper", "enrich_ratings_kitsu.py"),
    ]

    for script in enrichment_scripts:
        if not run_script(script, py_exe):
            print(f"Stopping pipeline because {script} failed.")
            sys.exit(1)

    print("\n>>> Enrichment scripts completed successfully.")
    print(">>> Starting clean/deduplicate/aggregate pipeline...")

    pipeline_scripts = [
        os.path.join("pipeline", "clean.py"),
        os.path.join("pipeline", "deduplicate.py"),
        os.path.join("pipeline", "aggregate.py"),
    ]

    for script in pipeline_scripts:
        if not run_script(script, py_exe):
            print(f"Stopping pipeline because {script} failed.")
            sys.exit(1)

    print("\n>>> Full enrichment + pipeline completed successfully.")
    print("The manga_rankings table should now reflect the latest scores.")


if __name__ == "__main__":
    main()
