import os
import tkinter as tk
from tkinter import ttk, messagebox
from gui import RepositoryGUI
from repo_handler import RepositoryHandler
from file_writer import FileWriter


class GitRepoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Git Repository Explorer")
        self.root.geometry("800x600")
        self.setup_styles()
        self.gui = RepositoryGUI(self.root, self, self.process_repo)
        self.repo_handler = None
        self.selected_files = set()
        self.structure = {}

    def setup_styles(self):
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

    def process_repo(self, repo_path, branch=None):
        try:
            self.repo_handler = RepositoryHandler(repo_path, branch)
            self.structure = self.repo_handler.get_repo_structure()
            self.gui.display_structure(self.structure)
            self.selected_files = self._get_all_files(self.structure)
            self.gui.update_save_button_state(len(self.selected_files) > 0)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _get_all_files(self, structure, prefix=""):
        files = set()
        for name, content in structure.items():
            full_path = os.path.join(prefix, name) if prefix else name
            if isinstance(content, dict):
                files.update(self._get_all_files(content, full_path))
            else:
                files.add(full_path)
        return files

    def on_file_select(self, event):
        item = self.gui.tree.identify("item", event.x, event.y)
        if not item:
            return
        full_path = self.gui.tree.item(item, "text")
        is_dir = self._is_directory(full_path)
        if full_path in self.selected_files or (
            is_dir and any(f.startswith(full_path) for f in self.selected_files)
        ):
            self._deselect_item(item, full_path, is_dir)
        else:
            self._select_item(item, full_path, is_dir)
        self.gui.update_save_button_state(len(self.selected_files) > 0)

    def _is_directory(self, path):
        current = self.structure
        for part in path.split(os.sep):
            if part not in current:
                return False
            current = current[part]
            if not isinstance(current, dict):
                return False
        return True

    def _select_item(self, item, path, is_dir):
        if is_dir:
            for child in self.gui.tree.get_children(item):
                child_path = self.gui.tree.item(child, "text")
                self._select_item(child, child_path, self._is_directory(child_path))
        else:
            self.selected_files.add(path)
            self.gui.tree.item(item, tags=("selected",))

    def _deselect_item(self, item, path, is_dir):
        if is_dir:
            for child in self.gui.tree.get_children(item):
                child_path = self.gui.tree.item(child, "text")
                self._deselect_item(child, child_path, self._is_directory(child_path))
        else:
            self.selected_files.discard(path)
            self.gui.tree.item(item, tags=())

    def save_to_file(self):
        if not self.selected_files:
            messagebox.showwarning("Warning", "No files selected!")
            return
        writer = FileWriter(self.repo_handler, self.selected_files)
        writer.save_to_file("repo_contents.txt")
        messagebox.showinfo("Success", "Repository contents saved to repo_contents.txt")


if __name__ == "__main__":
    root = tk.Tk()
    app = GitRepoApp(root)
    root.mainloop()
