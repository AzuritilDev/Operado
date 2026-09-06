import json
from pathlib import Path
import dotenv
import os
import tls_client
from requests_toolbelt.multipart.encoder import MultipartEncoder
from utils.headers import randomize_user_agent
from utils.ogg import get_ogg_duration_ffprobe
from utils.waveform import encode_waveform_ffmpeg

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
        "Accept": "*/*",
        "Accept-Language": "fr-HU,en-HU;q=0.9,ar-HU;q=0.8,ru-HU;q=0.7,zh-Hant-HU;q=0.6,tr-HU;q=0.5,el-HU;q=0.4,am-HU;q=0.3,hi-HU;q=0.2,es-HU;q=0.1,my-HU;q=0.1",
        "Authorization": f"{token}",
        "Connection": "keep-alive",
        "Host": "discord.com",
        "User-Agent": randomize_user_agent(),
        'X-Debug-Options': "bugReporterEnabled",
        "X-Discord-Locale": "en-US",
        "X-Discord-Timezone": "Europe/Budapest",
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
            "Content-Type": multipart.content_type,
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