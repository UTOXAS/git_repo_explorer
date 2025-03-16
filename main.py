import tkinter as tk
from tkinter import ttk, messagebox
import os
from repo_handler import RepositoryHandler
from gui import RepositoryGUI
from file_writer import FileWriter


class GitRepoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Git Repository Explorer")
        self.root.geometry("800x600")
        self.setup_styles()
        self.gui = RepositoryGUI(self.root, self.process_repo)
        self.repo_handler = None
        self.selected_files = set()

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

    def process_repo(self, repo_path):
        try:
            self.repo_handler = RepositoryHandler(repo_path)
            structure = self.repo_handler.get_repo_structure()
            self.gui.display_structure(structure)
            self.selected_files = set(structure.keys())
            self.gui.update_save_button_state(len(self.selected_files) > 0)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def on_file_select(self, event):
        item = self.gui.tree.identify("item", event.x, event.y)
        if item:
            file_path = self.gui.tree.item(item, "text")
            if file_path in self.selected_files:
                self.selected_files.remove(file_path)
                self.gui.tree.item(item, tags=())
            else:
                self.selected_files.add(file_path)
                self.gui.tree.item(item, tags=("selected",))
            self.gui.update_save_button_state(len(self.selected_files) > 0)

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
