# -*- coding: utf-8 -*-
"""
QQH (跟宇宙结婚悄悄话) Podcast Audio Downloader
Downloads the latest audio from afdian.com and saves to audios/qqh/
"""

import requests
import os
import re

# Download directory relative to project root (script is in scripts/ folder)
DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "audios", "qqh")


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
        response = requests.get(url, headers=headers, stream=True)

        if response.status_code == 200:
            total_size = int(response.headers.get('content-length', 0))
            block_size = 1024

            print(f"Downloading to: {download_path}")

            with open(download_path, 'wb') as f:
                for data in response.iter_content(block_size):
                    f.write(data)

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


def get_latest_audio_info(api_url, headers):
    """
    Fetches the list of posts from the API and returns the latest audio URL and title.
    """
    print(f"Fetching post list from: {api_url}")
    try:
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            post_list = data.get('data', {}).get('list', [])
            if post_list:
                print(f"Success: Found {len(post_list)} posts in the album.")
                latest_post = post_list[0]
                title = latest_post.get('title', 'untitled_audio')
                audio_url = latest_post.get('audio')

                if audio_url and title:
                    print(f"Found latest audio: '{title}'")
                    return audio_url, title
                else:
                    print("Error: Could not find 'audio' or 'title' field in the latest post.")
                    print("Latest post data:", latest_post)
                    return None, None
            else:
                print("Error: Post list is empty in the API response.")
                return None, None
        else:
            print(f"Error: Failed to fetch post list. Status code: {response.status_code}")
            print("Response content:", response.text)
            return None, None
    except (requests.exceptions.RequestException, ValueError) as e:
        print(f"An error occurred while fetching or parsing the post list: {e}")
        return None, None


if __name__ == "__main__":
    # Get auth_token from environment variable
    auth_token = os.environ.get('QQH_AUTH_TOKEN', '')
    if not auth_token:
        print("Warning: QQH_AUTH_TOKEN environment variable not set")
    
    # API URL to get the list of album posts
    list_api_url = "https://afdian.com/api/user/get-album-post?album_id=c6ae1166a9f511eab22c52540025c377&lastRank=&rankOrder=desc&rankField=rank"

    # Headers to mimic browser request
    request_headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7,de;q=0.6',
        'Afd-Fe-Version': '20250605',
        'Afd-Stat-Id': 'df74bff6561c11ef8e8f52540025c377',
        'Cache-Control': 'no-cache',
        'Cookie': f'_ga=GA1.1.1528726341.1723186748; auth_token={auth_token}; _ga_6STWKR7T9E=GS2.1.s1751639167$o56$g1$t1751639767$j59$l0$h1206931492; _ga_ZF21E9SBHP=GS2.1.s1751639167$o56$g1$t1751639767$j59$l0$h1763818580',
        'Locale-Lang': 'zh-CN',
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

    # Step 1: Get the URL and title of the latest audio
    audio_url, title = get_latest_audio_info(list_api_url, request_headers)

    # Step 2: If we got the info, download the audio
    if audio_url and title:
        file_name = sanitize_filename(title) + ".mp3"
        download_audio(audio_url, request_headers, file_name)