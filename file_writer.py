import logging
import os
import traceback

# Append to the same log file with detailed format
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    filename="repo_handler.log",
    filemode="a",
)
logger = logging.getLogger(__name__)


class FileWriter:
    def __init__(self, repo_handler, selected_files):
        logger.debug(
            f"__init__ called with repo_handler={repo_handler}, selected_files={selected_files}"
        )
        self.repo_handler = repo_handler
        self.selected_files = selected_files
        logger.info(
            f"FileWriter initialized with {len(selected_files)} files: {sorted(selected_files)}"
        )

    def save_to_file(self, output_file):
        logger.debug(f"save_to_file called with output_file='{output_file}'")
        logger.info(f"Starting save process to '{output_file}'")
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                logger.debug("File opened for writing")
                f.write("Directory structure:\n")
                logger.debug("Wrote 'Directory structure:' header")
                structure = self.repo_handler.get_repo_structure()
                logger.debug(f"Retrieved structure: {structure}")
                self._write_structure(f, structure)
                f.write("\nFiles Content:\n")
                logger.debug("Wrote 'Files Content:' header")
                # Ensure all files from structure are included if not explicitly deselected
                all_files = self._get_all_files(structure)
                logger.debug(f"All files from structure: {all_files}")
                self.selected_files = (
                    self.selected_files or all_files
                )  # Fallback to all files if selected_files is empty
                logger.debug(f"Final selected_files for content: {self.selected_files}")
                self._write_file_contents(f)
            logger.info(f"Successfully saved to '{output_file}'")
        except Exception as e:
            logger.error(f"Failed to save to '{output_file}': {str(e)}")
            logger.debug(f"Exception traceback: {traceback.format_exc()}")
            raise

    def _write_structure(self, file, structure, prefix=""):
        logger.debug(
            f"_write_structure called with prefix='{prefix}', structure={structure}"
        )
        for name, content in structure.items():
            logger.debug(f"Processing item: name='{name}', content={content}")
            if isinstance(content, dict):
                line = f"{prefix}└── {name}/\n"
                file.write(line)
                logger.debug(f"Wrote directory line: '{line.strip()}'")
                self._write_structure(file, content, prefix + "    ")
            else:
                line = f"{prefix}    ├── {name}\n"
                file.write(line)
                logger.debug(f"Wrote file line: '{line.strip()}'")
        logger.debug(f"Finished writing structure at prefix='{prefix}'")

    def _write_file_contents(self, file):
        logger.debug(
            f"_write_file_contents called with selected_files={self.selected_files}"
        )
        sorted_files = sorted(self.selected_files)
        logger.debug(f"Sorted files for writing: {sorted_files}")
        for file_path in sorted_files:
            logger.debug(f"Processing file: '{file_path}'")
            content = self.repo_handler.get_file_content(file_path)
            logger.debug(
                f"Retrieved content for '{file_path}': {content[:100]}... (first 100 chars)"
            )
            header = f"\n{'=' * 48}\nFile: {file_path}\n{'=' * 48}\n"
            file.write(header)
            logger.debug(f"Wrote header: '{header.strip()}'")
            file.write(f"{content}\n")
            logger.debug(f"Wrote content for '{file_path}'")
        logger.debug("Finished writing all file contents")

    def _get_all_files(self, structure, prefix=""):
        logger.debug(
            f"_get_all_files called with structure={structure}, prefix='{prefix}'"
        )
        files = set()
        for name, content in structure.items():
            full_path = os.path.join(prefix, name) if prefix else name
            logger.debug(
                f"Processing item: name='{name}', full_path='{full_path}', content={content}"
            )
            if isinstance(content, dict):
                sub_files = self._get_all_files(content, full_path)
                files.update(sub_files)
                logger.debug(f"Added sub-files from '{full_path}': {sub_files}")
            else:
                files.add(full_path)
                logger.debug(f"Added file: '{full_path}'")
        logger.debug(f"Returning files: {files}")
        return files
