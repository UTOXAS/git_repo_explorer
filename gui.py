import tkinter as tk
from tkinter import ttk
import os

"""Module for managing the GUI in Git Repository Explorer."""


class RepositoryGUI:
    """Handles the graphical user interface for the repository explorer."""

    def __init__(self, root, app, process_callback):
        self.root = root
        self.app = app
        self.process_callback = process_callback
        self.item_tags = []  # Track tags for each item
        self.item_full_paths = []  # Track full paths for each item
        self.create_widgets()

    def create_widgets(self):
        """Create and configure all GUI widgets."""
        self.main_frame = ttk.Frame(self.root, padding=30, style="Main.TFrame")
        self.main_frame.pack(fill="both", expand=True)

        self.input_label = ttk.Label(
            self.main_frame, text="REPO URL OR PATH", style="Heading.TLabel"
        )
        self.input_label.pack(pady=(0, 10))

        self.input_entry = tk.Entry(
            self.main_frame,
            width=40,
            font=("Consolas", 12, "bold"),
            relief="solid",
            borderwidth=3,
            bg="#E8ECEF",
            fg="#2B2D42",
            insertbackground="#FFB4A2",
        )
        self.input_entry.pack(pady=(0, 15))

        self.branch_label = ttk.Label(
            self.main_frame, text="BRANCH (OPT)", style="Subheading.TLabel"
        )
        self.branch_label.pack(pady=(0, 10))

        self.branch_entry = tk.Entry(
            self.main_frame,
            width=40,
            font=("Consolas", 12, "bold"),
            relief="solid",
            borderwidth=3,
            bg="#E8ECEF",
            fg="#2B2D42",
            insertbackground="#FFB4A2",
        )
        self.branch_entry.pack(pady=(0, 20))

        # Button frame for alignment
        self.button_frame = ttk.Frame(self.main_frame, style="Main.TFrame")
        self.button_frame.pack(fill="x", pady=(0, 15))

        self.process_button = ttk.Button(
            self.button_frame,
            text="EXPLORE",
            command=self.on_process,
            style="Primary.TButton",
        )
        self.process_button.pack(side="left", padx=10)

        self.toggle_button = ttk.Button(
            self.button_frame,
            text="TOGGLE ALL",
            command=self.app.toggle_all_selection,
            style="Secondary.TButton",
            state="disabled",
        )
        self.toggle_button.pack(side="right", padx=10)

        # Listbox with integrated scrollbar
        self.listbox_frame = ttk.Frame(self.main_frame, style="Main.TFrame")
        self.listbox_frame.pack(fill="both", expand=True)

        self.listbox = tk.Listbox(
            self.listbox_frame,
            font=("Consolas", 11),
            bg="#D8E2DC",
            fg="#2B2D42",
            selectmode="none",
            relief="solid",
            borderwidth=2,
            highlightthickness=0,
            activestyle="none",
            selectbackground="#FFB4A2",
            selectforeground="#2B2D42",
            height=15,
        )
        self.listbox.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(
            self.listbox_frame,
            orient="vertical",
            command=self.listbox.yview,
            style="Vertical.TScrollbar",
        )
        scrollbar.pack(side="right", fill="y")
        self.listbox.config(yscrollcommand=scrollbar.set)
        self.listbox.bind("<Button-1>", self.app.on_file_select)

        self.save_button = ttk.Button(
            self.main_frame,
            text="SAVE",
            command=self.app.save_to_file,
            style="Primary.TButton",
            state="disabled",
        )
        self.save_button.pack(pady=20)

    def on_process(self):
        """Process the repository when the explore button is clicked."""
        repo_path = self.input_entry.get().strip()
        branch = self.branch_entry.get().strip() or None
        if repo_path:
            self.process_callback(repo_path, branch)

    def display_structure(self, structure):
        """Display the repository structure in the listbox."""
        self.listbox.delete(0, tk.END)
        self.item_full_paths = []
        self.item_tags = []
        self._populate_listbox(structure)
        self.toggle_button["state"] = "normal"

    def _populate_listbox(self, structure, prefix="", path_prefix=""):
        """Populate the listbox with tree-like structure."""
        for name, content in structure.items():
            full_path = os.path.join(path_prefix, name) if path_prefix else name
            if isinstance(content, dict):
                display_name = f"{prefix}└── {name}/"
                self.listbox.insert(tk.END, display_name)
                self.item_full_paths.append(full_path)
                self.item_tags.append(())
                self._populate_listbox(content, prefix + "    ", full_path)
            else:
                display_name = f"{prefix}    ├── {name}"
                self.listbox.insert(tk.END, display_name)
                self.item_full_paths.append(full_path)
                self.item_tags.append(())

    def update_save_button_state(self, enabled):
        """Enable or disable the save button based on selection."""
        self.save_button["state"] = "normal" if enabled else "disabled"

    def get_item_text(self, index):
        """Get the full path of the item at the given index."""
        return self.item_full_paths[index]

    def set_item_tags(self, index, tags):
        """Set visual tags (e.g., strikethrough) for an item."""
        text = self.listbox.get(index).replace("\u0336", "")
        self.item_tags[index] = tags
        if "strikethrough" in tags:
            striked_text = "".join(c + "\u0336" for c in text)
            self.listbox.delete(index)
            self.listbox.insert(index, striked_text)
        else:
            self.listbox.delete(index)
            self.listbox.insert(index, text)

    def get_item_tags(self, index):
        """Get the tags for an item at the given index."""
        return self.item_tags[index]
