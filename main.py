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

    def process_repo(self, repo_path, branch=None):
        """Process the repository and update the GUI."""
        self.repo_handler = RepositoryHandler(repo_path, branch)
        self.structure = self.repo_handler.get_repo_structure()
        self.gui.display_structure(self.structure)
        self.selected_files = self._get_all_files(
            self.structure
        )  # All files initially selected
        # Ensure all items (files and folders) are visually selected (no strikethrough)
        for i in range(self.gui.listbox.size()):
            self.gui.set_item_tags(i, ())
        self.gui.update_save_button_state(True)

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
        """Handle file selection events in the listbox."""
        index = self.gui.listbox.nearest(event.y)
        if index < 0:
            return
        full_path = self.gui.get_item_text(index)
        is_dir = self._is_directory(full_path)
        is_selected = "strikethrough" not in self.gui.get_item_tags(index)

        if is_dir:
            if is_selected:
                self._deselect_folder(full_path)
            else:
                self._select_folder(full_path)
        else:
            if is_selected:
                self._deselect_file(index, full_path)
            else:
                self._select_file(index, full_path)
        self.gui.update_save_button_state(len(self.selected_files) > 0)

    def _is_directory(self, path):
        """Check if a path represents a directory."""
        current = self.structure
        for part in path.split(os.sep):
            if part not in current or not isinstance(current[part], dict):
                return False
            current = current[part]
        return True

    def _select_file(self, index, path):
        """Select a single file and remove strikethrough."""
        self.gui.set_item_tags(index, ())
        self.selected_files.add(path)

    def _deselect_file(self, index, path):
        """Deselect a single file and apply strikethrough."""
        self.gui.set_item_tags(index, ("strikethrough",))
        self.selected_files.discard(path)

    def _select_folder(self, folder_path):
        """Select a folder and all its children recursively, removing strikethrough."""
        folder_prefix = folder_path + os.sep if folder_path else ""
        for i in range(self.gui.listbox.size()):
            item_path = self.gui.get_item_text(i)
            # Select the folder itself or any item within it
            if item_path == folder_path or (
                folder_prefix and item_path.startswith(folder_prefix)
            ):
                self.gui.set_item_tags(i, ())  # Remove strikethrough
                if not self._is_directory(item_path):
                    self.selected_files.add(item_path)

    def _deselect_folder(self, folder_path):
        """Deselect a folder and all its children recursively, applying strikethrough."""
        folder_prefix = folder_path + os.sep if folder_path else ""
        for i in range(self.gui.listbox.size()):
            item_path = self.gui.get_item_text(i)
            # Deselect the folder itself or any item within it
            if item_path == folder_path or (
                folder_prefix and item_path.startswith(folder_prefix)
            ):
                self.gui.set_item_tags(i, ("strikethrough",))  # Apply strikethrough
                if not self._is_directory(item_path):
                    self.selected_files.discard(item_path)

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
