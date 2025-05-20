#!/usr/bin/env python3

import os
import pathlib

# Get the directory where the script is located
root = pathlib.Path(__file__).parent.resolve()
db_path = root / "til.db"

# Remove old database if it exists
if db_path.exists():
    print("Removing old database...")
    os.remove(db_path)
    print("Old database removed.")

# Import and rebuild
from app import build_database
print("Building new database...")
build_database(root)
print("Database rebuild complete, I hope!")