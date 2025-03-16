import os
import git
import shutil
import tempfile
import re
import logging
import traceback
from charset_normalizer import detect
from gitignore_parser import parse_gitignore

# Configure logging with maximum detail
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    filename="repo_handler.log",
    filemode="w",
)
logger = logging.getLogger(__name__)


class RepositoryHandler:
    def __init__(self, repo_path, branch=None):
        logger.debug(f"__init__ called with repo_path='{repo_path}', branch='{branch}'")
        self._repo_path = self._strip_branch_from_url(repo_path)
        self._branch = branch
        self._temp_dir = None
        self._repo_dir = None
        logger.info(
            f"Initialized attributes: repo_path='{self._repo_path}', branch='{self._branch}'"
        )
        self._initialize_repository()

    def _strip_branch_from_url(self, repo_path):
        logger.debug(f"_strip_branch_from_url called with repo_path='{repo_path}'")
        logger.debug(
            f"Checking if repo_path starts with 'https://github.com': {repo_path.startswith('https://github.com')}"
        )
        if repo_path.startswith("https://github.com"):
            logger.debug(f"Attempting regex match on '{repo_path}'")
            match = re.match(
                r"(https://github\.com/[^/]+/[^/]+)(?:/tree/[^/]+)?", repo_path
            )
            if match:
                base_url = match.group(1)
                result = (
                    base_url + ".git" if not base_url.endswith(".git") else base_url
                )
                logger.debug(f"Regex matched, returning stripped URL: '{result}'")
                return result
            logger.debug("Regex did not match, returning original repo_path")
        logger.debug(f"Returning original repo_path: '{repo_path}'")
        return repo_path

    def _initialize_repository(self):
        logger.debug("_initialize_repository called")
        logger.debug(
            f"Checking if '{self._repo_path}' is a directory: {os.path.isdir(self._repo_path)}"
        )
        if os.path.isdir(self._repo_path):
            logger.debug("Path is a directory, setting up local repo")
            self._setup_local_repo()
        else:
            logger.debug("Path is not a directory, cloning remote repo")
            self._clone_remote_repo()
        logger.info(f"Repository directory finalized: '{self._repo_dir}'")

    def _setup_local_repo(self):
        logger.debug(f"_setup_local_repo called with repo_path='{self._repo_path}'")
        self._repo_dir = os.path.realpath(os.path.abspath(self._repo_path))
        logger.debug(f"Resolved repo_dir to: '{self._repo_dir}'")
        git_path = os.path.join(self._repo_dir, ".git")
        logger.debug(
            f"Checking for .git directory at: '{git_path}' - Exists: {os.path.exists(git_path)}"
        )
        if not os.path.exists(git_path):
            logger.error(f"Path '{self._repo_path}' is not a Git repository")
            raise ValueError(f"Path '{self._repo_path}' is not a Git repository")
        if self._branch:
            logger.debug(f"Branch specified: '{self._branch}', proceeding to checkout")
            self._checkout_branch()

    def _checkout_branch(self):
        logger.debug(f"_checkout_branch called with branch='{self._branch}'")
        try:
            repo = git.Repo(self._repo_dir)
            logger.debug(f"Git repo object created for: '{self._repo_dir}'")
            repo.git.checkout(self._branch)
            logger.info(f"Successfully checked out branch: '{self._branch}'")
        except git.GitCommandError as e:
            logger.error(f"Failed to checkout branch '{self._branch}': {str(e)}")
            logger.debug(f"Exception traceback: {traceback.format_exc()}")
            raise ValueError(f"Branch '{self._branch}' not found")

    def _clone_remote_repo(self):
        logger.debug(f"_clone_remote_repo called with repo_path='{self._repo_path}'")
        self._temp_dir = tempfile.mkdtemp(prefix="git_repo_")
        logger.debug(f"Created temp directory: '{self._temp_dir}'")
        try:
            clone_args = {"url": self._repo_path, "to_path": self._temp_dir}
            if self._branch:
                clone_args["branch"] = self._branch
            logger.debug(f"Clone arguments: {clone_args}")
            git.Repo.clone_from(**clone_args)
            self._repo_dir = os.path.realpath(self._temp_dir)
            logger.info(f"Cloned repo to: '{self._repo_dir}'")
        except git.GitCommandError as e:
            logger.error(f"Failed to clone repo: {str(e)}")
            logger.debug(f"Exception traceback: {traceback.format_exc()}")
            shutil.rmtree(self._temp_dir, ignore_errors=True)
            raise e

    def get_repo_structure(self):
        logger.debug("get_repo_structure called")
        if not self._repo_dir:
            logger.error("Repository directory not initialized")
            raise ValueError("Repository directory not initialized")

        structure = {}
        ignore_func = self._get_ignore_function()
        repo_dir_normalized = os.path.normcase(os.path.normpath(self._repo_dir))
        logger.debug(f"Normalized repo_dir: '{repo_dir_normalized}'")

        for root, dirs, files in os.walk(
            self._repo_dir, topdown=True, followlinks=False
        ):
            root_normalized = os.path.normcase(os.path.normpath(os.path.realpath(root)))
            logger.debug(
                f"Traversing root: '{root_normalized}', dirs: {dirs}, files: {files}"
            )

            try:
                common_path = os.path.commonpath([repo_dir_normalized, root_normalized])
                logger.debug(
                    f"Common path between '{repo_dir_normalized}' and '{root_normalized}': '{common_path}'"
                )
                if common_path != repo_dir_normalized:
                    logger.warning(f"Skipping out-of-bounds path: '{root_normalized}'")
                    continue
            except ValueError as e:
                logger.error(f"Path comparison failed: {str(e)}")
                logger.debug(f"Exception traceback: {traceback.format_exc()}")
                continue

            if ".git" in root_normalized.split(os.sep):
                logger.debug(f"Skipping .git directory: '{root_normalized}'")
                dirs[:] = []
                continue

            relative_root = self._compute_relative_root(root_normalized)
            logger.debug(f"Computed relative_root: '{relative_root}'")
            if relative_root is None:
                logger.warning(
                    f"Skipping due to invalid relative_root for: '{root_normalized}'"
                )
                continue

            dirs_before = dirs.copy()
            logger.debug(f"Dirs before filtering: {dirs_before}")
            self._filter_dirs(dirs, relative_root, ignore_func)
            logger.debug(f"Dirs after filtering: {dirs}")

            if relative_root == ".":
                logger.debug("Applying root-level filtering")
                dirs[:] = [
                    d for d in dirs if not ignore_func(os.path.join(self._repo_dir, d))
                ]
                logger.debug(f"Root-level dirs after additional filter: {dirs}")

            self._build_structure(structure, relative_root, files, ignore_func)

        logger.info("Repository structure built successfully")
        logger.debug(f"Final structure: {structure}")
        return structure

    def _get_ignore_function(self):
        logger.debug("_get_ignore_function called")
        gitignore_path = os.path.join(self._repo_dir, ".gitignore")
        logger.debug(
            f"Checking .gitignore at: '{gitignore_path}' - Exists: {os.path.exists(gitignore_path)}"
        )
        if os.path.exists(gitignore_path):
            logger.info(f"Using .gitignore at: '{gitignore_path}'")
            ignore_func = parse_gitignore(gitignore_path, base_dir=self._repo_dir)
            logger.debug("Ignore function created with base_dir")
            return ignore_func
        logger.debug("No .gitignore found, returning default ignore function")
        return lambda x: False

    def _compute_relative_root(self, root):
        logger.debug(f"_compute_relative_root called with root='{root}'")
        try:
            rel_path = os.path.relpath(root, self._repo_dir)
            logger.debug(f"Computed rel_path: '{rel_path}'")
            if rel_path.startswith("..") or os.path.isabs(rel_path):
                logger.warning(f"Path outside repo: '{root}', rel_path='{rel_path}'")
                return None
            logger.debug(f"Valid relative path: '{rel_path}'")
            return rel_path
        except ValueError as e:
            logger.error(f"Error computing relative path: {str(e)}")
            logger.debug(f"Exception traceback: {traceback.format_exc()}")
            return None

    def _filter_dirs(self, dirs, relative_root, ignore_func):
        logger.debug(
            f"_filter_dirs called with dirs={dirs}, relative_root='{relative_root}'"
        )
        if relative_root is None:
            logger.warning("relative_root is None, clearing dirs")
            dirs[:] = []
            return

        dirs_before = dirs.copy()
        logger.debug(f"Dirs before filtering: {dirs_before}")
        filtered_dirs = []
        for d in dirs:
            # Use absolute path relative to repo_dir to avoid working directory confusion
            abs_path = (
                os.path.join(self._repo_dir, relative_root, d)
                if relative_root != "."
                else os.path.join(self._repo_dir, d)
            )
            logger.debug(f"Constructed absolute path to check: '{abs_path}'")
            try:
                is_ignored = ignore_func(abs_path)
                logger.debug(f"ignore_func('{abs_path}') returned: {is_ignored}")
                if not is_ignored:
                    filtered_dirs.append(d)
                else:
                    logger.debug(f"Directory '{d}' ignored by .gitignore")
            except Exception as e:
                logger.error(f"Exception in ignore_func for '{abs_path}': {str(e)}")
                logger.debug(f"Exception traceback: {traceback.format_exc()}")
                raise
        dirs[:] = filtered_dirs
        logger.debug(f"Dirs after filtering: {dirs}")

    def _build_structure(self, structure, relative_root, files, ignore_func):
        logger.debug(
            f"_build_structure called with relative_root='{relative_root}', files={files}"
        )
        current_level = structure
        if relative_root != ".":
            logger.debug(f"Navigating structure for relative_root: '{relative_root}'")
            for part in relative_root.split(os.sep):
                current_level = current_level.setdefault(part, {})
                logger.debug(f"Current level after '{part}': {current_level}")

        for file in files:
            # Use absolute path for ignore_func
            full_abs_path = (
                os.path.join(self._repo_dir, relative_root, file)
                if relative_root != "."
                else os.path.join(self._repo_dir, file)
            )
            logger.debug(f"Processing file with absolute path: '{full_abs_path}'")
            is_ignored = ignore_func(full_abs_path)
            logger.debug(f"ignore_func('{full_abs_path}') returned: {is_ignored}")
            if not is_ignored:
                full_rel_path = (
                    os.path.join(relative_root, file) if relative_root != "." else file
                )
                current_level[file] = False
                logger.debug(
                    f"Added file '{file}' to structure at '{relative_root}' as '{full_rel_path}'"
                )
            else:
                logger.debug(f"File '{file}' ignored by .gitignore")

    def get_file_content(self, file_path):
        logger.debug(f"get_file_content called with file_path='{file_path}'")
        full_path = os.path.join(self._repo_dir, file_path)
        logger.debug(f"Full path resolved: '{full_path}'")
        file_size = os.path.getsize(full_path)
        logger.debug(f"File size: {file_size} bytes")
        if file_size > 1024 * 1024:  # 1MB limit
            logger.debug(f"File too large: '{file_path}'")
            return "Binary file - contents omitted"

        encoding = self._detect_encoding(full_path)
        logger.debug(f"Detected encoding: '{encoding}'")
        if encoding:
            content = self._read_text_file(full_path, encoding)
            logger.debug(f"Content read: {content[:100]}... (first 100 chars)")
            return content
        logger.debug(f"File treated as binary: '{file_path}'")
        return "Binary file - contents omitted"

    def _detect_encoding(self, full_path):
        logger.debug(f"_detect_encoding called with full_path='{full_path}'")
        with open(full_path, "rb") as f:
            file_size = os.path.getsize(full_path)
            sample_size = min(file_size, 64 * 1024)
            logger.debug(f"Reading sample of {sample_size} bytes from '{full_path}'")
            sample = f.read(sample_size)
            logger.debug(f"Sample read: {sample[:50]}... (first 50 bytes)")
        result = detect(sample)
        logger.debug(f"Encoding detection result: {result}")
        encoding = result["encoding"] if result["confidence"] > 0.95 else None
        logger.debug(f"Returning encoding: '{encoding}'")
        return encoding

    def _read_text_file(self, full_path, encoding):
        logger.debug(
            f"_read_text_file called with full_path='{full_path}', encoding='{encoding}'"
        )
        try:
            with open(full_path, "r", encoding=encoding) as f:
                content = f.read()
                logger.debug(
                    f"Successfully read file, content length: {len(content)} chars"
                )
                return content
        except (UnicodeDecodeError, IOError) as e:
            logger.warning(f"Failed to read file '{full_path}': {str(e)}")
            logger.debug(f"Exception traceback: {traceback.format_exc()}")
            return "Binary file - contents omitted"

    def __del__(self):
        logger.debug("__del__ called")
        if self._temp_dir and os.path.exists(self._temp_dir):
            logger.info(f"Cleaning up temp dir: '{self._temp_dir}'")
            shutil.rmtree(self._temp_dir, ignore_errors=True)
            logger.debug(f"Temp dir cleanup attempted")
