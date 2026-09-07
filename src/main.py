import json
from pathlib import Path
import os
import sys
import argparse
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
DISCORD_API = "https://discord.com/api/v9"
IS_VOICE_MESSAGE = 1 << 13

def send_audio_file_as_voice_message(args):
    audio_path = args.file
    token = args.token
    reply_id = args.reply
    channel_id = args.channel
    mention = args.mention
    fail_if_not_exists = args.fail_if_not_exists

    target_endpoint = f"{DISCORD_API}/channels/{channel_id}/messages"

    # CRITICAL: Always use ffprobe over Mutagen for Discord voice UI payload metrics
    duration = get_ogg_duration_ffprobe(audio_path)

    # Temporary/simple waveform.
    # This is NOT a real waveform yet.
    waveform = encode_waveform_ffmpeg(audio_path)

    # Request body
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

    if reply_id != 0:
        additional_payload = {"message_reference": {
                "channel_id": str(channel_id),
                "message_id": str(reply_id),
                "fail_if_not_exists": True if fail_if_not_exists else False
            },
            # Optional: Control whether the reply sends a ping notification
            "allowed_mentions": {
                "replied_user": True if mention else False
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
        # Pass the direct multipart object raw string or bytes natively into the session
        response = session.post(
            url=target_endpoint,
            headers=headers,
            data=multipart.to_string() # Removed .decode("latin-1") to preserve binary layout integrity
        )

        print(response.status_code)
        return response.status_code

main_parser = argparse.ArgumentParser(description="OperadoCLI")
subparsers = main_parser.add_subparsers(dest="command", required=True)

parser_audio = subparsers.add_parser("audio")
parser_audio.add_argument("token", help="Your OAuth2 Token.", type=str)
parser_audio.add_argument("file", help="The file path to your .ogg audio file.", type=Path)
parser_audio.add_argument("channel", help="ID of the channel you want to send the message to.", type=int)
parser_audio.add_argument("--reply", "-ri", type=int, default=0)
parser_audio.add_argument("--mention", "-mt", action=argparse.BooleanOptionalAction)
parser_audio.add_argument("--fail-if-not-exists", "-fline", action=argparse.BooleanOptionalAction)

COMMAND_MAP = {
    "audio": send_audio_file_as_voice_message
}

def main(args : list[str]) -> None:
    parsed_args = main_parser.parse_args(args=args) 
    # fun fact: if you don't pass anything inside parse_args() it automatically passes sys.argv[1:] anyway
    
    chosen_cmd = COMMAND_MAP[parsed_args.command]
    chosen_cmd(parsed_args)

if __name__ == "__main__":
    main(sys.argv[1:])