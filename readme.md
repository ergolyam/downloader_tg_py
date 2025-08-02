# downloader_tg_py
This project is a YouTube downloader bot for Telegram. It allows users to download videos or audio from YouTube, manage their subscribed channels, and receive notifications and downloads about new videos.

### Initial Setup

1. **Clone the repository**: Clone this repository using `git clone`.
2. **Create Virtual Env**: Create a Python Virtual Environment `venv` to download the required dependencies and libraries.
3. **Download Dependencies**: Download the required dependencies into the Virtual Environment `venv` using `uv`.

```shell
git clone https://github.com/ergolyam/downloader_tg_py.git
cd downloader_tg_py
python -m venv .venv
.venv/bin/python -m pip install uv
.venv/bin/python -m uv sync
```

## Usage

### Deploy

- Run the bot:
    ```bash
    TG_TOKEN="telegram_bot_token" .venv/bin/python bot
    ```

### Container

- Pull the container:
    ```bash
    podman pull ghcr.io/ergolyam/downloader_tg_py:latest
    ```

- Deploy using Podman:
    ```bash
    mkdir -p $HOME/database/ && \
    podman run --tmpfs /tmp \
    --name downloader_tg_py \
    -v $HOME/database/:/app/database/:z \
    -e TG_TOKEN="your_telegram_bot_token" \
    ghcr.io/ergolyam/downloader_tg_py:latest
    ```

## Environment Variables

The following environment variables control the startup of the project:

| Variable       | Values                              | Description                                                             |
| -------------- | ----------------------------------- | ----------------------------------------------------------------------- |
| `LOG_LEVEL`    | `DEBUG`, `INFO`, `WARNING`, `ERROR` | Logging verbosity                                                       |
| `TG_ID`        | *integer*                           | Telegram API ID from [my.telegram.org](https://my.telegram.org)         |
| `TG_HASH`      | *string*                            | Telegram API hash                                                       |
| `TG_TOKEN`     | *string*                            | Bot token issued by [@BotFather](https://t.me/BotFather)                |
| `DB_PATH`      | *string*                            | Path to SQLite database file (default `data.db`)                        |
| `COOKIE_PATH`  | *string*                            | Path to cookie storage file (default `cookie.txt`)                      |
| `HTTP_PROXY`   | *URL*                               | HTTP proxy in the form `http://user:password@host:port`                 |

## Features

- **Download Videos**:
  Users can download YouTube videos in various qualities.
- **Channel Subscription**:
  Users can subscribe to YouTube channels and receive notifications and downloads when new videos are uploaded.
- **SponsorBlock Integration**:
  Automatically reads sponsored segments in downloaded videos.
- **Customizable**:
  Configure log level, http proxy, and more through environment variables. Also configuration of notifications about new videos the user has.
