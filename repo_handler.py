import os
import re
import shutil
import tempfile
import git
from charset_normalizer import detect
from gitignore_parser import parse_gitignore

"""Module for handling repository operations in Git Repository Explorer."""


class RepositoryHandler:
    """Manages repository cloning and content access."""

    # Define common text file extensions
    TEXT_EXTENSIONS = {
        ".md",
        ".txt",
        ".py",
        ".bat",
        ".json",
        ".yaml",
        ".yml",
        ".ini",
        ".cfg",
        ".sh",
    }

    def __init__(self, repo_path, branch=None):
        self._repo_path = self._strip_branch_from_url(repo_path)
        self._branch = branch
        self._temp_dir = None
        self._repo_dir = None
        self._initialize_repository()

    def _strip_branch_from_url(self, repo_path):
        """Strip branch information from GitHub URLs."""
        if repo_path.startswith("https://github.com"):
            match = re.match(
                r"(https://github\.com/[^/]+/[^/]+)(?:/tree/[^/]+)?", repo_path
            )
            if match:
                base_url = match.group(1)
                return base_url + ".git" if not base_url.endswith(".git") else base_url
        return repo_path

    def _initialize_repository(self):
        """Initialize the repository based on path type."""
        if os.path.isdir(self._repo_path):
            self._setup_local_repo()
        else:
            self._clone_remote_repo()

    def _setup_local_repo(self):
        """Set up a local repository."""
        self._repo_dir = os.path.realpath(self._repo_path)
        if not os.path.exists(os.path.join(self._repo_dir, ".git")):
            raise ValueError(f"Path '{self._repo_path}' is not a Git repository")
        if self._branch:
            repo = git.Repo(self._repo_dir)
            repo.git.checkout(self._branch)

    def _clone_remote_repo(self):
        """Clone a remote repository to a temporary directory."""
        self._temp_dir = tempfile.mkdtemp(prefix="git_repo_")
        clone_args = {"url": self._repo_path, "to_path": self._temp_dir}
        if self._branch:
            clone_args["branch"] = self._branch
        git.Repo.clone_from(**clone_args)
        self._repo_dir = self._temp_dir

    def get_repo_structure(self):
        """Get the directory structure of the repository."""
        structure = {}
        ignore_func = self._get_ignore_function()
        for root, dirs, files in os.walk(self._repo_dir, topdown=True):
            if ".git" in root.split(os.sep):
                dirs[:] = []
                continue
            relative_root = os.path.relpath(root, self._repo_dir)
            abs_root = os.path.join(self._repo_dir, relative_root)
            dirs[:] = [d for d in dirs if not ignore_func(os.path.join(abs_root, d))]
            files = [f for f in files if not ignore_func(os.path.join(abs_root, f))]
            self._build_structure(structure, relative_root, files)
        return structure

    def _get_ignore_function(self):
        """Create a function to check gitignore rules."""
        gitignore_path = os.path.join(self._repo_dir, ".gitignore")
        if os.path.exists(gitignore_path):
            return parse_gitignore(gitignore_path, base_dir=self._repo_dir)
        return lambda x: False

    def _build_structure(self, structure, relative_root, files):
        """Build the nested structure dictionary."""
        current_level = structure
        if relative_root != ".":
            for part in relative_root.split(os.sep):
                current_level = current_level.setdefault(part, {})
        for file in files:
            current_level[file] = False

    def get_file_content(self, file_path):
        """Get the content of a specific file."""
        full_path = os.path.join(self._repo_dir, file_path)

        # Check file size
        if os.path.getsize(full_path) > 1024 * 1024:  # 1MB limit
            return "Binary file - contents omitted"

        # Check if file has a known text extension
        _, ext = os.path.splitext(file_path)
        if ext.lower() in self.TEXT_EXTENSIONS:
            try:
                return self._read_text_file(full_path, "utf-8")
            except UnicodeDecodeError:
                # Fallback to encoding detection if UTF-8 fails
                pass

        # Proceed with encoding detection for other files
        encoding = self._detect_encoding(full_path)
        return (
            self._read_text_file(full_path, encoding)
            if encoding
            else "Binary file - contents omitted"
        )

    def _detect_encoding(self, full_path):
        """Detect the file encoding."""
        with open(full_path, "rb") as f:
            file_size = os.path.getsize(full_path)
            sample = f.read(min(file_size, 64 * 1024))

        # Handle empty files
        if not len(sample):
            return "utf-8"  # Assume UTF-8 for empty files

        result = detect(sample)
        # Lower confidence threshold to 0.8
        return (
            result["encoding"]
            if result["encoding"]
            and result["confidence"]
            and result["confidence"] > 0.8
            else None
        )

    def _read_text_file(self, full_path, encoding):
        """Read the text file with specified encoding."""
        try:
            with open(full_path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            return "Binary file - contents omitted"

    def __del__(self):
        """Clean up temporary directory on object deletion."""
        if self._temp_dir and os.path.exists(self._temp_dir):
            shutil.rmtree(self._temp_dir, ignore_errors=True)
