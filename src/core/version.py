import subprocess
import os
import shutil
from pathlib import Path

def get_git_info() -> str:
    """
    Get the latest git commit has and date.
    
    Returns:
        str: Formatted git info string (hash date), or "Unknown Version" if failed.
    """
    try:
        # Resolve project root relative to this file
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent
        
        git_dir = project_root / ".git"

        # Check if we are in a git repository
        if not git_dir.exists():
            return f"Unknown Version (No .git found at {project_root})"
            
        # Resolve git executable path
        git_cmd = shutil.which("git")
        
        # Fallback for Windows if git is not in PATH
        if not git_cmd and os.name == 'nt':
            possible_paths = [
                r"C:\Program Files\Git\cmd\git.exe",
                r"C:\Program Files\Git\bin\git.exe",
                r"C:\Program Files (x86)\Git\cmd\git.exe",
                r"C:\Program Files (x86)\Git\bin\git.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Programs\Git\cmd\git.exe"),
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    git_cmd = path
                    break

        if not git_cmd:
             print("Warning: Git executable not found in PATH or common locations. Attempting to read .git files directly.")
             return _get_git_info_from_files(project_root)

        # Run git log command with explicit cwd
        # %h: abbreviated commit hash
        # %cd: committer date (format respects --date= option)
        result = subprocess.run(
            [git_cmd, "log", "-1", "--format=%h %cd"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except Exception as e:
        return f"Unknown Version (Error: {str(e)})"

def _get_git_info_from_files(project_root: Path) -> str:
    """Fallback: Read commit info directly from .git directory."""
    try:
        git_dir = project_root / ".git"
        head_file = git_dir / "HEAD"
        
        if not head_file.exists():
            return "Unknown Version (No .git/HEAD)"
            
        # 1. Get current commit hash
        with open(head_file, "r", encoding="utf-8") as f:
            ref = f.read().strip()
            
        commit_hash = ""
        if ref.startswith("ref:"):
            ref_path = ref.split(" ")[1]
            ref_file = git_dir / ref_path
            if ref_file.exists():
                with open(ref_file, "r", encoding="utf-8") as f:
                    commit_hash = f.read().strip()
            else:
                # Packed refs case or other complex cases not handled simply
                pass
        else:
            commit_hash = ref # Detached HEAD case
            
        if not commit_hash:
            return "Unknown Version (Ref not found)"
            
        short_hash = commit_hash[:7]
        
        # 2. Try to get date from logs/HEAD (simple parsing)
        # Log format: <old_hash> <new_hash> <committer> <timestamp> <tz> <message>
        # We want the last line's timestamp
        date_str = ""
        logs_head = git_dir / "logs" / "HEAD"
        if logs_head.exists():
            try:
                with open(logs_head, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    if lines:
                        last_line = lines[-1]
                        parts = last_line.split("> ") # Split after email
                        if len(parts) > 1:
                            time_part = parts[1].split(" ")
                            if len(time_part) >= 2:
                                timestamp = int(time_part[0])
                                import datetime
                                dt = datetime.datetime.fromtimestamp(timestamp)
                                date_str = dt.strftime("%a %b %d %H:%M:%S %Y")
            except Exception:
                pass # Ignore log parsing errors
        
        return f"{short_hash} {date_str}".strip()

    except Exception as e:
        return f"Unknown Version (File Parse Error: {str(e)})"
