import sys
import json
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QListWidget, QLabel, QProgressBar, QTextEdit, 
                             QMessageBox, QSpinBox, QListWidgetItem)

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from ytmusicapi import YTMusic

class TransferThread(QThread):
    update_progress = pyqtSignal(int, str)
    transfer_complete = pyqtSignal(dict)

    def __init__(self, spotify, ytmusic, playlist_ids, batch_size):
        super().__init__()
        self.spotify = spotify
        self.ytmusic = ytmusic
        self.playlist_ids = playlist_ids
        self.batch_size = batch_size

    def run(self):
        total_results = {"total": 0, "added": 0, "skipped": 0, "not_found": 0}
        for i, playlist_id in enumerate(self.playlist_ids):
            self.update_progress.emit(0, f"Processing playlist {i+1} of {len(self.playlist_ids)}")
            tracks = self.get_spotify_tracks(playlist_id)
            yt_playlist_id, is_new_playlist = self.create_ytmusic_playlist(playlist_id)
            if yt_playlist_id:
                existing_tracks = set() if is_new_playlist else self.get_existing_tracks(yt_playlist_id)
                results = self.batch_process_tracks(yt_playlist_id, tracks, existing_tracks)
                for key in total_results:
                    total_results[key] += results[key]
            else:
                total_results["total"] += len(tracks)
                total_results["not_found"] += len(tracks)
        self.transfer_complete.emit(total_results)
        
    def get_spotify_tracks(self, playlist_id):
        tracks = []
        results = self.spotify.playlist_tracks(playlist_id)
        tracks.extend(results['items'])
        while results['next']:
            results = self.spotify.next(results)
            tracks.extend(results['items'])
        return tracks

    def create_ytmusic_playlist(self, playlist_id):
        playlist_info = self.spotify.playlist(playlist_id)
        name = playlist_info['name']
        description = playlist_info['description']
        
        # Check if a playlist with the same name already exists
        existing_playlists = self.ytmusic.get_library_playlists()
        for playlist in existing_playlists:
            if playlist['title'] == name:
                self.update_progress.emit(0, f"Playlist {name} already exists")
                return playlist['playlistId'], False
        
        # If not, create a new playlist
        try:
            self.update_progress.emit(0, f"Creating playlist {name}")
            return self.ytmusic.create_playlist(name, description), True
        except Exception as e:
            self.update_progress.emit(0, f"Error creating YouTube Music playlist: {e}")
            return None, False

    def get_existing_tracks(self, playlist_id):
        tracks = self.ytmusic.get_playlist(playlist_id, limit=None)['tracks']
        return set(track['videoId'] for track in tracks)

    def batch_process_tracks(self, yt_playlist_id, tracks, existing_tracks):
        new_tracks = []
        skipped_count = 0
        not_found_count = 0
        added_count = 0  # Initialize added count
        
        total_tracks = len(tracks)
        
        for i, track in enumerate(tracks):
            track_name = track['track']['name']
            artist_name = track['track']['artists'][0]['name']
            
            video_id = self.search_track(track)
            if video_id:
                if video_id not in existing_tracks:
                    new_tracks.append(video_id)
                    existing_tracks.add(video_id)
                    added_count += 1  # Increment added count
                    self.update_progress.emit(int((i+1) / total_tracks * 100), f"Added: {track_name} by {artist_name}")
                else:
                    skipped_count += 1
                    self.update_progress.emit(int((i+1) / total_tracks * 100), f"Skipped: {track_name} by {artist_name} (already in playlist)")
            else:
                not_found_count += 1
                self.update_progress.emit(int((i+1) / total_tracks * 100), f"Not found on YTMusic: {track_name} by {artist_name}")
            
            if len(new_tracks) == self.batch_size:
                self.add_tracks_to_playlist(yt_playlist_id, new_tracks)
                new_tracks = []
        
        if new_tracks:
            self.add_tracks_to_playlist(yt_playlist_id, new_tracks)
        
        return {
            "total": total_tracks,
            "added": added_count,  # Use added count
            "skipped": skipped_count,
            "not_found": not_found_count
        }

    def search_track(self, track):
        query = f"{track['track']['name']} {track['track']['artists'][0]['name']}"
        results = self.ytmusic.search(query, filter="songs")
        return results[0]['videoId'] if results else None

    def add_tracks_to_playlist(self, playlist_id, video_ids):
        try:
            self.ytmusic.add_playlist_items(playlist_id, video_ids)
        except Exception as e:
            print(f"Error adding tracks to playlist: {e}")

class SpotifyYouTubeMusicTransfer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Spotify to YouTube Music Transfer")
        self.setGeometry(100, 100, 800, 600)
        
        # Set the window icon
        # self.setWindowIcon(QIcon('path/to/your/icon.png'))
        
        self.spotify = None
        self.ytmusic = None
        self.playlists = []
        self.all_selected = False
        
        self.init_ui()
    
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        # Spotify authentication
        spotify_auth_button = QPushButton("Authenticate Spotify")
        spotify_auth_button.setStyleSheet("background-color: #1DB954; color: white;")  # Spotify green
        spotify_auth_button.clicked.connect(self.authenticate_spotify)
        layout.addWidget(spotify_auth_button)

        # YouTube Music authentication
        ytmusic_auth_button = QPushButton("Authenticate YouTube Music")
        ytmusic_auth_button.setStyleSheet("background-color: #FF0000; color: white;")  # YouTube red
        ytmusic_auth_button.clicked.connect(self.authenticate_ytmusic)
        layout.addWidget(ytmusic_auth_button)
        # Authentication status label
        self.auth_status_label = QLabel("Please authenticate both Spotify and YouTube Music")
        self.auth_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.auth_status_label)
        
        # Playlist selection
        self.playlist_list = QListWidget()
        self.playlist_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        layout.addWidget(QLabel("Select Spotify Playlists:"))
        layout.addWidget(self.playlist_list)
        
        # Select All button
        self.select_all_button = QPushButton("Select All")
        self.select_all_button.clicked.connect(self.toggle_select_all_playlists)
        layout.addWidget(self.select_all_button)
        
        # Batch size selection
        self.batch_size_spinbox = QSpinBox()
        self.batch_size_spinbox.setRange(1, 100)
        self.batch_size_spinbox.setValue(50)
        
        # Transfer button
        self.transfer_button = QPushButton("Transfer Playlists")
        self.transfer_button.clicked.connect(self.start_transfer)
        layout.addWidget(self.transfer_button)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        # Status log
        self.status_log = QTextEdit()
        self.status_log.setReadOnly(True)
        layout.addWidget(self.status_log)
        
        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close_application)
        layout.addWidget(close_button)
    
    def close_application(self):
        QApplication.quit()
    
    def authenticate_spotify(self):
        config = self.load_config()
        if not config:
            return
        
        try:
            self.spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(
                client_id=config['SPOTIPY_CLIENT_ID'],
                client_secret=config['SPOTIPY_CLIENT_SECRET'],
                redirect_uri=config['SPOTIPY_REDIRECT_URI'],
                scope=config['SPOTIPY_SCOPE']
            ))
            self.log("Spotify authenticated successfully")
            if self.ytmusic:
                self.auth_status_label.setText("Spotify and YouTube Music authenticated. Please select playlists to transfer.")
            else:
                self.auth_status_label.setText("Spotify authenticated. Please authenticate YouTube Music.")
            self.load_playlists()
        except Exception as e:
            self.show_error("Spotify Authentication Error", str(e))
    
    def authenticate_ytmusic(self):
        try:
            self.ytmusic = YTMusic('oauth.json')
            self.log("YouTube Music authenticated successfully")
            if self.spotify:
                self.auth_status_label.setText("YouTube Music and Spotify authenticated. Please select playlists to transfer.")
            else:
                self.auth_status_label.setText("YouTube Music authenticated. Please authenticate Spotify.")
        except FileNotFoundError:
            self.show_error("YouTube Music Authentication Error", "The oauth.json file was not found. Please ensure the file exists and try again.")
        except json.JSONDecodeError:
            self.show_error("YouTube Music Authentication Error", "The oauth.json file is not properly formatted. Please check the file and try again.")
        except Exception as e:
            self.show_error("YouTube Music Authentication Error", f"An unexpected error occurred: {str(e)}")
    
    def load_config(self):
        try:
            with open('config.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            self.show_error("Configuration Error", "config.json file not found")
        except json.JSONDecodeError:
            self.show_error("Configuration Error", "Invalid JSON in config.json")
        return None
    
    def load_playlists(self):
        if not self.spotify:
            self.show_error("Error", "Please authenticate Spotify first")
            return
        
        self.playlists = self.spotify.current_user_playlists()['items']
        self.playlist_list.clear()
        for playlist in self.playlists:
            item = QListWidgetItem(playlist['name'])
            item.setData(Qt.ItemDataRole.UserRole, playlist['id'])
            self.playlist_list.addItem(item)
    
    def toggle_select_all_playlists(self):
        self.all_selected = not self.all_selected
        for i in range(self.playlist_list.count()):
            item = self.playlist_list.item(i)
            item.setSelected(self.all_selected)
        
        if self.all_selected:
            self.select_all_button.setText("Deselect All")
        else:
            self.select_all_button.setText("Select All")
    
    def start_transfer(self):
        if not self.spotify or not self.ytmusic:
            self.show_error("Error", "Please authenticate both Spotify and YouTube Music")
            return
        
        selected_items = self.playlist_list.selectedItems()
        if not selected_items:
            self.show_error("Error", "Please select at least one playlist to transfer")
            return
        
        playlist_ids = [item.data(Qt.ItemDataRole.UserRole) for item in selected_items]
        
        self.transfer_thread = TransferThread(self.spotify, self.ytmusic, playlist_ids, self.batch_size_spinbox.value())
        self.transfer_thread.update_progress.connect(self.update_progress)
        self.transfer_thread.transfer_complete.connect(self.transfer_complete)
        self.transfer_thread.start()
        
        self.transfer_button.setEnabled(False)
    
    def update_progress(self, value, status):
        self.progress_bar.setValue(value)
        self.log(status)
    
    def transfer_complete(self, results):
        self.log(f"Transfer complete!")
        self.log(f"Total tracks: {results['total']}")
        self.log(f"Added: {results['added']}")
        self.log(f"Skipped: {results['skipped']}")
        self.log(f"Not found: {results['not_found']}")
        self.transfer_button.setEnabled(True)
    
    def log(self, message):
        self.status_log.append(message)
    
    def show_error(self, title, message):
        QMessageBox.critical(self, title, message)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SpotifyYouTubeMusicTransfer()
    window.show()
    sys.exit(app.exec())