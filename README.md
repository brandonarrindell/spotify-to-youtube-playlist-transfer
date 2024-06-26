# Spotify to YouTube Playlist Transfer

This application allows you to transfer your Spotify playlists to YouTube Music. It uses the Spotify API and YouTube Music API to fetch and transfer playlists.

## Features

- Authenticate with Spotify and YouTube Music.
- Select multiple Spotify playlists to transfer.
- Transfer playlists with progress updates.
- Handles existing playlists and tracks on YouTube Music.

## Requirements

- Python 3.6+
- PyQt6
- spotipy
- ytmusicapi

## Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/yourusername/spotify-to-ytmusic.git
    cd spotify-to-ytmusic
    ```

2. Install the required packages:
    ```sh
    pip install -r requirements.txt
    ```

3. Create a `config.json` file in the root directory with your Spotify API credentials. See [spotipy docs](https://spotipy.readthedocs.io/en/latest/#getting-started) for more info.
    ```json
    {
        "SPOTIPY_CLIENT_ID": "your_spotify_client_id",
        "SPOTIPY_CLIENT_SECRET": "your_spotify_client_secret",
        "SPOTIPY_REDIRECT_URI": "your_spotify_redirect_uri",
        "SPOTIPY_SCOPE": "playlist-read-private"
    }
    ```

4. Obtain YouTube Music OAuth credentials by running `ytmusicapi oauth` and following the prompts. This will create an `oauth.json` file in the root directory.

## Usage

1. Run the application:
    ```sh
    python spotify_to_ytmusic.py
    ```

2. Authenticate with Spotify by clicking the "Authenticate Spotify" button.

3. Authenticate with YouTube Music by clicking the "Authenticate YouTube Music" button.

4. Select the Spotify playlists you want to transfer.

5. Click the "Transfer Playlists" button to start the transfer process.

6. Monitor the progress through the progress bar and status log.

## File Structure

- `spotify_to_ytmusic.py`: Main application file.
- `config.json`: Configuration file for Spotify API credentials.
- `oauth.json`: OAuth credentials for YouTube Music.

## License

This project is licensed under the MIT License.
