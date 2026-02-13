# Music Files

Place your background music files here (MP3, WAV, or other audio formats supported by moviepy).

## Example Usage

```bash
# Generate a reel with background music
python main.py generate --theme 06_digestive_health --type reel --combined --music assets/00_music/your_music.mp3

# Generate a regular reel with music
python main.py generate --theme 05_kombucha_benefits --type reel --music assets/00_music/your_music.mp3
```

## Music Features

- Music will automatically loop if shorter than the video duration
- Music volume is set to 30% to not overpower the video audio
- Supported formats: MP3, WAV, M4A, and other formats supported by moviepy
