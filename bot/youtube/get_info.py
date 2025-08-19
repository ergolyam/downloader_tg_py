import asyncio
from typing import Any, Dict, Union, Mapping, Optional
from bot.core.helpers import Common
from bot.db.cache_qualitys import set_qualitys, get_qualitys
from bot.config.config import Config
from bot.config import logging_config
logging = logging_config.setup_logging(__name__)


def _estimate_bytes_from_info(info: Optional[Mapping[str, Any]]) -> int:
    if not info:
        return 0
    if 'requested_formats' in info and info['requested_formats']:
        s = 0
        for f in info['requested_formats']:
            s += int(f.get('filesize') or f.get('filesize_approx') or 0)
        if s > 0:
            return s
    if 'requested_downloads' in info and info['requested_downloads']:
        s = 0
        for f in info['requested_downloads']:
            s += int(f.get('filesize') or f.get('filesize_approx') or 0)
        if s > 0:
            return s
    return int(info.get('filesize') or info.get('filesize_approx') or 0)


def _estimate_bytes_from_format(fmt: dict, duration: Union[int, None]) -> int:
    size = fmt.get('filesize') or fmt.get('filesize_approx')
    if size:
        return int(size)
    if duration:
        kbps = fmt.get('vbr') or fmt.get('abr') or fmt.get('tbr')
        if kbps:
            return int((kbps * 1000 / 8) * duration)
    return 0


async def get_video_metainfo(url: str) -> dict:
    output = await get_qualitys(url)
    if output:
        logging.debug("Use video metainfo from cache")
        return output

    loop = asyncio.get_event_loop()

    def _get_video_metainfo_sync(_url: str) -> dict:
        base_opts: Dict[str, Any] = {
            'quiet': True,
            'noplaylist': True,
        }
        if Config.http_proxy:
            base_opts['proxy'] = Config.http_proxy
            logging.debug("Use http proxy")
        if Config.cookie_path:
            base_opts['cookiefile'] = Config.cookie_path
            logging.debug("Use cookie file")

        with Common.youtube(base_opts) as ydl:
            try:
                info = ydl.extract_info(_url, download=False)
            except Exception as e:
                logging.error(f'Extract video error: {e}')
                return {}

        if not info or "formats" not in info:
            return {}

        duration = info.get('duration') or 0

        all_heights = sorted({
            f['height']
            for f in info['formats']
            if f.get('height') and f.get('vcodec') not in (None, 'none')
        })

        audio_formats = [
            f for f in info['formats']
            if f.get('acodec') not in (None, 'none') and f.get('vcodec') in (None, 'none')
        ]

        def best_audio_for(container_pref: str) -> Union[dict, None]:
            preferred = [f for f in audio_formats if f.get('ext') == container_pref]
            pool = preferred if preferred else audio_formats
            if not pool:
                return None
            return max(pool, key=lambda x: (x.get('abr') or x.get('tbr') or 0))

        result: Dict[int, float] = {}

        native_mp4_available = any(
            f.get('ext') == 'mp4' for f in info.get('formats', [])
        )

        for quality in all_heights:
            videos_video_only = [
                f for f in info['formats']
                if f.get('height') == quality
                and f.get('vcodec') not in (None, 'none')
                and f.get('acodec') in (None, 'none')
            ]
            progressive = [
                f for f in info['formats']
                if f.get('height') == quality
                and f.get('vcodec') not in (None, 'none')
                and f.get('acodec') not in (None, 'none')
            ]

            if videos_video_only:
                best_video = max(videos_video_only, key=lambda x: (x.get('tbr') or x.get('vbr') or 0))
                video_ext = best_video.get('ext') or ''
                if video_ext == 'mp4':
                    best_audio = best_audio_for('m4a') or best_audio_for('mp4')
                elif video_ext == 'webm':
                    best_audio = best_audio_for('webm')
                else:
                    best_audio = best_audio_for('m4a') or best_audio_for('webm')

                if best_audio:
                    if native_mp4_available:
                        fmt_selector = f"bestvideo[ext=mp4][height={quality}]+bestaudio[ext=m4a]/mp4"
                    else:
                        fmt_selector = f"bestvideo[height={quality}]+bestaudio/best"
                else:
                    if native_mp4_available:
                        fmt_selector = f"bestvideo[ext=mp4][height={quality}]/mp4"
                    else:
                        fmt_selector = f"bestvideo[height={quality}]"

                sel_opts = dict(base_opts)
                sel_opts['format'] = fmt_selector
                sel_opts['simulate'] = True

                with Common.youtube(sel_opts) as y2:
                    try:
                        selected = y2.extract_info(_url, download=False)
                    except Exception:
                        selected = {}

                total_bytes = _estimate_bytes_from_info(selected)
                if total_bytes <= 0:
                    video_bytes = _estimate_bytes_from_format(best_video, duration)
                    audio_bytes = _estimate_bytes_from_format(best_audio, duration) if best_audio else 0
                    total_bytes = video_bytes + audio_bytes
            elif progressive:
                best_prog = max(progressive, key=lambda x: (x.get('tbr') or x.get('vbr') or 0))
                fmt_selector = f"best[height={quality}]"
                sel_opts = dict(base_opts)
                sel_opts['format'] = fmt_selector
                sel_opts['simulate'] = True

                with Common.youtube(sel_opts) as y2:
                    try:
                        selected = y2.extract_info(_url, download=False)
                    except Exception:
                        selected = {}

                total_bytes = _estimate_bytes_from_info(selected)
                if total_bytes <= 0:
                    total_bytes = _estimate_bytes_from_format(best_prog, duration)
            else:
                continue

            if total_bytes <= 0:
                continue

            result[quality] = round(total_bytes / (1024 * 1024), 2)

        mp3_kbps = 192
        if duration and duration > 0:
            mp3_bytes = int((mp3_kbps * 1000 / 8) * duration)
            result[2] = round(mp3_bytes / (1024 * 1024), 2)
        else:
            if audio_formats:
                best_audio_overall = max(audio_formats, key=lambda x: (x.get('abr') or x.get('tbr') or 0))
                audio_size_bytes = _estimate_bytes_from_format(best_audio_overall, duration)
                if audio_size_bytes > 0:
                    result[2] = round(audio_size_bytes / (1024 * 1024), 2)

        return result

    output = await loop.run_in_executor(None, _get_video_metainfo_sync, url)
    await set_qualitys(url, output)
    return output


async def get_video_info(url: str) -> Dict[str, Union[str, int, None]]:
    loop = asyncio.get_event_loop()

    def _get_video_info_sync(_url: str):
        ydl_opts: Dict[str, Any] = {
            'quiet': True,
            'noplaylist': True,
        }
        if Config.http_proxy:
            ydl_opts['proxy'] = Config.http_proxy
            logging.debug("Use http proxy")
        if Config.cookie_path:
            ydl_opts['cookiefile'] = Config.cookie_path
            logging.debug("Use cookie file")

        with Common.youtube(ydl_opts) as ydl:
            info = ydl.extract_info(_url, download=False)
        if not info:
            logging.error(f"Failed to retrieve channel information from the link: {_url}")
            return {}
        name = info.get('title', 'N/A')
        duration = info.get('duration', 'N/A')
        duration_sec = duration if duration != 'N/A' else 0
        upload_date = info.get('upload_date', 'N/A')
        author = info.get('uploader', 'N/A')

        thumbnail = None
        raw_thumb = info.get("thumbnail")
        if raw_thumb:
            fixed = raw_thumb.replace("/vi_webp/", "/vi/")
            if fixed.lower().endswith(".webp"):
                fixed = fixed[:-5] + ".jpg"
            thumbnail = fixed

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
            "thumbnail": thumbnail,
        }
        return video_info

    output = await loop.run_in_executor(None, _get_video_info_sync, url)

    return output


if __name__ == "__main__":
    raise RuntimeError("This module should be run only via main.py")
