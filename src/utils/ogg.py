"""This is where we handle things related to the .ogg file"""
import json
import subprocess
from mutagen.oggopus import OggOpus
from pathlib import Path

def get_ogg_duration(file_path: Path) -> float:
    audio = OggOpus(file_path)
    print(audio.info.length)
    return audio.info.length


def get_ogg_duration_ffprobe(file_path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "json", str(file_path),
        ],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(result.stdout)
    return float(data["format"]["duration"])