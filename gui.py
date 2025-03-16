import tkinter as tk
from tkinter import ttk
import os


class RepositoryGUI:
    def __init__(self, root, app, process_callback):
        self.root = root
        self.app = app
        self.process_callback = process_callback
        self.create_widgets()

    def create_widgets(self):
        self.main_frame = ttk.Frame(self.root, padding=25, style="Main.TFrame")
        self.main_frame.pack(fill="both", expand=True)

        self.input_label = ttk.Label(
            self.main_frame, text="Repository URL or Path:", style="Heading.TLabel"
        )
        self.input_label.pack(pady=(0, 8))

        self.input_entry = tk.Entry(
            self.main_frame,
            width=50,
            font=("Arial", 11),
            relief="flat",
            bg="#F7F7F7",
            bd=0,
            highlightthickness=1,
            highlightcolor="#D0D5DD",
        )
        self.input_entry.pack(pady=(0, 12))

        self.branch_label = ttk.Label(
            self.main_frame, text="Branch (optional):", style="Subheading.TLabel"
        )
        self.branch_label.pack(pady=(0, 8))

        self.branch_entry = tk.Entry(
            self.main_frame,
            width=50,
            font=("Arial", 11),
            relief="flat",
            bg="#F7F7F7",
            bd=0,
            highlightthickness=1,
            highlightcolor="#D0D5DD",
        )
        self.branch_entry.pack(pady=(0, 15))

        self.process_button = ttk.Button(
            self.main_frame,
            text="Explore",
            command=self.on_process,
            style="Primary.TButton",
        )
        self.process_button.pack(pady=(0, 20))

        self.tree = ttk.Treeview(
            self.main_frame, show="tree", selectmode="none", style="Custom.Treeview"
        )
        self.tree.pack(fill="both", expand=True)
        self.tree.tag_configure("strikethrough", font=("Arial", 10, "overstrike"))
        self.tree.bind("<Button-1>", self.app.on_file_select)

        self.save_button = ttk.Button(
            self.main_frame,
            text="Save Selection",
            command=self.app.save_to_file,
            style="Primary.TButton",
            state="disabled",
        )
        self.save_button.pack(pady=20)

    def on_process(self):
        repo_path = self.input_entry.get().strip()
        branch = self.branch_entry.get().strip() or None
        if repo_path:
            self.process_callback(repo_path, branch)

    def display_structure(self, structure):
        self.tree.delete(*self.tree.get_children())
        self._populate_tree("", structure)

    def _populate_tree(self, parent, structure):
        for path, content in structure.items():
            full_path = (
                path
                if not parent
                else os.path.join(self.tree.item(parent, "text"), path)
            )
            # Remove open=True to prevent collapsing functionality
            node = self.tree.insert(parent, "end", text=path)
            if isinstance(content, dict):
                self._populate_tree(node, content)
            # Files are added without any special tags initially (selected by default)
