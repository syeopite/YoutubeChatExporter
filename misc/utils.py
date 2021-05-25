import json

import requests

HARDCODED_API_KEY = "AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8"
HARDCODED_CLIENT_VERS = "2.20210330.08.00"


def translate_rgb_int_to_tuple(rgbint):
    return (rgbint >> 16) & 255, (rgbint >> 8) & 255, rgbint & 255


def clean_path(path):
    for path_char in ["/", "\\"]:
        path = path.replace(path_char, "")
    return path


# Since pytchat no longer returns video information we'll going to have to fetch it
# ourselves.
def fetch_video_information(video_id: str):
    """Requests youtube/v1/watch endpoint for video information

    The following code is an transcription of Invidious's crystal code, more specifically of PR #1985

    Parameter
        video_id: Youtube video id
    """

    request_data = {
        "videoId": video_id,
        "context": {
            "client": {
                "hl": "en",
                "gl": "US",
                "clientName": "WEB",
                "clientVersion": HARDCODED_CLIENT_VERS
            }
        }
    }
    headers = {"content-type": "application/json; charset=UTF-8"}

    response = requests.post(f"https://www.youtube.com/youtubei/v1/player?key={HARDCODED_API_KEY}",
                             json=request_data, headers=headers)

    if response.status_code == 400:
        return

    video_data = json.loads(response.content)
    video_details = video_data["videoDetails"]

    # For now the only information we need is the title.
    return {
        "title": video_details["title"]
    }
