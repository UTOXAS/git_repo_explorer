import os
import git
import shutil
import tempfile
import re
from charset_normalizer import detect
from gitignore_parser import parse_gitignore


class RepositoryHandler:
    def __init__(self, repo_path, branch=None):
        self.repo_path = self._strip_branch_from_url(repo_path)
        self.branch = branch
        self.temp_dir = None
        self._clone_or_validate_repo()

    def _strip_branch_from_url(self, repo_path):
        if repo_path.startswith("https://github.com"):
            match = re.match(
                r"(https://github\.com/[^/]+/[^/]+)(?:/tree/[^/]+)?", repo_path
            )
            if match:
                base_url = match.group(1)
                if not base_url.endswith(".git"):
                    base_url += ".git"
                return base_url
        return repo_path

    def _clone_or_validate_repo(self):
        if os.path.isdir(self.repo_path):
            if not os.path.exists(os.path.join(self.repo_path, ".git")):
                raise ValueError("Local path is not a Git repository")
            self.repo_dir = self.repo_path
            if self.branch:
                try:
                    repo = git.Repo(self.repo_dir)
                    repo.git.checkout(self.branch)
                except git.GitCommandError as e:
                    raise ValueError(
                        f"Branch '{self.branch}' not found in local repository"
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
        gitignore_path = os.path.join(self.repo_dir, ".gitignore")
        ignore_func = (
            parse_gitignore(gitignore_path)
            if os.path.exists(gitignore_path)
            else lambda x: False
        )

        for root, dirs, files in os.walk(self.repo_dir, topdown=True):
            if ".git" in dirs:
                dirs.remove(".git")  # Exclude .git directory

            # Get relative path safely
            try:
                relative_root = os.path.relpath(root, self.repo_dir)
            except ValueError:
                continue  # Skip if path resolution fails

            # Skip if the root itself is ignored
            if relative_root != "." and ignore_func(relative_root):
                dirs[:] = []  # Clear dirs to prevent further traversal
                continue

            # Filter directories
            dirs[:] = [
                d
                for d in dirs
                if not ignore_func(
                    os.path.join(relative_root, d) if relative_root != "." else d
                )
            ]

            current_level = structure
            if relative_root != ".":
                for part in relative_root.split(os.sep):
                    current_level = current_level.setdefault(part, {})

            # Filter files
            for file in files:
                full_rel_path = (
                    os.path.join(relative_root, file) if relative_root != "." else file
                )
                if not ignore_func(full_rel_path):
                    current_level[file] = False

        return structure

    def get_file_content(self, file_path):
        full_path = os.path.join(self.repo_dir, file_path)
        file_size = os.path.getsize(full_path)
        if file_size > 1024 * 1024:  # 1MB limit
            return "Binary file - contents omitted"

        sample_size = min(file_size, 64 * 1024)
        with open(full_path, "rb") as f:
            sample = f.read(sample_size)

        result = detect(sample)
        confidence = result["confidence"] or 0
        encoding = result["encoding"]

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
