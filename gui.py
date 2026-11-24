import os
import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk

"""Module for managing the modern responsive GUI in Git Repository Explorer."""


class RepositoryGUI:
    """Handles the modern graphical user interface for the repository explorer."""

    def __init__(self, root, app, process_callback):
        self.root = root
        self.app = app
        self.process_callback = process_callback

        # MODIFIED: Replaced fragile Unicode strikethrough tracking with clean state dictionaries
        self.tree_nodes = []  # List of dicts: {path, name, depth, is_dir, selected, widget, checkbox}
        self.commit_map = {}  # Maps dropdown label -> commit hexsha
        self.is_loading = False

        self.create_widgets()

    def create_widgets(self):
        """Create and configure all modern responsive GUI widgets."""
        # MODIFIED: Responsive 3-row grid layout
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)

        # ==================== TOP HEADER & CONTROLS ====================
        self.top_frame = ctk.CTkFrame(self.root, corner_radius=10)
        self.top_frame.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        self.top_frame.grid_columnconfigure(1, weight=1)

        # Title & Theme Switcher Row
        title_bar = ctk.CTkFrame(self.top_frame, fg_color="transparent")
        title_bar.grid(row=0, column=0, columnspan=4, sticky="ew", padx=14, pady=(12, 6))
        title_bar.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(
            title_bar,
            text="Git Repository Explorer",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        self.title_label.grid(row=0, column=0, sticky="w")

        self.theme_switch = ctk.CTkSegmentedButton(
            title_bar,
            values=["Dark", "Light", "System"],
            command=self._change_appearance_mode,
            width=180,
        )
        self.theme_switch.set("Dark")
        self.theme_switch.grid(row=0, column=1, sticky="e")

        # Input Row: Repo URL/Path + Browse + Branch + Explore
        ctk.CTkLabel(
            self.top_frame, text="Repository:", font=ctk.CTkFont(weight="bold")
        ).grid(row=1, column=0, sticky="w", padx=(14, 6), pady=6)

        repo_input_frame = ctk.CTkFrame(self.top_frame, fg_color="transparent")
        repo_input_frame.grid(row=1, column=1, sticky="ew", padx=4, pady=6)
        repo_input_frame.grid_columnconfigure(0, weight=1)

        self.input_entry = ctk.CTkEntry(
            repo_input_frame,
            placeholder_text="https://github.com/user/repo or C:\\path\\to\\local\\repo",
            height=36,
        )
        self.input_entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.input_entry.bind("<Return>", lambda e: self.on_process())

        # ADDED: Local directory browser button
        self.browse_button = ctk.CTkButton(
            repo_input_frame,
            text="Browse",
            width=80,
            height=36,
            fg_color=("gray75", "gray28"),
            text_color=("gray10", "gray90"),
            hover_color=("gray65", "gray35"),
            command=self._browse_local_repo,
        )
        self.browse_button.grid(row=0, column=1)

        self.branch_entry = ctk.CTkEntry(
            self.top_frame,
            placeholder_text="Branch (optional)",
            width=160,
            height=36,
        )
        self.branch_entry.grid(row=1, column=2, sticky="ew", padx=6, pady=6)
        self.branch_entry.bind("<Return>", lambda e: self.on_process())

        self.process_button = ctk.CTkButton(
            self.top_frame,
            text="Explore",
            width=110,
            height=36,
            font=ctk.CTkFont(weight="bold"),
            command=self.on_process,
        )
        self.process_button.grid(row=1, column=3, sticky="e", padx=(6, 14), pady=6)

        # ADDED: Commit Selector Row (Defaults to most recent commit)
        ctk.CTkLabel(
            self.top_frame, text="Commit:", font=ctk.CTkFont(weight="bold")
        ).grid(row=2, column=0, sticky="w", padx=(14, 6), pady=(4, 12))

        self.commit_dropdown = ctk.CTkOptionMenu(
            self.top_frame,
            values=["Load a repository to view commits..."],
            command=self._on_commit_dropdown_select,
            state="disabled",
            height=34,
            dynamic_resizing=False,
        )
        self.commit_dropdown.grid(
            row=2, column=1, columnspan=3, sticky="ew", padx=(4, 14), pady=(4, 12)
        )

        # ==================== MAIN SPLIT WORKSPACE ====================
        self.workspace_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self.workspace_frame.grid(row=1, column=0, sticky="nsew", padx=16, pady=4)
        self.workspace_frame.grid_columnconfigure(0, weight=4)
        self.workspace_frame.grid_columnconfigure(1, weight=6)
        self.workspace_frame.grid_rowconfigure(0, weight=1)

        # Left Pane: File Tree Explorer
        self.left_pane = ctk.CTkFrame(self.workspace_frame, corner_radius=10)
        self.left_pane.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.left_pane.grid_columnconfigure(0, weight=1)
        self.left_pane.grid_rowconfigure(2, weight=1)

        tree_header = ctk.CTkFrame(self.left_pane, fg_color="transparent")
        tree_header.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 4))
        tree_header.grid_columnconfigure(0, weight=1)

        self.selection_count_label = ctk.CTkLabel(
            tree_header,
            text="Files (0 selected)",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.selection_count_label.grid(row=0, column=0, sticky="w")

        self.toggle_button = ctk.CTkButton(
            tree_header,
            text="Toggle All",
            width=90,
            height=28,
            state="disabled",
            command=self.app.toggle_all_selection,
        )
        self.toggle_button.grid(row=0, column=1, sticky="e")

        # ADDED: Live file filter search input
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self._filter_tree())
        self.search_entry = ctk.CTkEntry(
            self.left_pane,
            placeholder_text="Filter files by name or path...",
            textvariable=self.search_var,
            height=30,
        )
        self.search_entry.grid(row=1, column=0, sticky="ew", padx=12, pady=(2, 6))

        # Scrollable Checkbox Tree
        self.tree_scroll = ctk.CTkScrollableFrame(
            self.left_pane, fg_color=("gray92", "gray14"), corner_radius=8
        )
        self.tree_scroll.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.tree_scroll.grid_columnconfigure(0, weight=1)

        # ADDED: Right Pane - Live File Content Preview
        self.right_pane = ctk.CTkFrame(self.workspace_frame, corner_radius=10)
        self.right_pane.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self.right_pane.grid_columnconfigure(0, weight=1)
        self.right_pane.grid_rowconfigure(1, weight=1)

        self.preview_header = ctk.CTkLabel(
            self.right_pane,
            text="File Preview (Click any file name to inspect)",
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        )
        self.preview_header.grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 6))

        self.preview_textbox = ctk.CTkTextbox(
            self.right_pane,
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="none",
            activate_scrollbars=True,
        )
        self.preview_textbox.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.preview_textbox.insert("1.0", "Select a repository to inspect its structure and file contents.")
        self.preview_textbox.configure(state="disabled")

        # ==================== BOTTOM ACTION & STATUS BAR ====================
        self.bottom_frame = ctk.CTkFrame(self.root, corner_radius=10)
        self.bottom_frame.grid(row=2, column=0, sticky="ew", padx=16, pady=(8, 16))
        self.bottom_frame.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            self.bottom_frame,
            text="Ready",
            font=ctk.CTkFont(size=12),
            anchor="w",
        )
        self.status_label.grid(row=0, column=0, sticky="w", padx=14, pady=10)

        self.progress_bar = ctk.CTkProgressBar(self.bottom_frame, width=160, mode="indeterminate")

        self.save_button = ctk.CTkButton(
            self.bottom_frame,
            text="Export Selected to File",
            height=36,
            width=190,
            font=ctk.CTkFont(weight="bold"),
            fg_color="#2FA572",
            hover_color="#248259",
            state="disabled",
            command=self.app.save_to_file,
        )
        self.save_button.grid(row=0, column=2, sticky="e", padx=14, pady=10)

    def _change_appearance_mode(self, mode):
        ctk.set_appearance_mode(mode)

    def _browse_local_repo(self):
        folder = filedialog.askdirectory(title="Select Local Git Repository")
        if folder:
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, folder)

    def on_process(self):
        """Process the repository when the explore button is clicked."""
        if self.is_loading:
            return
        repo_path = self.input_entry.get().strip()
        branch = self.branch_entry.get().strip() or None
        if repo_path:
            self.process_callback(repo_path, branch)

    # ADDED: Populate commit dropdown with latest commit selected by default
    def set_commits(self, commits, active_sha=None):
        """Populate commit selector dropdown."""
        self.commit_map.clear()
        if not commits:
            self.commit_dropdown.configure(values=["No commits found"], state="disabled")
            self.commit_dropdown.set("No commits found")
            return

        labels = []
        selected_label = commits[0]["label"]
        for c in commits:
            self.commit_map[c["label"]] = c["hexsha"]
            labels.append(c["label"])
            if active_sha and c["hexsha"] == active_sha:
                selected_label = c["label"]

        self.commit_dropdown.configure(values=labels, state="normal")
        self.commit_dropdown.set(selected_label)

    def _on_commit_dropdown_select(self, selected_label):
        """Handle user selecting a past commit from the dropdown."""
        commit_sha = self.commit_map.get(selected_label)
        if commit_sha:
            self.app.on_commit_selected(commit_sha)

    def set_loading(self, loading, status_text=""):
        """Toggle loading indicator and disable controls during Git operations."""
        self.is_loading = loading
        self.status_label.configure(text=status_text)
        state = "disabled" if loading else "normal"
        self.process_button.configure(state=state)
        self.browse_button.configure(state=state)
        if self.commit_map:
            self.commit_dropdown.configure(state=state)

        if loading:
            self.progress_bar.grid(row=0, column=1, padx=10, pady=10)
            self.progress_bar.start()
        else:
            self.progress_bar.stop()
            self.progress_bar.grid_forget()

    def display_structure(self, structure):
        """Display the repository structure as an interactive checkbox tree."""
        for widget in self.tree_scroll.winfo_children():
            widget.destroy()
        self.tree_nodes.clear()
        self.search_var.set("")

        self._populate_tree(structure)
        self.toggle_button.configure(state="normal")
        self.update_selection_count(len(self.app.selected_files))

    def _populate_tree(self, structure, depth=0, path_prefix=""):
        """Recursively build modern interactive rows for folders and files."""
        sorted_items = sorted(
            structure.items(), key=lambda item: (not isinstance(item[1], dict), item[0].lower())
        )
        for name, content in sorted_items:
            full_path = os.path.join(path_prefix, name) if path_prefix else name
            is_dir = isinstance(content, dict)

            row_frame = ctk.CTkFrame(self.tree_scroll, fg_color="transparent", height=28)
            row_frame.pack(fill="x", pady=1)

            var = tk.BooleanVar(value=True)
            cb = ctk.CTkCheckBox(
                row_frame,
                text="",
                variable=var,
                width=20,
                height=20,
                checkbox_width=18,
                checkbox_height=18,
                command=lambda p=full_path, d=is_dir, v=var: self.app.on_item_toggled(
                    p, d, v.get()
                ),
            )
            cb.pack(side="left", padx=(depth * 18 + 4, 4))

            icon = "📁" if is_dir else "📄"
            label_font = ctk.CTkFont(
                family="Consolas", size=12, weight="bold" if is_dir else "normal"
            )
            item_btn = ctk.CTkButton(
                row_frame,
                text=f"{icon} {name}",
                font=label_font,
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray82", "gray24"),
                anchor="w",
                height=24,
                command=lambda p=full_path, d=is_dir: self._on_item_clicked(p, d),
            )
            item_btn.pack(side="left", fill="x", expand=True)

            self.tree_nodes.append(
                {
                    "path": full_path,
                    "name": name,
                    "depth": depth,
                    "is_dir": is_dir,
                    "var": var,
                    "frame": row_frame,
                }
            )

            if is_dir:
                self._populate_tree(content, depth + 1, full_path)

    def _on_item_clicked(self, full_path, is_dir):
        """Preview file contents when a file label is clicked."""
        if not is_dir:
            self.app.preview_file(full_path)

    def _filter_tree(self):
        """Filter visible tree items based on search query."""
        query = self.search_var.get().strip().lower()
        for node in self.tree_nodes:
            if not query or query in node["path"].lower():
                node["frame"].pack(fill="x", pady=1)
            else:
                node["frame"].pack_forget()

    def sync_checkbox_states(self, selected_files):
        """Synchronize all folder and file checkboxes with the selected_files set."""
        for node in self.tree_nodes:
            path = node["path"]
            if node["is_dir"]:
                prefix = path + os.sep
                has_selected_child = any(
                    f.startswith(prefix) for f in selected_files
                )
                node["var"].set(has_selected_child)
            else:
                node["var"].set(path in selected_files)
        self.update_selection_count(len(selected_files))

    def update_selection_count(self, count):
        """Update selected file counter label."""
        self.selection_count_label.configure(text=f"Files ({count} selected)")

    def show_file_preview(self, file_path, content):
        """Render file content in the right-hand preview pane."""
        self.preview_header.configure(text=f"Preview: {file_path}")
        self.preview_textbox.configure(state="normal")
        self.preview_textbox.delete("1.0", tk.END)
        self.preview_textbox.insert("1.0", content)
        self.preview_textbox.configure(state="disabled")

    def update_save_button_state(self, enabled):
        """Enable or disable the save button based on selection."""
        self.save_button.configure(state="normal" if enabled else "disabled")