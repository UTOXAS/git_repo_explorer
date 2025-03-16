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
        self.create_widgets()

    def create_widgets(self):
        """Create and configure all GUI widgets."""
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

        self.listbox = tk.Listbox(
            self.main_frame,
            font=("Arial", 10),
            bg="#FFFFFF",
            fg="#374151",
            selectmode="none",
            relief="solid",
            borderwidth=1,
            highlightthickness=0,
            activestyle="none",  # No active style change
            selectbackground="#FFFFFF",  # Match background to remove highlighting
            selectforeground="#374151",  # Match foreground to remove highlighting
        )
        self.listbox.pack(fill="both", expand=True)
        self.listbox.bind("<Button-1>", self.app.on_file_select)

        self.save_button = ttk.Button(
            self.main_frame,
            text="Save Selection",
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
        self.item_tags = []
        self._populate_listbox(structure)

    def _populate_listbox(self, structure, prefix=""):
        """Populate the listbox with tree-like structure."""
        for name, content in structure.items():
            if isinstance(content, dict):
                display_name = f"{prefix}└── {name}/"
                self.listbox.insert(tk.END, display_name)
                self.item_tags.append(())  # Initially selected, no strikethrough
                self._populate_listbox(content, prefix + "    ")
            else:
                display_name = f"{prefix}    ├── {name}"
                self.listbox.insert(tk.END, display_name)
                self.item_tags.append(())  # Initially selected, no strikethrough

    def update_save_button_state(self, enabled):
        """Enable or disable the save button based on selection."""
        self.save_button["state"] = "normal" if enabled else "disabled"

    def get_item_text(self, index):
        """Get the actual path from the display text at the given index."""
        display_text = self.listbox.get(index).replace(
            "\u0336", ""
        )  # Remove strikethrough
        if "└──" in display_text:
            return display_text.split("└── ")[1].rstrip("/")
        return display_text.split("├── ")[1]

    def set_item_tags(self, index, tags):
        """Set visual tags (e.g., strikethrough) for an item."""
        text = self.listbox.get(index).replace("\u0336", "")  # Clean original text
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
