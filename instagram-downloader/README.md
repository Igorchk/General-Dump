# Instagram Reels Downloader

A small CLI tool that reads a text file of Instagram Reel/Post URLs and
downloads the videos locally using [`yt-dlp`](https://github.com/yt-dlp/yt-dlp).
Downloads are forced to standard H.264 (avc1) video + AAC audio in an mp4
container, so files play natively in QuickTime, Windows Media Player, etc.
(Instagram otherwise often serves VP9/AV1, which those players can't decode.)

## Setup

```bash
cd instagram-downloader
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

`ffmpeg` must also be installed and on your `PATH` — yt-dlp uses it to merge
separate video/audio streams and remux into a clean mp4 (e.g. `brew install
ffmpeg` on macOS, or `apt install ffmpeg` on Debian/Ubuntu).

## Usage

1. Create a text file with one Instagram Reel/Post URL per line (blank lines
   and lines starting with `#` are ignored). See [`reels.example.txt`](reels.example.txt).

2. Run the downloader:

   ```bash
   python download_reels.py reels.txt
   ```

3. Videos are saved to `downloads/` as `<upload_date>_<id>.mp4` by default.

### Authentication (cookies)

Instagram frequently requires a logged-in session to fetch video data. Supply
cookies one of two ways:

```bash
# Pull cookies directly from an installed, logged-in browser
python download_reels.py reels.txt --cookies-from-browser chrome

# Or point at a Netscape-format cookies.txt file
python download_reels.py reels.txt --cookies cookies.txt
```

Supported `--cookies-from-browser` values include `chrome`, `firefox`,
`safari`, `edge`, `brave`, `opera`, `vivaldi`, and `chromium`.

### Other options

| Flag | Default | Description |
|---|---|---|
| `--output-dir` | `downloads/` | Where videos are saved |
| `--failed-file` | `failed_urls.txt` | Where failed URLs are recorded |
| `--archive-file` | `.download_archive.txt` | yt-dlp archive used to skip already-downloaded videos on rerun |
| `--delay-min` / `--delay-max` | `2.0` / `4.0` | Random delay range (seconds) between downloads |
| `--force-redownload` | off | Delete the download archive and overwrite existing local files, forcing every URL to be re-fetched |

### Example

```bash
python download_reels.py reels.txt --cookies-from-browser chrome --delay-min 3 --delay-max 6
```

If you have old files downloaded before the H.264/AAC format fix (video-only,
no sound in QuickTime/Windows Media Player), re-run with `--force-redownload`
to wipe the archive and re-fetch everything in the correct format:

```bash
python download_reels.py reels.txt --cookies-from-browser chrome --force-redownload
```

## Behavior

- Invalid or unsupported lines (non-Instagram URLs) are skipped with a warning.
- Already-downloaded videos are tracked via a yt-dlp download archive
  (`.download_archive.txt`) and are skipped automatically on rerun.
- If a single URL fails (deleted post, private account, rate limit, etc.),
  the error is logged and the tool continues to the next URL.
- At the end of a run, a summary is printed (processed / succeeded / skipped
  / failed), and any failed URLs are written to `failed_urls.txt` for review
  or retry.

## Notes

- Downloaded videos, the download archive, and `failed_urls.txt` are
  git-ignored (see the repo root [`.gitignore`](../.gitignore)) — they are
  local artifacts, not something to commit.
- Respect Instagram's Terms of Service and only download content you have
  the right to use.
