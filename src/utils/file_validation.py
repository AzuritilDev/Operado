import magic
from pathlib import Path

def validate_path_structure(path: Path) -> bool:
    if not path.exists():
        print("Error: Path does not exist.")
        return False
    if not path.is_file():
        print("Error: Path points to a directory, not a file.")
        return False
        
    return True

ALLOWED_FORMATS = {
    ".ogg": "audio/ogg"
}

def validate_file_format(path: Path) -> bool:
    file_extension = path.suffix.lower()  # Extracts extension (e.g., '.ogg')
    
    # Validate Extension
    if file_extension not in ALLOWED_FORMATS:
        print(f"Error: Extension '{file_extension}' is not allowed.")
        return False
        
    # Validate Actual File Payload (MIME type verification)
    try:
        # Read the first 2048 bytes to deduce the file type safely
        file_mime = magic.from_buffer(path.read_bytes()[:2048], mime=True)
    except Exception as e:
        print(f"Error reading file content: {e}")
        return False

    expected_mime = ALLOWED_FORMATS[file_extension]
    if file_mime != expected_mime:
        print(f"Spoofing Alert! Extension is {file_extension} but internal type is {file_mime}.")
        return False
        
    return True
