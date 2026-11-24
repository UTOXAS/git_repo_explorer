import os
import re
import shutil
import tempfile
import git
from charset_normalizer import detect
from gitignore_parser import parse_gitignore

"""Module for handling repository operations in Git Repository Explorer."""


class RepositoryHandler:
    """Manages repository cloning, commit checkout, and content access."""

    # MODIFIED: Expanded common text file extensions
    TEXT_EXTENSIONS = {
        ".md",
        ".txt",
        ".py",
        ".bat",
        ".ps1",
        ".json",
        ".yaml",
        ".yml",
        ".ini",
        ".cfg",
        ".sh",
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".html",
        ".css",
        ".scss",
        ".xml",
        ".sql",
        ".csv",
        ".java",
        ".c",
        ".cpp",
        ".h",
        ".cs",
        ".go",
        ".rs",
        ".php",
        ".rb",
        ".toml",
        ".env",
    }

    def __init__(self, repo_path, branch=None):
        self._repo_path = self._strip_branch_from_url(repo_path)
        self._branch = branch
        self._temp_dir = None
        self._repo_dir = None
        # ADDED: Store GitPython Repo instance and active commit hash
        self._repo = None
        self.current_commit = None
        self._initialize_repository()

    def _strip_branch_from_url(self, repo_path):
        """Strip branch information from GitHub URLs."""
        if repo_path.startswith("https://github.com"):
            match = re.match(
                r"(https://github\.com/[^/]+/[^/]+)(?:/tree/([^/]+))?", repo_path
            )
            if match:
                base_url = match.group(1)
                # ADDED: Auto-extract branch from URL if not explicitly provided
                if match.group(2) and not self._branch:
                    self._branch = match.group(2)
                return base_url + ".git" if not base_url.endswith(".git") else base_url
        return repo_path

    def _initialize_repository(self):
        """Initialize the repository based on path type."""
        if os.path.isdir(self._repo_path):
            self._setup_local_repo()
        else:
            self._clone_remote_repo()
        # ADDED: Track initial HEAD commit
        self.current_commit = self._repo.head.commit.hexsha

    def _setup_local_repo(self):
        """Set up a local repository safely in a temporary copy."""
        source_dir = os.path.realpath(self._repo_path)
        if not os.path.exists(os.path.join(source_dir, ".git")):
            raise ValueError(f"Path '{self._repo_path}' is not a Git repository")
        # MODIFIED: Clone local repo to temp_dir so checking out past commits never alters user's local working tree
        self._temp_dir = tempfile.mkdtemp(prefix="git_repo_local_")
        clone_args = {"url": source_dir, "to_path": self._temp_dir}
        if self._branch:
            clone_args["branch"] = self._branch
        self._repo = git.Repo.clone_from(**clone_args)
        self._repo_dir = self._temp_dir

    def _clone_remote_repo(self):
        """Clone a remote repository to a temporary directory."""
        self._temp_dir = tempfile.mkdtemp(prefix="git_repo_")
        clone_args = {"url": self._repo_path, "to_path": self._temp_dir}
        if self._branch:
            clone_args["branch"] = self._branch
        # MODIFIED: Store cloned repo reference
        self._repo = git.Repo.clone_from(**clone_args)
        self._repo_dir = self._temp_dir

    # ADDED: Retrieve commit history for the commit selector dropdown
    def get_commits(self, max_count=100):
        """Return a list of recent commits with hash, short hash, date, author, and summary."""
        if not self._repo:
            return []
        commits = []
        target_rev = self._branch if self._branch else "HEAD"
        try:
            commit_iter = self._repo.iter_commits(target_rev, max_count=max_count)
        except git.GitCommandError:
            commit_iter = self._repo.iter_commits(max_count=max_count)

        for c in commit_iter:
            date_str = c.committed_datetime.strftime("%Y-%m-%d %H:%M")
            summary = c.summary[:60] + ("..." if len(c.summary) > 60 else "")
            commits.append(
                {
                    "hexsha": c.hexsha,
                    "short_sha": c.hexsha[:7],
                    "summary": summary,
                    "author": c.author.name,
                    "date": date_str,
                    "label": f"[{c.hexsha[:7]}] {date_str} - {summary} ({c.author.name})",
                }
            )
        return commits

    # ADDED: Checkout a specific commit hash
    def checkout_commit(self, commit_sha):
        """Checkout the repository to a specific commit."""
        if not self._repo:
            raise RuntimeError("Repository is not initialized.")
        self._repo.git.checkout(commit_sha, force=True)
        self.current_commit = commit_sha

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
        # MODIFIED: Sort directories and files alphabetically
        for file in sorted(files):
            current_level[file] = False

    def get_file_content(self, file_path):
        """Get the content of a specific file."""
        full_path = os.path.join(self._repo_dir, file_path)

        if not os.path.exists(full_path):
            return "File not found in selected commit."

        if os.path.getsize(full_path) > 1024 * 1024:  # 1MB limit
            return "Binary file - contents omitted"

        _, ext = os.path.splitext(file_path)
        if ext.lower() in self.TEXT_EXTENSIONS:
            try:
                return self._read_text_file(full_path, "utf-8")
            except UnicodeDecodeError:
                pass

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

        if not len(sample):
            return "utf-8"

        result = detect(sample)
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

    # ADDED: Explicit cleanup method
    def cleanup(self):
        """Clean up temporary directory explicitly."""
        if self._temp_dir and os.path.exists(self._temp_dir):
            shutil.rmtree(self._temp_dir, ignore_errors=True)
            self._temp_dir = None

    def __del__(self):
        """Clean up temporary directory on object deletion."""
        self.cleanup()