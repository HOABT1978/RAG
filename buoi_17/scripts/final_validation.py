import os
import sys

# Standard wrapper for executing final validation checks
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)

import final_audit

if __name__ == "__main__":
    # Runs the final audit script to evaluate the project and generate outputs/final_validation_report.md
    print("Executing final validation checklist...")
