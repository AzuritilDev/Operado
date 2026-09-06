import base64
import subprocess

def encode_waveform_ffmpeg(file_path, samples=256):
    """Uses FFmpeg directly to extract raw PCM data safely without pydub crashes."""
    cmd = [
        "ffmpeg", "-v", "error",
        "-i", str(file_path),
        "-f", "s16le",       # 16-bit Signed Integer PCM
        "-acodec", "pcm_s16le",
        "-ar", "8000",       # Low sample rate is fine for waveform calculations
        "-ac", "1",          # Mono channel
        "-"
    ]
    result = subprocess.run(cmd, capture_output=True, check=True)
    raw_data = result.stdout
    
    # Convert binary buffer to list of integers
    import struct
    fmt = f"{len(raw_data) // 2}h"
    raw_samples = list(struct.unpack(fmt, raw_data))

    if not raw_samples:
        return base64.b64encode(bytes([128] * samples)).decode("ascii")

    bucket_size = max(1, len(raw_samples) // samples)
    waveform = []

    for i in range(samples):
        start = i * bucket_size
        end = min(start + bucket_size, len(raw_samples))

        if start >= len(raw_samples):
            value = 0
        else:
            bucket = raw_samples[start:end]
            value = sum(abs(x) for x in bucket) / len(bucket)
        waveform.append(value)

    maximum = max(waveform) or 1
    # Discord prefers amplitudes scaled between 0 and 255
    waveform = [round((value / maximum) * 255) for value in waveform]

    return base64.b64encode(bytes(waveform)).decode("ascii")
