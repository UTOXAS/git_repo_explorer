import os
import tkinter as tk
from tkinter import ttk, messagebox
import logging
import traceback
from gui import RepositoryGUI
from repo_handler import RepositoryHandler
from file_writer import FileWriter

# Append to the same log file
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    filename="repo_handler.log",
    filemode="a",
)
logger = logging.getLogger(__name__)


class GitRepoApp:
    def __init__(self, root):
        logger.debug(f"__init__ called with root={root}")
        self.root = root
        self.root.title("Git Repository Explorer")
        self.root.geometry("800x600")
        self.setup_styles()
        self.gui = RepositoryGUI(self.root, self, self.process_repo)
        self.repo_handler = None
        self.selected_files = set()
        self.structure = {}
        logger.info("GitRepoApp initialized")

    def setup_styles(self):
        logger.debug("setup_styles called")
        style = ttk.Style()
        style.configure("TFrame", background="#F5F5F5")
        style.configure("TLabel", font=("Arial", 12, "bold"), background="#F5F5F5")
        style.configure(
            "TButton",
            font=("Arial", 10, "bold"),
            background="#FF5733",
            foreground="white",
        )
        style.map("TButton", background=[("active", "#E74C3C")])
        style.configure("Treeview", font=("Arial", 10), rowheight=25)
        style.configure("Treeview.Heading", font=("Arial", 10, "bold"))
        logger.debug("Styles configured")

    def process_repo(self, repo_path, branch=None):
        logger.debug(
            f"process_repo called with repo_path='{repo_path}', branch='{branch}'"
        )
        try:
            self.repo_handler = RepositoryHandler(repo_path, branch)
            self.structure = self.repo_handler.get_repo_structure()
            logger.debug(f"Repository structure: {self.structure}")
            self.gui.display_structure(self.structure)
            self.selected_files = self._get_all_files(self.structure)
            logger.info(f"Initial selected_files: {self.selected_files}")
            self.gui.update_save_button_state(len(self.selected_files) > 0)
        except Exception as e:
            logger.error(f"Error processing repo: {str(e)}")
            logger.debug(f"Exception traceback: {traceback.format_exc()}")
            messagebox.showerror("Error", str(e))

    def _get_all_files(self, structure, prefix=""):
        logger.debug(
            f"_get_all_files called with structure={structure}, prefix='{prefix}'"
        )
        files = set()
        for name, content in structure.items():
            full_path = os.path.join(prefix, name) if prefix else name
            logger.debug(
                f"Processing item: name='{name}', full_path='{full_path}', content={content}"
            )
            if isinstance(content, dict):
                sub_files = self._get_all_files(content, full_path)
                files.update(sub_files)
                logger.debug(f"Added sub-files from '{full_path}': {sub_files}")
            else:
                files.add(full_path)
                logger.debug(f"Added file: '{full_path}'")
        logger.debug(f"Returning files: {files}")
        return files

    def on_file_select(self, event):
        logger.debug(f"on_file_select called with event={event}")
        item = self.gui.tree.identify("item", event.x, event.y)
        if not item:
            logger.debug("No item selected")
            return
        full_path = self.gui.tree.item(item, "text")
        logger.debug(f"Selected item: '{full_path}'")
        is_dir = self._is_directory(full_path)
        logger.debug(f"Is directory: {is_dir}")
        if full_path in self.selected_files or (
            is_dir and any(f.startswith(full_path) for f in self.selected_files)
        ):
            self._deselect_item(item, full_path, is_dir)
            logger.info(f"Deselected: '{full_path}'")
        else:
            self._select_item(item, full_path, is_dir)
            logger.info(f"Selected: '{full_path}'")
        self.gui.update_save_button_state(len(self.selected_files) > 0)
        logger.debug(f"Updated selected_files: {self.selected_files}")

    def _is_directory(self, path):
        logger.debug(f"_is_directory called with path='{path}'")
        current = self.structure
        for part in path.split(os.sep):
            logger.debug(f"Checking part: '{part}' in current={current}")
            if part not in current:
                logger.debug(f"Part '{part}' not found, returning False")
                return False
            current = current[part]
            if not isinstance(current, dict):
                logger.debug(f"Reached file at '{part}', returning False")
                return False
        logger.debug(f"Path '{path}' is a directory")
        return True

    def _select_item(self, item, path, is_dir):
        logger.debug(
            f"_select_item called with item={item}, path='{path}', is_dir={is_dir}"
        )
        if is_dir:
            for child in self.gui.tree.get_children(item):
                child_path = self.gui.tree.item(child, "text")
                logger.debug(f"Processing child: '{child_path}'")
                self._select_item(child, child_path, self._is_directory(child_path))
        else:
            self.selected_files.add(path)
            self.gui.tree.item(item, tags=("selected",))
            logger.debug(f"Added '{path}' to selected_files")

    def _deselect_item(self, item, path, is_dir):
        logger.debug(
            f"_deselect_item called with item={item}, path='{path}', is_dir={is_dir}"
        )
        if is_dir:
            for child in self.gui.tree.get_children(item):
                child_path = self.gui.tree.item(child, "text")
                logger.debug(f"Processing child: '{child_path}'")
                self._deselect_item(child, child_path, self._is_directory(child_path))
        else:
            self.selected_files.discard(path)
            self.gui.tree.item(item, tags=())
            logger.debug(f"Removed '{path}' from selected_files")

    def save_to_file(self):
        logger.debug("save_to_file called")
        if not self.selected_files:
            logger.warning("No files selected")
            messagebox.showwarning("Warning", "No files selected!")
            return
        logger.info(
            f"Saving {len(self.selected_files)} selected files: {self.selected_files}"
        )
        writer = FileWriter(self.repo_handler, self.selected_files)
        writer.save_to_file("repo_contents.txt")
        logger.info("Save operation completed")
        messagebox.showinfo("Success", "Repository contents saved to repo_contents.txt")


if __name__ == "__main__":
    logger.debug("Main block executed")
    root = tk.Tk()
    app = GitRepoApp(root)
    root.mainloop()
    logger.debug("Main loop exited")
