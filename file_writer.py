import os


class FileWriter:
    def __init__(self, repo_handler, selected_files):
        self.repo_handler = repo_handler
        self.selected_files = selected_files

    def save_to_file(self, output_file):
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("Directory structure:\n")
            structure = self.repo_handler.get_repo_structure()
            self._write_structure(f, structure)
            f.write("\nFiles Content:\n")
            all_files = self._get_all_files(structure)
            self.selected_files = self.selected_files or all_files
            self._write_file_contents(f)

    def _write_structure(self, file, structure, prefix=""):
        for name, content in structure.items():
            if isinstance(content, dict):
                file.write(f"{prefix}└── {name}/\n")
                self._write_structure(file, content, prefix + "    ")
            else:
                file.write(f"{prefix}    ├── {name}\n")

    def _write_file_contents(self, file):
        for file_path in sorted(self.selected_files):
            content = self.repo_handler.get_file_content(file_path)
            file.write(f"\n{'=' * 48}\nFile: {file_path}\n{'=' * 48}\n")
            file.write(f"{content}\n")

    def _get_all_files(self, structure, prefix=""):
        files = set()
        for name, content in structure.items():
            full_path = os.path.join(prefix, name) if prefix else name
            if isinstance(content, dict):
                files.update(self._get_all_files(content, full_path))
            else:
                files.add(full_path)
        return files
