import os

# Base Directory of the project
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Data Directories
DEFAULT_DATA_DIR = os.path.join(BASE_DIR, "data")
if os.environ.get("VERCEL") or os.environ.get("IS_SERVERLESS"):
    DEFAULT_DATA_DIR = "/tmp/data"

DATA_DIR = os.environ.get("DATA_DIR", DEFAULT_DATA_DIR)
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", os.path.join(DATA_DIR, "raw"))
EXPORT_DIR = os.environ.get("EXPORT_DIR", os.path.join(DATA_DIR, "exports"))

# Public backend URL for generating absolute file download links
# e.g., BACKEND_URL=https://api.example.com
BACKEND_URL = os.environ.get("BACKEND_URL")

# Create directories if they do not exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(EXPORT_DIR, exist_ok=True)
