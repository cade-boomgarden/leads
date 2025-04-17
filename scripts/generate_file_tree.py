import os

def generate_file_tree(start_path=".", ignore_folders=None, output_file="file_tree.txt"):
    if ignore_folders is None:
        ignore_folders = {"venv", "__pycache__", "migrations"}  # Default folder to ignore

    def tree(directory, prefix=""):
        entries = sorted(os.listdir(directory))
        for index, entry in enumerate(entries):
            entry_path = os.path.join(directory, entry)

            # Ignore hidden files and folders, and specified folders
            if entry.startswith(".") or entry in ignore_folders:
                continue

            connector = "├── " if index < len(entries) - 1 else "└── "
            file_tree.append(f"{prefix}{connector}{entry}")

            if os.path.isdir(entry_path):
                sub_prefix = "│   " if index < len(entries) - 1 else "    "
                tree(entry_path, prefix=prefix + sub_prefix)

    file_tree = []
    file_tree.append(start_path)
    tree(start_path)

    with open(output_file, "w") as f:
        f.write("\n".join(file_tree))

def run():
    # Change start_path if your Django project root is not the script's location
    generate_file_tree(start_path=".")