import json
from pathlib import Path
# from mutagen.oggvorbis import OggVorbis
from mutagen.oggopus import OggOpus
import random
import dotenv
import os
import tls_client
from requests_toolbelt.multipart.encoder import MultipartEncoder
import base64
# import io
from pydub import AudioSegment
import subprocess 

"""
This is the initial version of the CLI app, it may look rough around the edges 
so that's why it doesn't look very user friendly

Add the following to the payload when you are replying to someone:

 # Add the reply reference block here:
    "message_reference": {
        "channel_id": str(channel_id),
        "message_id": str(reply_message_id),
        "fail_if_not_exists": False # True if you want the request to fail if the original message was deleted
    },
    # Optional: Control whether the reply sends a ping notification
    "allowed_mentions": {
        "replied_user": False # Set to True if you want to ping the author of the original message
    }
"""

"""
ffmpeg -i input.mp4 output.ogg

After doing that, make sure to do:

ffmpeg -i input.ogg -map 0:a:0 -vn -c:a libopus -ar 48000 -ac 1 -b:a 64k output.ogg

to make it Opus compatible and then verify it using:

ffprobe -v error -select_streams a:0 \
-show_entries stream=codec_name,codec_type,sample_rate,channels \
-of default=noprint_wrappers=1 output.ogg

This is the result you want:

codec_name=opus
codec_type=audio
sample_rate=48000
channels=1
"""

dotenv.load_dotenv()

DISCORD_API = "https://discord.com/api/v9"
IS_VOICE_MESSAGE = 1 << 13

def randomize_user_agent() -> str:
        discord_versions = [
            "69548",
            "69547",
            "69546",
            "69545"
        ]
        
        darwin_versions = [
            "24.3.0",
            "24.2.0",
            "24.1.0",
            "23.3.0"
        ]
        
        cfnetwork_versions = [
            "3826.400.110",
            "3826.400.100",
            "3826.300.110"
        ]
        
        version = random.choice(discord_versions)
        darwin = random.choice(darwin_versions)
        cfnet = random.choice(cfnetwork_versions)
        
        return f'Discord/{version} CFNetwork/{cfnet} Darwin/{darwin}'

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

def encode_waveform(file_path, samples=256):
    audio = AudioSegment.from_ogg(file_path)

    # Convert to mono
    audio = audio.set_channels(1)

    # Get raw samples
    raw = audio.get_array_of_samples()

    # Divide the audio into `samples` buckets
    bucket_size = max(1, len(raw) // samples)

    waveform = []

    for i in range(samples):
        start = i * bucket_size
        end = min(start + bucket_size, len(raw))

        if start >= len(raw):
            value = 0
        else:
            bucket = raw[start:end]

            # Average absolute amplitude
            value = sum(abs(x) for x in bucket) / len(bucket)

        waveform.append(value)

    # Normalize to 0-255
    maximum = max(waveform) or 1
    waveform = [
        round((value / maximum) * 255)
        for value in waveform
    ]

    return base64.b64encode(bytes(waveform)).decode("ascii")

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

def send_voice_message(
    token: str,
    channel_id: int,
    audio_path: Path,
    target_url: str,
    repyling: bool,
):
    # CRITICAL: Always use ffprobe over Mutagen for Discord voice UI payload metrics
    duration = get_ogg_duration_ffprobe(audio_path)

    # Temporary/simple waveform.
    # This is NOT a real waveform yet.
    waveform = encode_waveform_ffmpeg(audio_path)
    
    payload = {
        "flags": IS_VOICE_MESSAGE,
        "attachments": [
            {
                "id": "0",
                "filename": audio_path.name,
                "duration_secs": duration,
                "waveform": waveform,
            }
        ],
    }

    if repyling == True:
        additional_payload = {"message_reference": {
                "channel_id": str(channel_id),
                "message_id": str(),
                "fail_if_not_exists": False # True if you want the request to fail if the original message was deleted
            },
            # Optional: Control whether the reply sends a ping notification
            "allowed_mentions": {
                "replied_user": False # Set to True if you want to ping the author of the original message
            }
        }

        payload.update(additional_payload)

    headers = {
        'accept': '*/*',
        'accept-language': 'fr-HU,en-HU;q=0.9,ar-HU;q=0.8,ru-HU;q=0.7,zh-Hant-HU;q=0.6,tr-HU;q=0.5,el-HU;q=0.4,am-HU;q=0.3,hi-HU;q=0.2,es-HU;q=0.1,my-HU;q=0.1',
        'authorization': f"{token}",
        'connection': 'keep-alive',
        'host': 'discord.com',
        'user-agent': randomize_user_agent(),
        'x-debug-options': 'bugReporterEnabled',
        'x-discord-locale': 'en-US',
        'x-discord-timezone': 'Europe/Budapest',
    }

    session = tls_client.Session()

    with open(audio_path, "rb") as audio_file:
        multipart = MultipartEncoder(
            fields={
                "payload_json": (
                    None,
                    json.dumps(payload),
                    "application/json",
                ),
                "files[0]": (
                    audio_path.name,
                    audio_file,
                    "audio/ogg",
                ),
            }
        )

        headers = {
            **headers,
            "content-type": multipart.content_type,
        }

        # NOTE: Using multipart.to_string().decode("latin-1") can corrupt the binary audio data payload.
        # Pass the direct multipart object raw string or bytes natively into the session!
        response = session.post(
            url=target_url,
            headers=headers,
            data=multipart.to_string() # Removed .decode("latin-1") to preserve binary layout integrity
        )

        print(response.status_code)
        return response.status_code

channel_id = int(os.getenv("CHANNEL_ID"))

wanted_url1 = f"{DISCORD_API}/channels/{channel_id}/messages"
wanted_url2 = f"{DISCORD_API}/channels/@me/{channel_id}"

def main():
    send_voice_message(
        token=str(os.getenv("TOKEN")),
        channel_id=channel_id,
        audio_path=Path(
            r"file_name"
        ),
        target_url=wanted_url1,
        repyling=False,
    )

if __name__ == "__main__":
    main()