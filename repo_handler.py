import os
import git
import shutil
import mimetypes


class RepositoryHandler:
    def __init__(self, repo_path):
        self.repo_path = repo_path
        self.temp_dir = None
        self._clone_or_validate_repo()

    def _clone_or_validate_repo(self):
        if os.path.isdir(self.repo_path):
            if not os.path.exists(os.path.join(self.repo_path, ".git")):
                raise ValueError("Local path is not a Git repository")
            self.repo_dir = self.repo_path
        else:
            self.temp_dir = "temp_repo"
            git.Repo.clone_from(self.repo_path, self.temp_dir)
            self.repo_dir = self.temp_dir

    def get_repo_structure(self):
        structure = {}
        for root, dirs, files in os.walk(self.repo_dir):
            relative_root = os.path.relpath(root, self.repo_dir)
            current_level = structure
            if relative_root != ".":
                for part in relative_root.split(os.sep):
                    current_level = current_level.setdefault(part, {})
            for file in files:
                if file != ".git":
                    current_level[file] = False
        return structure

    def get_file_content(self, file_path):
        full_path = os.path.join(self.repo_dir, file_path)
        if (
            not mimetypes.guess_type(full_path)[0]
            or os.path.getsize(full_path) > 1024 * 1024
        ):
            return "Binary file - contents omitted"
        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    def __del__(self):
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
