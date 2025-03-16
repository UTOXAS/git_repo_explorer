import os
import git
import shutil
import tempfile
import re
from charset_normalizer import detect


class RepositoryHandler:
    def __init__(self, repo_path):
        self.repo_path, self.branch = self._parse_repo_url(repo_path)
        self.temp_dir = None
        self._clone_or_validate_repo()

    def _parse_repo_url(self, repo_path):
        if repo_path.startswith("https://github.com"):
            match = re.match(
                r"(https://github\.com/[^/]+/[^/]+)(?:/tree/([^/]+))?", repo_path
            )
            if match:
                base_url = match.group(1)
                branch = match.group(2) if match.group(2) else None
                if not base_url.endswith(".git"):
                    base_url += ".git"
                return base_url, branch
        return repo_path, None

    def _clone_or_validate_repo(self):
        if os.path.isdir(self.repo_path):
            if not os.path.exists(os.path.join(self.repo_path, ".git")):
                raise ValueError("Local path is not a Git repository")
            self.repo_dir = self.repo_path
            if self.branch:
                raise ValueError(
                    "Branch specification is not supported for local paths"
                )
        else:
            self.temp_dir = tempfile.mkdtemp(prefix="git_repo_")
            try:
                clone_args = {"url": self.repo_path, "to_path": self.temp_dir}
                if self.branch:
                    clone_args["branch"] = self.branch
                git.Repo.clone_from(**clone_args)
                self.repo_dir = self.temp_dir
            except git.GitCommandError as e:
                shutil.rmtree(self.temp_dir, ignore_errors=True)
                raise e

    def get_repo_structure(self):
        structure = {}
        for root, dirs, files in os.walk(self.repo_dir):
            if ".git" in dirs:
                dirs.remove(".git")  # Exclude .git directory
            relative_root = os.path.relpath(root, self.repo_dir)
            current_level = structure
            if relative_root != ".":
                for part in relative_root.split(os.sep):
                    current_level = current_level.setdefault(part, {})
            for file in files:
                current_level[file] = False
        return structure

    def get_file_content(self, file_path):
        full_path = os.path.join(self.repo_dir, file_path)
        file_size = os.path.getsize(full_path)
        if file_size > 1024 * 1024:  # 1MB limit
            return "Binary file - contents omitted"

        # Read a sample of the file (up to 64KB) for encoding detection
        sample_size = min(file_size, 64 * 1024)
        with open(full_path, "rb") as f:
            sample = f.read(sample_size)

        # Detect encoding with charset-normalizer
        result = detect(sample)
        confidence = result["confidence"] or 0
        encoding = result["encoding"]

        # High confidence (>0.95) and a known text encoding = text file
        if confidence > 0.95 and encoding:
            try:
                with open(full_path, "r", encoding=encoding) as f:
                    return f.read()
            except (UnicodeDecodeError, IOError):
                return "Binary file - contents omitted"
        return "Binary file - contents omitted"

    def __del__(self):
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
