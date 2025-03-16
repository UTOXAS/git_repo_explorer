import tkinter as tk
from tkinter import ttk


class RepositoryGUI:
    def __init__(self, root, process_callback):
        self.root = root
        self.process_callback = process_callback
        self.create_widgets()

    def create_widgets(self):
        self.main_frame = ttk.Frame(self.root, padding=20)
        self.main_frame.pack(fill="both", expand=True)

        self.input_label = ttk.Label(
            self.main_frame, text="Enter Git Repo URL or Local Path:"
        )
        self.input_label.pack(pady=(0, 5))

        self.input_entry = tk.Entry(
            self.main_frame, width=50, font=("Arial", 12), relief="solid", borderwidth=3
        )
        self.input_entry.pack(pady=(0, 10))

        self.process_button = ttk.Button(
            self.main_frame, text="Process", command=self.on_process
        )
        self.process_button.pack(pady=(0, 10))

        self.tree = ttk.Treeview(self.main_frame, show="tree", selectmode="none")
        self.tree.pack(fill="both", expand=True)
        self.tree.tag_configure("selected", background="#FFCCCB")
        self.tree.bind("<Button-1>", self.root.git_app.on_file_select)

        self.save_button = ttk.Button(
            self.main_frame,
            text="Save to File",
            command=self.root.git_app.save_to_file,
            state="disabled",
        )
        self.save_button.pack(pady=10)

    def on_process(self):
        repo_path = self.input_entry.get().strip()
        if repo_path:
            self.process_callback(repo_path)

    def display_structure(self, structure):
        self.tree.delete(*self.tree.get_children())
        self._populate_tree("", structure)

    def _populate_tree(self, parent, structure):
        for path, is_dir in structure.items():
            if is_dir:
                node = self.tree.insert(parent, "end", text=path, open=False)
                self._populate_tree(node, structure[path])
            else:
                self.tree.insert(parent, "end", text=path, tags=("selected",))

    def update_save_button_state(self, enabled):
        self.save_button["state"] = "normal" if enabled else "disabled"
