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
        self.root.title("GIT REPO EXPLORER")
        self.root.geometry("800x600")
        self.setup_styles()
        self.gui = RepositoryGUI(self.root, self, self.process_repo)
        self.repo_handler = None
        self.selected_files = set()
        self.structure = {}
        self.all_selected = True  # Track toggle state

    def setup_styles(self):
        """Configure the visual styles for the application."""
        style = ttk.Style()
        style.configure("Main.TFrame", background="#F5F6CE")  # Soft cream
        style.configure(
            "Heading.TLabel",
            font=("Consolas", 16, "bold"),
            background="#F5F6CE",
            foreground="#2B2D42",  # Dark slate
        )
        style.configure(
            "Subheading.TLabel",
            font=("Consolas", 12, "bold"),
            background="#F5F6CE",
            foreground="#2B2D42",
        )
        style.configure(
            "Primary.TButton",
            font=("Consolas", 12, "bold"),
            background="#FFB4A2",  # Soft peach
            foreground="#2B2D42",  # Dark slate for contrast
            borderwidth=3,
            relief="raised",
            padding=12,
        )
        style.map(
            "Primary.TButton",
            background=[("active", "#E59887")],
            relief=[("pressed", "sunken")],
        )
        style.configure(
            "Secondary.TButton",
            font=("Consolas", 12, "bold"),
            background="#A9DEF9",  # Light sky blue
            foreground="#2B2D42",  # Dark slate for contrast
            borderwidth=3,
            relief="raised",
            padding=12,
        )
        style.map(
            "Secondary.TButton",
            background=[("active", "#8CCDE8")],
            relief=[("pressed", "sunken")],
        )
        style.configure(
            "Vertical.TScrollbar",
            background="#D8E2DC",  # Match listbox
            troughcolor="#F5F6CE",
            borderwidth=2,
            relief="solid",
        )

    def process_repo(self, repo_path, branch=None):
        """Process the repository and update the GUI."""
        self.repo_handler = RepositoryHandler(repo_path, branch)
        self.structure = self.repo_handler.get_repo_structure()
        self.gui.display_structure(self.structure)
        self.selected_files = self._get_all_files(self.structure)
        self.all_selected = True
        self._update_all_visuals()
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
        """Select a folder and all its children recursively."""
        folder_prefix = folder_path + os.sep if folder_path else ""
        for i in range(self.gui.listbox.size()):
            item_path = self.gui.get_item_text(i)
            if item_path == folder_path or (
                folder_prefix and item_path.startswith(folder_prefix)
            ):
                self.gui.set_item_tags(i, ())
                if not self._is_directory(item_path):
                    self.selected_files.add(item_path)

    def _deselect_folder(self, folder_path):
        """Deselect a folder and all its children recursively."""
        folder_prefix = folder_path + os.sep if folder_path else ""
        for i in range(self.gui.listbox.size()):
            item_path = self.gui.get_item_text(i)
            if item_path == folder_path or (
                folder_prefix and item_path.startswith(folder_prefix)
            ):
                self.gui.set_item_tags(i, ("strikethrough",))
                if not self._is_directory(item_path):
                    self.selected_files.discard(item_path)

    def toggle_all_selection(self):
        """Toggle selection state of all items."""
        self.all_selected = not self.all_selected
        if self.all_selected:
            self.selected_files = self._get_all_files(self.structure)
        else:
            self.selected_files.clear()
        self._update_all_visuals()
        self.gui.update_save_button_state(self.all_selected)

    def _update_all_visuals(self):
        """Update visual state of all items based on toggle."""
        tags = () if self.all_selected else ("strikethrough",)
        for i in range(self.gui.listbox.size()):
            self.gui.set_item_tags(i, tags)

    def save_to_file(self):
        """Save selected files to an output file."""
        if not self.selected_files:
            messagebox.showwarning("Warning", "No files selected!")
            return
        writer = FileWriter(self.repo_handler, self.selected_files)
        user_home_directory = writer.get_user_home_directory()
        filename = "repo_contents.txt"
        full_filepath = os.path.join(user_home_directory, filename)
        writer.save_to_file(full_filepath)
        messagebox.showinfo(
            "Success",
            "Repository contents saved to ${full_filepath}",
        )


if __name__ == "__main__":
    root_window = tk.Tk()
    app = GitRepoApp(root_window)
    root_window.mainloop()
