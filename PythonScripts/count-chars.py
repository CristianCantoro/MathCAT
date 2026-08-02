import os
import argparse
import re

MATCH = re.compile(r't: [\'\"](.*?)[\'\"]')
def count_t_strings(full_path: str) -> int:
    try:
        with open(full_path, 'r', encoding='utf8') as f:
            n_chars = 0
            for line in f:
                # The '.' in regex matches any character except newline (including UTF-8)
                match = MATCH.search(line)
                if match:
                    extracted_string = match.group(1)
                    n_chars += len(extracted_string)
            print(f"File: {full_path.rsplit(os.sep, 1)[1]}, Characters: {n_chars}")
            return n_chars
    except UnicodeDecodeError as e:
        print(f"Error: A file was found that is not valid UTF-8. {e}")
        return 0
            
    print(f"Total characters found: {n_chars}")

def main():
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description="Process .yaml files in a directory recursively.")
    parser.add_argument("directory", help="Path to the directory to scan")
    
    args = parser.parse_args()
    target_dir = args.directory

    # Verify the provided path is a directory
    if not os.path.isdir(target_dir):
        print(f"Error: {target_dir} is not a valid directory.")
        return

    # Walk through the directory tree recursively
    total_chars = 0
    for root, dirs, files in os.walk(target_dir):
        for file in files:
            # Check for .yaml or .yml extensions
            if file.lower().endswith(('.yaml', '.yml')):
                full_path = os.path.join(root, file)
                total_chars += count_t_strings(full_path)
    print(f"Total characters found: {total_chars}")

if __name__ == "__main__":
    main()
