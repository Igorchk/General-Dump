#!/usr/bin/env python3
"""Batch-download Instagram Reels/Posts from a list of URLs using yt-dlp."""

import argparse
import random
import re
import sys
import time
from pathlib import Path

import yt_dlp

PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = PROJECT_DIR / "downloads"
DEFAULT_ARCHIVE_FILE = PROJECT_DIR / ".download_archive.txt"
DEFAULT_FAILED_FILE = PROJECT_DIR / "failed_urls.txt"

URL_PATTERN = re.compile(r"instagram\.com/(?:[^/]+/)?(p|reel|reels)/[A-Za-z0-9_-]+", re.IGNORECASE)

ALREADY_RECORDED_MARKER = "has already been recorded in the archive"

# Force standard H.264/AAC mp4 output so files play in QuickTime/Windows Media
# Player, which don't support the VP9/AV1 streams Instagram serves by default.
FORMAT_SELECTOR = "bestvideo[vcodec^=avc1]+bestaudio[acodec^=mp4a]/best[vcodec^=avc1]/best"
FORMAT_SORT = ["codec:h264:m4a", "res", "ext:mp4:m4a"]


class BufferingLogger:
    """Captures yt-dlp log lines so we can detect archive-skip messages."""

    def __init__(self):
        self.lines = []

    def debug(self, msg):
        self.lines.append(msg)

    def info(self, msg):
        self.lines.append(msg)

    def warning(self, msg):
        self.lines.append(msg)

    def error(self, msg):
        self.lines.append(msg)

    def was_skipped(self):
        return any(ALREADY_RECORDED_MARKER in line for line in self.lines)


def read_urls(input_file: Path) -> list[str]:
    urls = []
    with input_file.open("r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            urls.append(line)
    return urls


def validate_url(url: str) -> bool:
    return bool(URL_PATTERN.search(url))


def build_ydl_opts(output_dir: Path, archive_file: Path, cookies_from_browser: str | None,
                    cookies_file: str | None, logger: BufferingLogger,
                    force_redownload: bool = False) -> dict:
    opts = {
        "outtmpl": str(output_dir / "%(upload_date)s_%(id)s.%(ext)s"),
        "download_archive": str(archive_file),
        "format": FORMAT_SELECTOR,
        "format_sort": FORMAT_SORT,
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": False,
        "logger": logger,
        "noprogress": True,
        "ignoreerrors": False,
    }
    if cookies_from_browser:
        opts["cookiesfrombrowser"] = (cookies_from_browser,)
    if cookies_file:
        opts["cookiefile"] = cookies_file
    if force_redownload:
        # Also overwrite any existing local file with the same name, since a
        # cleared archive alone won't re-fetch a file that's already on disk.
        opts["overwrites"] = True
    return opts


def main():
    parser = argparse.ArgumentParser(
        description="Download Instagram Reels/Posts listed in a text file (one URL per line)."
    )
    parser.add_argument("input_file", type=Path, help="Path to a text file with Instagram URLs (one per line)")
    parser.add_argument(
        "--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR,
        help=f"Directory to save downloaded videos (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--failed-file", type=Path, default=DEFAULT_FAILED_FILE,
        help=f"Where to write URLs that failed to download (default: {DEFAULT_FAILED_FILE})",
    )
    parser.add_argument(
        "--archive-file", type=Path, default=DEFAULT_ARCHIVE_FILE,
        help=f"yt-dlp download-archive file used to skip already-downloaded videos (default: {DEFAULT_ARCHIVE_FILE})",
    )
    parser.add_argument(
        "--cookies-from-browser", type=str, default=None,
        help="Load cookies from an installed browser (e.g. chrome, firefox, safari, edge)",
    )
    parser.add_argument(
        "--cookies", type=str, default=None,
        help="Path to a Netscape-format cookies.txt file (alternative to --cookies-from-browser)",
    )
    parser.add_argument(
        "--delay-min", type=float, default=2.0,
        help="Minimum delay in seconds between downloads (default: 2.0)",
    )
    parser.add_argument(
        "--delay-max", type=float, default=4.0,
        help="Maximum delay in seconds between downloads (default: 4.0)",
    )
    parser.add_argument(
        "--force-redownload", action="store_true",
        help=(
            "Delete the existing download-archive file before starting, so every "
            "URL is re-downloaded even if already recorded as downloaded. Use this "
            "to fix files downloaded before the H.264/AAC format fix."
        ),
    )
    args = parser.parse_args()

    if not args.input_file.exists():
        print(f"Error: input file not found: {args.input_file}", file=sys.stderr)
        sys.exit(1)

    args.output_dir.mkdir(parents=True, exist_ok=True)

    if args.force_redownload and args.archive_file.exists():
        args.archive_file.unlink()
        print(f"Removed existing download archive: {args.archive_file} (forcing re-download of all URLs)")

    raw_urls = read_urls(args.input_file)
    urls = []
    for url in raw_urls:
        if validate_url(url):
            urls.append(url)
        else:
            print(f"Skipping invalid/unsupported URL: {url}")

    if not urls:
        print("No valid Instagram URLs found in the input file.")
        sys.exit(0)

    succeeded, skipped, failed = 0, 0, []

    for i, url in enumerate(urls):
        logger = BufferingLogger()
        ydl_opts = build_ydl_opts(
            args.output_dir, args.archive_file, args.cookies_from_browser, args.cookies, logger,
            force_redownload=args.force_redownload,
        )

        print(f"[{i + 1}/{len(urls)}] Processing {url}")
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            if logger.was_skipped():
                print("  -> already downloaded, skipped")
                skipped += 1
            else:
                print("  -> downloaded successfully")
                succeeded += 1
        except Exception as exc:
            print(f"  -> FAILED: {exc}", file=sys.stderr)
            failed.append(url)

        if i < len(urls) - 1:
            time.sleep(random.uniform(args.delay_min, args.delay_max))

    if failed:
        args.failed_file.parent.mkdir(parents=True, exist_ok=True)
        with args.failed_file.open("w", encoding="utf-8") as f:
            f.write("\n".join(failed) + "\n")

    print("\n----- Summary -----")
    print(f"Total processed: {len(urls)}")
    print(f"Succeeded:       {succeeded}")
    print(f"Skipped:         {skipped}")
    print(f"Failed:          {len(failed)}")
    if failed:
        print(f"Failed URLs written to: {args.failed_file}")


if __name__ == "__main__":
    main()
