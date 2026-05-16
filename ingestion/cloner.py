import os
import shutil
import tempfile
# pyrefly: ignore [missing-import]
from git import Repo

MAX_LINES = 50000
IGNORE_DIRS = {".git", "venv", "node_modules", ".venv", "__pycache__"}

class RepoTooLargeError(Exception):
    pass

def clone_and_validate(repo_url: str):
    """Clones a repo to a temporary directory, validates line count, and returns the path."""
    temp_dir = tempfile.mkdtemp()
    print(f"Cloning {repo_url} into {temp_dir}...")
    Repo.clone_from(repo_url, temp_dir)
    
    total_lines = 0
    py_files = []
    
    for root, dirs, files in os.walk(temp_dir):
        # Modify dirs in-place to skip ignored directories
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                py_files.append(file_path)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        total_lines += len(lines)
                except Exception as e:
                    print(f"Skipping file due to read error: {file_path}")
                    
    if total_lines > MAX_LINES:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise RepoTooLargeError(f"Repo too large for V1: {total_lines} lines (Limit is {MAX_LINES})")
        
    print(f"Validation successful. {len(py_files)} Python files, {total_lines} total lines.")
    return temp_dir, py_files

def cleanup_repo(repo_path: str):
    """Deletes the cloned repository."""
    shutil.rmtree(repo_path, ignore_errors=True)
