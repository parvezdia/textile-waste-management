import subprocess
import sys
import os

def run_management_command():
    manage_py = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'manage.py'))
    result = subprocess.run(
        [sys.executable, manage_py, 'generate_dummy_data'],
        cwd=os.path.dirname(manage_py)
    )
    if result.returncode != 0:
        print("Failed to generate dummy data.")
        sys.exit(1)

def run_locust():
    result = subprocess.run(
        ['locust', '-f', 'locustfile.py'],
        cwd=os.path.dirname(__file__)
    )
    if result.returncode != 0:
        print("Locust exited with an error.")
        sys.exit(1)

if __name__ == "__main__":
    print("Generating dummy data...")
    run_management_command()
    print("Starting Locust...")
    run_locust()
