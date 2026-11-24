import os
import threading
from tkinter import filedialog, messagebox
import customtkinter as ctk
from gui import RepositoryGUI
from repo_handler import RepositoryHandler
from file_writer import FileWriter

"""Module for running the main application of Git Repository Explorer."""


class GitRepoApp:
    """Main application class managing the repository explorer functionality."""

    def __init__(self, window):
        self.root = window
        self.root.title("Git Repo Explorer")
        # MODIFIED: Larger default responsive window with minimum size constraints
        self.root.geometry("1120x740")
        self.root.minsize(860, 560)

        self.gui = RepositoryGUI(self.root, self, self.process_repo)
        self.repo_handler = None
        self.selected_files = set()
        self.structure = {}
        self.all_selected = True

        # ADDED: Clean up temp directories when closing the window
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def process_repo(self, repo_path, branch=None):
        """Clone/load the repository asynchronously without freezing the UI."""
        self.gui.set_loading(True, f"Loading repository: {repo_path}...")

        def worker():
            try:
                if self.repo_handler:
                    self.repo_handler.cleanup()
                handler = RepositoryHandler(repo_path, branch)
                commits = handler.get_commits(max_count=100)
                structure = handler.get_repo_structure()
                self.root.after(
                    0, lambda: self._on_repo_loaded(handler, commits, structure)
                )
            except Exception as exc:
                self.root.after(0, lambda err=exc: self._on_repo_error(str(err)))

        threading.Thread(target=worker, daemon=True).start()

    def _on_repo_loaded(self, handler, commits, structure):
        """Update UI once repository and commit history are loaded."""
        self.repo_handler = handler
        self.structure = structure
        self.selected_files = self._get_all_files(self.structure)
        self.all_selected = True

        self.gui.set_commits(commits, active_sha=handler.current_commit)
        self.gui.display_structure(self.structure)
        self.gui.sync_checkbox_states(self.selected_files)
        self.gui.update_save_button_state(len(self.selected_files) > 0)
        self.gui.show_file_preview(
            "Repository Ready",
            f"Loaded {len(self.selected_files)} files at commit {handler.current_commit[:7]}.\n"
            "Click any file on the left to inspect its contents, or switch commits above.",
        )
        self.gui.set_loading(
            False, f"Loaded commit {handler.current_commit[:7]} ({len(self.selected_files)} files)"
        )

    def _on_repo_error(self, error_message):
        """Handle errors during repository loading or checkout."""
        self.gui.set_loading(False, "Error loading repository")
        messagebox.showerror("Repository Error", error_message)

    # ADDED: Handle switching to a past commit from the dropdown
    def on_commit_selected(self, commit_sha):
        """Checkout the selected commit asynchronously and refresh the file tree."""
        if not self.repo_handler or commit_sha == self.repo_handler.current_commit:
            return

        self.gui.set_loading(True, f"Checking out commit {commit_sha[:7]}...")

        def worker():
            try:
                self.repo_handler.checkout_commit(commit_sha)
                structure = self.repo_handler.get_repo_structure()
                self.root.after(
                    0, lambda: self._on_commit_checked_out(commit_sha, structure)
                )
            except Exception as exc:
                self.root.after(0, lambda err=exc: self._on_repo_error(str(err)))

        threading.Thread(target=worker, daemon=True).start()

    def _on_commit_checked_out(self, commit_sha, structure):
        """Refresh UI tree and selection after checking out a past commit."""
        self.structure = structure
        self.selected_files = self._get_all_files(self.structure)
        self.all_selected = True

        self.gui.display_structure(self.structure)
        self.gui.sync_checkbox_states(self.selected_files)
        self.gui.update_save_button_state(len(self.selected_files) > 0)
        self.gui.show_file_preview(
            f"Commit {commit_sha[:7]}",
            f"Switched to commit {commit_sha[:7]} ({len(self.selected_files)} files).\n"
            "Select a file on the left to preview its content at this point in history.",
        )
        self.gui.set_loading(
            False, f"Active commit: {commit_sha[:7]} ({len(self.selected_files)} files)"
        )

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

    # MODIFIED: Clean checkbox toggle handler for both files and recursive folders
    def on_item_toggled(self, path, is_dir, is_checked):
        """Handle checkbox toggle events for files and folders."""
        if is_dir:
            folder_prefix = path + os.sep
            all_files = self._get_all_files(self.structure)
            for f in all_files:
                if f.startswith(folder_prefix):
                    if is_checked:
                        self.selected_files.add(f)
                    else:
                        self.selected_files.discard(f)
        else:
            if is_checked:
                self.selected_files.add(path)
            else:
                self.selected_files.discard(path)

        self.gui.sync_checkbox_states(self.selected_files)
        self.gui.update_save_button_state(len(self.selected_files) > 0)

    def toggle_all_selection(self):
        """Toggle selection state of all items."""
        all_files = self._get_all_files(self.structure)
        self.all_selected = len(self.selected_files) < len(all_files)
        if self.all_selected:
            self.selected_files = all_files
        else:
            self.selected_files.clear()

        self.gui.sync_checkbox_states(self.selected_files)
        self.gui.update_save_button_state(len(self.selected_files) > 0)

    # ADDED: Live file content preview handler
    def preview_file(self, file_path):
        """Load and display the selected file's content in the preview pane."""
        if not self.repo_handler:
            return
        content = self.repo_handler.get_file_content(file_path)
        self.gui.show_file_preview(file_path, content)

    def save_to_file(self):
        """Save selected files to a user-chosen output file."""
        if not self.selected_files:
            messagebox.showwarning("Warning", "No files selected!")
            return

        writer = FileWriter(self.repo_handler, self.selected_files)
        default_dir = writer.get_user_home_directory()
        short_sha = (
            self.repo_handler.current_commit[:7]
            if self.repo_handler and self.repo_handler.current_commit
            else "export"
        )

        # MODIFIED: Added Save As dialog with commit-tagged default filename
        full_filepath = filedialog.asksaveasfilename(
            title="Save Repository Contents",
            initialdir=default_dir,
            initialfile=f"repo_contents_{short_sha}.txt",
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("Markdown Files", "*.md"), ("All Files", "*.*")],
        )
        if not full_filepath:
            return

        writer.save_to_file(full_filepath)
        # MODIFIED: Fixed broken f-string interpolation (${full_filepath} -> {full_filepath})
        messagebox.showinfo(
            "Success",
            f"Repository contents saved to:\n{full_filepath}",
        )

    def on_closing(self):
        """Clean up temporary files on application exit."""
        if self.repo_handler:
            self.repo_handler.cleanup()
        self.root.destroy()


if __name__ == "__main__":
    # ADDED: Initialize modern CustomTkinter theme and scaling
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")

    root_window = ctk.CTk()
    app = GitRepoApp(root_window)
    root_window.mainloop()