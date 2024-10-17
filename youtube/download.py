import asyncio, yt_dlp, re

from config import logging_config
logging = logging_config.setup_logging(__name__)

class MyLogger:
    def __init__(self):
        self.last_percentage = None

    def debug(self, msg):
        match = re.search(r'(\d+\.\d+)%', msg)
        if match:
            percentage = match.group(1)
            if self.last_percentage != percentage:
                print(f"\rDownloading: {percentage}%", end='', flush=True)
                self.last_percentage = percentage
        else:
            logging.debug(msg)

    def info(self, msg):
        logging.info(msg)

    def warning(self, msg):
        logging.warning(msg)

    def error(self, msg):
        logging.error(msg)

async def get_video_info(url_id):
    url = f"https://www.youtube.com/watch?v={url_id}"
    logging.debug(url)
    ydl_opts = {
        'logger': MyLogger(),
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = await asyncio.to_thread(ydl.extract_info, url, download=False)
        name = info_dict.get('title', 'N/A')
        duration = info_dict.get('duration', 'N/A')
        duration_sec = duration if duration != 'N/A' else 0
        upload_date = info_dict.get('upload_date', 'N/A')
        author = info_dict.get('uploader', 'N/A')
        thumbnail = info_dict.get('thumbnail', None)
        
        formats = info_dict.get('formats', [])
        qualities = {}
        
        for f in formats:
            if f.get('vcodec') != 'none' and f.get('ext') == 'mp4':
                resolution = f.get('height', 'Unknown')
                filesize = f.get('filesize', None)
                
                if resolution != 'Unknown':
                    if resolution not in qualities:
                        qualities[resolution] = {'filesize': 0, 'size_str': 'Unknown size'}
                    
                    if filesize and (qualities[resolution]['filesize'] < filesize):
                        size_mb = filesize / (1024 * 1024)
                        size_str = f"{size_mb:.2f}Mb" if size_mb < 1024 else f"{size_mb / 1024:.2f}Gb"
                        qualities[resolution] = {'filesize': filesize, 'size_str': size_str}
        
        qualities_list = [f"{resolution}p - {data['size_str']}" for resolution, data in qualities.items()]
        if qualities_list == []:
            qualities_list = ["144p", "360p", "480p", "720p", "1080p"]
        
        if duration != 'N/A':
            if duration < 60:
                duration_str = f"{duration} seconds"
            elif duration < 3600:
                minutes, seconds = divmod(duration, 60)
                duration_str = f"{minutes} minutes {seconds} seconds"
            else:
                hours, remainder = divmod(duration, 3600)
                minutes, seconds = divmod(remainder, 60)
                duration_str = f"{hours} hours {minutes} minutes {seconds} seconds"
        else:
            duration_str = 'Unknown duration'
        
        video_info = {
            "name": name,
            "duration": duration_str,
            "duration_sec": duration_sec,
            "date": upload_date if upload_date != 'N/A' else 'Unknown date',
            "author": author if author != 'N/A' else 'Unknown author',
            "qualities": qualities_list,
            "thumbnail": thumbnail,
        }
        
        return video_info

async def download_video(url_id, quality, progress_hook, download_path):
    url = f"https://www.youtube.com/watch?v={url_id}"
    file_path = f'{download_path}/video-{url_id}-{quality}.mp4'

    ydl_opts = {
        'format': f'bestvideo[ext=mp4][height<={quality}]+bestaudio/best[height<={quality}]',
        'outtmpl': file_path,
        'extract_flat': 'discard_in_playlist',
        'fragment_retries': 10,
        'ignoreerrors': 'only_download',
        'retries': 10,
        'logger': MyLogger(),
        'progress_hooks': [progress_hook.hook],
        'merge_output_format': 'mp4',
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = await asyncio.to_thread(ydl.extract_info, url)
        await asyncio.to_thread(ydl.download, [url])

    return file_path

async def download_audio(url_id, progress_hook, download_path):
    url = f"https://www.youtube.com/watch?v={url_id}"
    file_path = f'{download_path}/audio-{url_id}.mp3'

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': file_path,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'logger': MyLogger(),
        'progress_hooks': [progress_hook.hook],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = await asyncio.to_thread(ydl.extract_info, url)
        await asyncio.to_thread(ydl.download, [url])

    return file_path

if __name__ == "__main__":
    raise RuntimeError("This module should be run only via main.py")

