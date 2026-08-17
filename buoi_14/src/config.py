import os
from pathlib import Path
from dotenv import load_dotenv

# Base Directory of buoi_14
BASE_DIR = Path(__file__).resolve().parent.parent

# Load local environment configuration
dotenv_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=dotenv_path)

# RBAC Valid Roles definition
VALID_ROLES = ["Admin", "HR_Manager", "Risk_Officer", "Employee", "Guest"]

# Retrieve database connection settings
NEO4J_URI = os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "BUOI_14")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "12345678")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
