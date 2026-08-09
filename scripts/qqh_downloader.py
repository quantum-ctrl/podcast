# -*- coding: utf-8 -*-
"""
QQH (跟宇宙结婚悄悄话) Podcast Audio Downloader
Downloads the latest audio from afdian.com and saves to audios/qqh/
"""

import requests
import os
import re
from urllib.parse import urlsplit, urlunsplit

# Download directory relative to project root (script is in scripts/ folder)
DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "audios", "qqh")
REQUEST_TIMEOUT = 30


def _as_non_empty_string(value):
    """Return a trimmed string value, or None for empty/non-string values."""
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return None


def extract_audio_url(post):
    """Extract an audio URL from both current and older Afdian response shapes."""
    if not isinstance(post, dict):
        return None

    # ``audio`` is the normal field.  The other two are used by some API
    # responses and by the media player/detail response.
    for field in ("audio", "audio_url", "play_url"):
        audio_url = _as_non_empty_string(post.get(field))
        if audio_url:
            return audio_url

    # Keep attachment handling deliberately strict: attachments can contain
    # images and documents, so only accept values explicitly marked as audio.
    attachments = post.get("attachment") or post.get("attachments") or []
    if isinstance(attachments, list):
        for attachment in attachments:
            if not isinstance(attachment, dict):
                continue
            attachment_type = " ".join(
                str(attachment.get(field, "")).lower()
                for field in ("type", "cate", "mime", "content_type", "file_type")
            )
            if "audio" not in attachment_type and not attachment.get("is_audio"):
                continue
            for field in ("play_url", "audio", "url", "download_url"):
                audio_url = _as_non_empty_string(attachment.get(field))
                if audio_url:
                    return audio_url

    return None


def _post_sort_key(post):
    """Sort newest posts first while tolerating missing/string sort fields."""
    def number(value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return -1

    return (
        number(post.get("rank")),
        number(post.get("publish_time")),
        number(post.get("publish_sn")),
    )


def _detail_api_url(api_url):
    parsed = urlsplit(api_url)
    return urlunsplit((parsed.scheme, parsed.netloc, "/api/post/get-detail", "", ""))


def get_post_detail(post, api_url, headers):
    """Fetch a post detail when the album list omits its media URL."""
    post_id = _as_non_empty_string(post.get("post_id"))
    if not post_id:
        return None

    album_id = ""
    album_ids = post.get("album_ids")
    if isinstance(album_ids, list) and album_ids:
        album_id = _as_non_empty_string(album_ids[0]) or ""

    params = {"post_id": post_id}
    if album_id:
        params["album_id"] = album_id

    try:
        response = requests.get(
            _detail_api_url(api_url),
            params=params,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        if response.status_code != 200:
            print(f"Warning: Failed to fetch post detail. Status code: {response.status_code}")
            return None
        data = response.json()
        return data.get("data", {}).get("post")
    except (requests.exceptions.RequestException, ValueError) as e:
        print(f"Warning: Could not fetch or parse post detail: {e}")
        return None


def sanitize_filename(filename):
    """
    Removes invalid characters from a string to make it a valid filename.
    Also, renames the file to the desired format: vol.XXX-RestOfTitle.mp3
    """
    # First, sanitize invalid characters
    sanitized = re.sub(r'[\\/*?:"<>|]', "", filename)

    # Attempt to reformat the filename
    match = re.search(r'.*?(vol\.\d+)\s*(.*)', sanitized, re.IGNORECASE)
    if match:
        vol_part = match.group(1)
        rest_of_title = match.group(2).strip()
        if rest_of_title:
            reformatted_filename = f"{vol_part}-{rest_of_title}"
        else:
            reformatted_filename = f"{vol_part}"
    else:
        reformatted_filename = sanitized

    # Limit filename length to avoid OS errors
    return (reformatted_filename[:200] + '...') if len(reformatted_filename) > 200 else reformatted_filename


def download_audio(url, headers, file_name="downloaded_audio.mp3"):
    """
    Downloads an audio file from a given URL with specified headers.
    Skips download if file already exists.

    Args:
        url (str): The URL of the audio file to download.
        headers (dict): The headers to include in the request.
        file_name (str): The name to save the downloaded file as.
    
    Returns:
        bool: True if downloaded or already exists, False on error.
    """
    # Ensure download directory exists
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    
    download_path = os.path.join(DOWNLOAD_DIR, file_name)
    
    # Skip if file already exists
    if os.path.exists(download_path):
        print(f"File already exists, skipping: {file_name}")
        return True
    
    print(f"Attempting to download audio from: {url}")
    try:
        response = requests.get(url, headers=headers, stream=True, timeout=REQUEST_TIMEOUT)

        if response.status_code == 200:
            block_size = 1024
            temporary_path = download_path + ".part"

            print(f"Downloading to: {download_path}")

            with open(temporary_path, 'wb') as f:
                for data in response.iter_content(block_size):
                    if data:
                        f.write(data)

            os.replace(temporary_path, download_path)

            print(f"\nDownload complete! File saved as {file_name}")
            
            file_size_mb = os.path.getsize(download_path) / (1024*1024)
            print(f"File size: {file_size_mb:.2f} MB")
            
            # Check if file size exceeds 90MB, if so compress it
            if file_size_mb > 90:
                print(f"File size ({file_size_mb:.2f} MB) exceeds 90MB limit. Compressing to 64kbps MP3...")
                temp_path = download_path + ".temp.mp3"
                import subprocess
                try:
                    subprocess.run(
                        ["ffmpeg", "-i", download_path, "-codec:a", "libmp3lame", "-b:a", "64k", "-y", temp_path],
                        check=True,
                        capture_output=True,
                        text=True
                    )
                    os.replace(temp_path, download_path)
                    new_size_mb = os.path.getsize(download_path) / (1024*1024)
                    print(f"Compression complete! New file size: {new_size_mb:.2f} MB")
                except subprocess.CalledProcessError as e:
                    print(f"Error: Failed to compress audio. ffmpeg error: {e.stderr}")
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    return False
                except FileNotFoundError:
                    print("Error: ffmpeg is not installed or not in PATH. Skipping compression.")
                    return False

            return True

        else:
            print(f"Error: Failed to download audio. Status code: {response.status_code}")
            print("Response content:", response.text)
            return False

    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return False
    finally:
        partial_path = download_path + ".part"
        if os.path.exists(partial_path):
            os.remove(partial_path)


def get_latest_audio_info(api_url, headers):
    """
    Fetches the newest playable post from the API and returns its audio URL/title.

    Afdian may return a post with ``has_audio=1`` but an empty ``audio`` field
    when the request is not authenticated. It may also omit the media URL from
    the album list while including it in the post detail response.
    """
    print(f"Fetching post list from: {api_url}")
    try:
        response = requests.get(api_url, headers=headers, timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            if data.get("ec") not in (None, 200):
                print(f"Error: Afdian API returned {data.get('ec')}: {data.get('em', '')}")
                return None, None

            post_list = data.get('data', {}).get('list', [])
            if post_list:
                print(f"Success: Found {len(post_list)} posts in the album.")

                # Do not depend on the API returning the newest post first.
                # Some album responses contain pinned/non-audio entries ahead
                # of the newest audio post.
                sorted_posts = sorted(post_list, key=_post_sort_key, reverse=True)
                for post in sorted_posts:
                    audio_url = extract_audio_url(post)

                    # The list endpoint can omit the URL even when the user is
                    # entitled to the post. Retry through the detail endpoint
                    # before moving on to an older post.
                    if not audio_url and post.get("has_audio"):
                        detail = get_post_detail(post, api_url, headers)
                        audio_url = extract_audio_url(detail)
                        if audio_url:
                            post = detail

                    title = _as_non_empty_string(post.get('title'))
                    if audio_url and title:
                        print(f"Found latest audio: '{title}'")
                        return audio_url, title

                latest_post = sorted_posts[0]
                if latest_post.get("has_audio"):
                    print(
                        "Error: Afdian reports audio on the latest post, but did not "
                        "return an audio URL. The QQH_AUTH_TOKEN may be expired, "
                        "invalid, or missing permissions."
                    )
                else:
                    print("Error: No playable audio was found in the returned posts.")
                print("Latest post:", latest_post.get("title", "untitled_audio"))
                return None, None
            else:
                print("Error: Post list is empty in the API response.")
                return None, None
        else:
            print(f"Error: Failed to fetch post list. Status code: {response.status_code}")
            print("Response content:", response.text)
            return None, None
    except (requests.exceptions.RequestException, ValueError, TypeError) as e:
        print(f"An error occurred while fetching or parsing the post list: {e}")
        return None, None


if __name__ == "__main__":
    # Get auth_token from environment variable
    auth_token = os.environ.get('QQH_AUTH_TOKEN', '').strip()
    if not auth_token:
        print("Warning: QQH_AUTH_TOKEN environment variable not set")
    
    # API URL to get the list of album posts
    list_api_url = "https://afdian.com/api/user/get-album-post?album_id=c6ae1166a9f511eab22c52540025c377&lastRank=&rankOrder=desc&rankField=rank"

    # Headers to mimic the browser request. Keep the auth cookie isolated from
    # stale analytics cookies; only the Afdian session cookie is needed here.
    request_headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7,de;q=0.6',
        'Afd-Fe-Version': '20250605',
        'Afd-Stat-Id': 'df74bff6561c11ef8e8f52540025c377',
        'Cache-Control': 'no-cache',
        'Locale-Lang': 'zh-CN',
        'Origin': 'https://afdian.com',
        'Pragma': 'no-cache',
        'Priority': 'u=1, i',
        'Referer': 'https://afdian.com/album/c6ae1166a9f511eab22c52540025c377',
        'Sec-Ch-Ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"macOS"',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'
    }
    if auth_token:
        request_headers['Cookie'] = f'auth_token={auth_token}'

    # Step 1: Get the URL and title of the latest audio
    audio_url, title = get_latest_audio_info(list_api_url, request_headers)

    # Step 2: If we got the info, download the audio
    if audio_url and title:
        file_name = sanitize_filename(title) + ".mp3"
        if not download_audio(audio_url, request_headers, file_name):
            raise SystemExit(1)
    else:
        # Do not let the workflow continue and report success while publishing
        # a feed that still points at the previous episode.
        raise SystemExit(1)
