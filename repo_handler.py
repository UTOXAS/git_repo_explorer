import os
import git
import shutil
import tempfile
import re
from charset_normalizer import detect
from gitignore_parser import parse_gitignore


class RepositoryHandler:
    def __init__(self, repo_path, branch=None):
        self._repo_path = self._strip_branch_from_url(repo_path)
        self._branch = branch
        self._temp_dir = None
        self._repo_dir = None
        print(f"Initializing with repo_path: {self._repo_path}, branch: {self._branch}")
        self._initialize_repository()

    def _strip_branch_from_url(self, repo_path):
        """Extracts the base repository URL from a GitHub link."""
        if repo_path.startswith("https://github.com"):
            match = re.match(
                r"(https://github\.com/[^/]+/[^/]+)(?:/tree/[^/]+)?", repo_path
            )
            if match:
                base_url = match.group(1)
                return base_url + ".git" if not base_url.endswith(".git") else base_url
        return repo_path

    def _initialize_repository(self):
        """Sets up the repository by cloning or validating the path."""
        if os.path.isdir(self._repo_path):
            self._setup_local_repo()
        else:
            self._clone_remote_repo()
        print(f"Repository directory set to: {self._repo_dir}")

    def _setup_local_repo(self):
        """Validates and configures a local repository."""
        self._repo_dir = os.path.realpath(os.path.abspath(self._repo_path))
        if not os.path.exists(os.path.join(self._repo_dir, ".git")):
            raise ValueError(f"Path '{self._repo_path}' is not a Git repository")
        if self._branch:
            self._checkout_branch()

    def _checkout_branch(self):
        """Switches to the specified branch in the local repository."""
        try:
            repo = git.Repo(self._repo_dir)
            repo.git.checkout(self._branch)
        except git.GitCommandError:
            raise ValueError(f"Branch '{self._branch}' not found")

    def _clone_remote_repo(self):
        """Clones a remote repository to a temporary directory."""
        self._temp_dir = tempfile.mkdtemp(prefix="git_repo_")
        try:
            clone_args = {"url": self._repo_path, "to_path": self._temp_dir}
            if self._branch:
                clone_args["branch"] = self._branch
            git.Repo.clone_from(**clone_args)
            self._repo_dir = os.path.realpath(self._temp_dir)
        except git.GitCommandError as e:
            shutil.rmtree(self._temp_dir, ignore_errors=True)
            raise e

    def get_repo_structure(self):
        """Builds a dictionary representing the repository's file structure."""
        if not self._repo_dir:
            raise ValueError("Repository directory not initialized")

        structure = {}
        ignore_func = self._get_ignore_function()
        repo_dir_normalized = os.path.normcase(os.path.normpath(self._repo_dir))

        for root, dirs, files in os.walk(
            self._repo_dir, topdown=True, followlinks=False
        ):
            root_normalized = os.path.normcase(os.path.normpath(os.path.realpath(root)))
            print(f"Traversing: {root_normalized}")
            if not root_normalized.startswith(repo_dir_normalized):
                print(f"Skipping out-of-bounds path: {root_normalized}")
                continue
            if ".git" in root_normalized.split(os.sep):
                dirs[:] = []
                print(f"Skipping .git directory: {root_normalized}")
                continue

            relative_root = self._compute_relative_root(root_normalized)
            if relative_root is None:
                print(f"Failed to compute relative path for: {root_normalized}")
                continue

            # Apply .gitignore filtering to directories
            dirs_before = dirs.copy()
            self._filter_dirs(dirs, relative_root, ignore_func)
            print(
                f"Filtered dirs from {dirs_before} to {dirs} for relative_root: {relative_root}"
            )
            self._build_structure(structure, relative_root, files, ignore_func)

        return structure

    def _get_ignore_function(self):
        """Creates a function to filter files based on .gitignore."""
        gitignore_path = os.path.join(self._repo_dir, ".gitignore")
        if os.path.exists(gitignore_path):
            print(f"Using .gitignore at: {gitignore_path}")
            return parse_gitignore(gitignore_path)
        print("No .gitignore found, using default ignore function")
        return lambda x: False

    def _compute_relative_root(self, root):
        """Computes the relative path of root from repo_dir safely."""
        try:
            rel_path = os.path.relpath(root, self._repo_dir)
            print(f"Computed relative path: {rel_path} for root: {root}")
            return rel_path
        except ValueError as e:
            print(f"ValueError in _compute_relative_root: {e}")
            return None

    def _filter_dirs(self, dirs, relative_root, ignore_func):
        """Filters directories based on .gitignore rules."""
        if relative_root is None:
            print("Skipping filter due to invalid relative_root")
            dirs[:] = []
            return
        dirs[:] = [
            d
            for d in dirs
            if not ignore_func(
                os.path.join(relative_root, d) if relative_root != "." else d
            )
        ]

    def _build_structure(self, structure, relative_root, files, ignore_func):
        """Populates the structure dictionary with files and directories."""
        current_level = structure
        if relative_root != ".":
            for part in relative_root.split(os.sep):
                current_level = current_level.setdefault(part, {})

        for file in files:
            full_rel_path = (
                os.path.join(relative_root, file) if relative_root != "." else file
            )
            if not ignore_func(full_rel_path):
                current_level[file] = False

    def get_file_content(self, file_path):
        """Reads and returns the content of a file."""
        full_path = os.path.join(self._repo_dir, file_path)
        file_size = os.path.getsize(full_path)
        if file_size > 1024 * 1024:  # 1MB limit
            return "Binary file - contents omitted"

        encoding = self._detect_encoding(full_path)
        if encoding:
            return self._read_text_file(full_path, encoding)
        return "Binary file - contents omitted"

    def _detect_encoding(self, full_path):
        """Detects the file encoding with a sample."""
        with open(full_path, "rb") as f:
            sample = f.read(min(os.path.getsize(full_path), 64 * 1024))
        result = detect(sample)
        return result["encoding"] if result["confidence"] > 0.95 else None

    def _read_text_file(self, full_path, encoding):
        """Reads a text file with the specified encoding."""
        try:
            with open(full_path, "r", encoding=encoding) as f:
                return f.read()
        except (UnicodeDecodeError, IOError):
            return "Binary file - contents omitted"

    def __del__(self):
        """Cleans up temporary directory on object destruction."""
        if self._temp_dir and os.path.exists(self._temp_dir):
            shutil.rmtree(self._temp_dir, ignore_errors=True)
