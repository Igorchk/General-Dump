#!/usr/bin/env python3
"""Summarize downloaded Instagram Reel videos using the Gemini API."""

import argparse
import os
import random
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai

PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_DOWNLOADS_DIR = PROJECT_DIR / "downloads"
DEFAULT_MODEL = "gemini-2.5-flash"
POLL_INTERVAL_SECONDS = 2

SYSTEM_PROMPT = """\
You are analyzing a short-form video (e.g. an Instagram Reel). Watch and \
listen to the entire video, then respond in Markdown with EXACTLY these \
four sections, in this order:

## Overview
A 1-2 sentence high-level summary of what the video is about.

## Key Takeaways & Spoken Advice
A bulleted list of the core points made in the speech/audio/narration.

## On-Screen Content & Entities
Any exact URLs, handles (@username), app/tool names, or major text overlays \
that appear on screen. Quote them verbatim. Write "None detected" if there \
are none.

## Notable Visuals/Milestones
Key timestamps (e.g. 0:05, 0:12) and notable visual transitions, demos, or \
milestones shown in the video.
"""


def find_videos(downloads_dir: Path) -> list[Path]:
    return sorted(downloads_dir.glob("*.mp4"))


def summary_path_for(video_path: Path) -> Path:
    return video_path.with_name(f"{video_path.stem}_summary.md")


def wait_for_active(client: genai.Client, uploaded_file):
    file = uploaded_file
    while file.state.name == "PROCESSING":
        time.sleep(POLL_INTERVAL_SECONDS)
        file = client.files.get(name=file.name)
    if file.state.name != "ACTIVE":
        raise RuntimeError(f"Gemini file processing did not complete (state={file.state.name})")
    return file


def summarize_video(client: genai.Client, model: str, video_path: Path) -> str:
    uploaded = None
    try:
        uploaded = client.files.upload(file=str(video_path))
        uploaded = wait_for_active(client, uploaded)

        response = client.models.generate_content(
            model=model,
            contents=[uploaded, SYSTEM_PROMPT],
        )
        text = response.text
        if not text:
            feedback = getattr(response, "prompt_feedback", None)
            raise RuntimeError(f"Empty or blocked response from Gemini (prompt_feedback={feedback})")
        return text
    finally:
        if uploaded is not None:
            try:
                client.files.delete(name=uploaded.name)
            except Exception as cleanup_exc:
                print(
                    f"  (warning: failed to delete uploaded file {uploaded.name}: {cleanup_exc})",
                    file=sys.stderr,
                )


def main():
    load_dotenv(PROJECT_DIR / ".env")

    parser = argparse.ArgumentParser(
        description="Summarize downloaded Instagram Reel videos (.mp4) using the Gemini API."
    )
    parser.add_argument(
        "--downloads-dir", type=Path, default=DEFAULT_DOWNLOADS_DIR,
        help=f"Directory containing downloaded .mp4 files (default: {DEFAULT_DOWNLOADS_DIR})",
    )
    parser.add_argument(
        "--model", type=str, default=DEFAULT_MODEL,
        help=f"Gemini model to use (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-summarize videos even if a *_summary.md file already exists",
    )
    parser.add_argument(
        "--delay-min", type=float, default=2.0,
        help="Minimum delay in seconds between videos (default: 2.0)",
    )
    parser.add_argument(
        "--delay-max", type=float, default=3.0,
        help="Maximum delay in seconds between videos (default: 3.0)",
    )
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print(
            "Error: GEMINI_API_KEY is not set. Export it in your shell or put it in a "
            f".env file at {PROJECT_DIR / '.env'} (see HOW_TO_USE.md).",
            file=sys.stderr,
        )
        sys.exit(1)

    if not args.downloads_dir.exists():
        print(f"Error: downloads directory not found: {args.downloads_dir}", file=sys.stderr)
        sys.exit(1)

    videos = find_videos(args.downloads_dir)
    if not videos:
        print(f"No .mp4 files found in {args.downloads_dir}")
        sys.exit(0)

    client = genai.Client(api_key=api_key)

    succeeded, skipped, failed = 0, 0, []
    total = len(videos)

    for i, video_path in enumerate(videos, start=1):
        summary_path = summary_path_for(video_path)
        print(f"[{i}/{total}] Analyzing {video_path.name}...", end=" ", flush=True)

        if summary_path.exists() and not args.force:
            print("-> Skipped (summary already exists).")
            skipped += 1
            continue

        try:
            summary_text = summarize_video(client, args.model, video_path)
            summary_path.write_text(summary_text, encoding="utf-8")
            print(f"-> Saved summary ({summary_path.name}).")
            succeeded += 1
        except Exception as exc:
            print(f"-> FAILED: {exc}", file=sys.stderr)
            failed.append(video_path.name)

        if i < total:
            time.sleep(random.uniform(args.delay_min, args.delay_max))

    print("\n----- Summary -----")
    print(f"Total videos: {total}")
    print(f"Succeeded:    {succeeded}")
    print(f"Skipped:      {skipped}")
    print(f"Failed:       {len(failed)}")
    if failed:
        print("Failed videos:")
        for name in failed:
            print(f"  - {name}")


if __name__ == "__main__":
    main()
