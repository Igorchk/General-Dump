# How to Use

This project has two tools:

1. `download_reels.py` — downloads Instagram Reels/Posts from a list of URLs.
2. `summarize_reels.py` — uses the Gemini API to watch each downloaded video
   and write a structured Markdown summary next to it.

See [README.md](README.md) for full details on `download_reels.py`. This
guide focuses on `summarize_reels.py`.

## 1. Install dependencies

```bash
cd instagram-downloader
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Set your Gemini API key

Get a key from [Google AI Studio](https://aistudio.google.com/apikey), then
provide it one of two ways:

**Option A — environment variable (current shell session):**

```bash
export GEMINI_API_KEY="your_api_key_here"
```

**Option B — `.env` file (persists across sessions):**

```bash
cp .env.example .env
# then edit .env and replace the placeholder with your real key
```

`.env` is listed in the repo's root [`.gitignore`](../.gitignore), so it will
never be committed. Never paste your real key into `.env.example` or commit
it anywhere.

## 3. Run the summarizer

Make sure you've already downloaded some videos into `downloads/` with
`download_reels.py`, then run:

```bash
python summarize_reels.py
```

This scans `downloads/*.mp4`, and for each video not already summarized:
uploads it to the Gemini File API, waits for processing, asks
`gemini-2.5-flash` to analyze it, and saves the result as
`downloads/<video_name>_summary.md`.

### Options

| Flag | Default | Description |
|---|---|---|
| `--downloads-dir` | `downloads/` | Directory to scan for `.mp4` files |
| `--model` | `gemini-2.5-flash` | Gemini model to use |
| `--force` | off | Re-summarize videos even if a summary file already exists |
| `--delay-min` / `--delay-max` | `2.0` / `3.0` | Random delay range (seconds) between videos |

### Example

```bash
python summarize_reels.py --force --model gemini-2.5-flash
```

## Behavior

- Videos that already have a `<video_name>_summary.md` are skipped unless
  `--force` is passed.
- Each summary has four sections: **Overview**, **Key Takeaways & Spoken
  Advice**, **On-Screen Content & Entities**, and **Notable
  Visuals/Milestones**.
- Uploaded files are always deleted from Google's File API after processing
  (success or failure) so nothing lingers in your Gemini storage.
- If one video fails (rate limit, safety block, upload timeout, etc.), the
  error is printed and the tool moves on to the next video instead of
  crashing.
- A summary line at the end reports total / succeeded / skipped / failed
  counts, with failed filenames listed.
