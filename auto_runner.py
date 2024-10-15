import subprocess
import sys
import os

# Get the path to the Python interpreter in the current virtual environment
VENV_PYTHON = os.path.join(os.getcwd(), ".venv", "Scripts", "python.exe")

# Paths to the scripts you want to run
MAIN_SCRIPT_PATH = "main.py"
IP_CHECKER_SCRIPT_PATH = "ip_checker.py"

def run_scripts():
    # Run main.py with the virtual environment's Python interpreter
    subprocess.Popen([VENV_PYTHON, MAIN_SCRIPT_PATH])

    # Run ip_checker.py with the virtual environment's Python interpreter
    subprocess.Popen([VENV_PYTHON, IP_CHECKER_SCRIPT_PATH])

if __name__ == '__main__':
    run_scripts()
