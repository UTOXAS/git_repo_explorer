import os
import tkinter as tk
from tkinter import ttk, messagebox
from gui import RepositoryGUI
from repo_handler import RepositoryHandler
from file_writer import FileWriter

"""Module for running the main application of Git Repository Explorer."""


class GitRepoApp:
    """Main application class managing the repository explorer functionality."""

    def __init__(self, window):
        self.root = window
        self.root.title("Git Repository Explorer")
        self.root.geometry("800x600")
        self.setup_styles()
        self.gui = RepositoryGUI(self.root, self, self.process_repo)
        self.repo_handler = None
        self.selected_files = set()
        self.structure = {}

    def setup_styles(self):
        """Configure the visual styles for the application."""
        style = ttk.Style()
        style.configure("Main.TFrame", background="#F9FAFB")

        style.configure(
            "Heading.TLabel",
            font=("Arial", 14, "bold"),
            background="#F9FAFB",
            foreground="#1F2937",
        )
        style.configure(
            "Subheading.TLabel",
            font=("Arial", 11),
            background="#F9FAFB",
            foreground="#6B7280",
        )

        style.configure(
            "Primary.TButton",
            font=("Arial", 10, "bold"),
            background="#10B981",
            foreground="#FFFFFF",
            borderwidth=0,
            relief="flat",
            padding=10,
        )
        style.map(
            "Primary.TButton",
            background=[("active", "#059669")],
            shiftrelief=[("pressed", -1)],
        )

        style.configure(
            "Custom.Treeview",
            font=("Arial", 10),
            rowheight=28,
            background="#FFFFFF",
            foreground="#374151",
            fieldbackground="#FFFFFF",
            borderwidth=1,
            relief="solid",
            bordercolor="#E5E7EB",
        )
        style.configure(
            "Custom.Treeview.Heading", font=("Arial", 10, "bold"), background="#F9FAFB"
        )

    def process_repo(self, repo_path, branch=None):
        """Process the repository and update the GUI."""
        self.repo_handler = RepositoryHandler(repo_path, branch)
        self.structure = self.repo_handler.get_repo_structure()
        self.gui.display_structure(self.structure)
        self.selected_files = self._get_all_files(self.structure)
        self.gui.update_save_button_state(len(self.selected_files) > 0)

    def _get_all_files(self, structure, prefix=""):
        """Get all file paths from the repository structure."""
        files = set()
        for name, content in structure.items():
            full_path = os.path.join(prefix, name) if prefix else name
            if isinstance(content, dict):
                files.update(self._get_all_files(content, full_path))
            else:
                files.add(full_path)
        return files

    def on_file_select(self, event):
        """Handle file selection events in the treeview."""
        item = self.gui.tree.identify("item", event.x, event.y)
        if not item:
            return
        full_path = self.gui.tree.item(item, "text")
        is_dir = self._is_directory(full_path)

        if (not is_dir and full_path in self.selected_files) or (
            is_dir
            and any(f.startswith(full_path + os.sep) for f in self.selected_files)
        ):
            self._deselect_item(item, full_path, is_dir)
        else:
            self._select_item(item, full_path, is_dir)
        self.gui.update_save_button_state(len(self.selected_files) > 0)

    def _is_directory(self, path):
        """Check if a path represents a directory."""
        current = self.structure
        for part in path.split(os.sep):
            if part not in current or not isinstance(current[part], dict):
                return False
            current = current[part]
        return True

    def _select_item(self, item, path, is_dir):
        """Select an item and its children if it's a directory."""
        self.gui.tree.item(item, tags=())
        if is_dir:
            for child in self.gui.tree.get_children(item):
                child_path = self.gui.tree.item(child, "text")
                self._select_item(child, child_path, self._is_directory(child_path))
        else:
            self.selected_files.add(path)

    def _deselect_item(self, item, path, is_dir):
        """Deselect an item and its children if it's a directory."""
        self.gui.tree.item(item, tags=("strikethrough",))
        if is_dir:
            for child in self.gui.tree.get_children(item):
                child_path = self.gui.tree.item(child, "text")
                self._deselect_item(child, child_path, self._is_directory(child_path))
        else:
            self.selected_files.discard(path)

    def save_to_file(self):
        """Save selected files to an output file."""
        if not self.selected_files:
            messagebox.showwarning("Warning", "No files selected!")
            return
        writer = FileWriter(self.repo_handler, self.selected_files)
        writer.save_to_file("repo_contents.txt")
        messagebox.showinfo("Success", "Repository contents saved to repo_contents.txt")


if __name__ == "__main__":
    root_window = tk.Tk()
    app = GitRepoApp(root_window)
    root_window.mainloop()
