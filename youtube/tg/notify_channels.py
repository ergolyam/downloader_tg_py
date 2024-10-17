import asyncio
from db.channel import get_all_channels
from youtube.scrap import main as scrap_video_url
from youtube.download import get_video_info
from youtube.tg.video import download_video_tg
from db.notify import get_last_sent_video, update_last_sent_video
from config import logging_config
logging = logging_config.setup_logging(__name__)

async def process_user_channels(app, download_path):
    for user_id, channel_urls in await get_all_channels():
        for channel_url in channel_urls:
            last_sent_video_id = await get_last_sent_video(user_id, channel_url)
            new_video_id = await scrap_video_url(channel_url)
            if new_video_id:
                if last_sent_video_id != new_video_id:
                    logging.debug(f"{user_id}: New video found on {channel_url}: {new_video_id}")
                    video_info = await get_video_info(new_video_id)
                    message_text = f"""
**Название**: {video_info['name']}
**Автор**: {video_info['author']}
**Дата выхода**: {video_info['date']}
**Продолжительность**: {video_info['duration']}
**Ссылка**: https://www.youtube.com/watch?v={new_video_id}
                    """
                    message = await app.send_photo(user_id, video_info['thumbnail'], caption=message_text)
                    await download_video_tg(app, new_video_id, '720', message, user_id, video_info['duration_sec'], download_path)
                    await update_last_sent_video(user_id, channel_url, new_video_id)
                else:
                    logging.debug(f"User {user_id} already received the latest video from {channel_url}.")
            else:
                logging.debug(f"No new video found for channel {channel_url}.")
        await asyncio.sleep(1)

if __name__ == "__main__":
    raise RuntimeError("This module should be run only via main.py")
