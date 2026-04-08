# Top 10 YouTube Video Generator

Automatically generates fully produced "Top 10" countdown YouTube videos from a single topic prompt. The pipeline researches the topic, writes a narrated script, generates AI voiceover, assembles visuals, and outputs a ready-to-upload `final_video.mp4`.

## How It Works

```
Topic → Research → Script → Voice → Assemble → final_video.mp4
```

| Stage | What happens |
|-------|-------------|
| **Research** | Tavily searches the web; Claude ranks and structures 10 items (title, facts, hook line per item) |
| **Script** | Claude writes a timed narration script — intro, 10 segments, outro |
| **Voice** | ElevenLabs converts each segment to MP3 with timestamps |
| **Assemble** | Replicate (Flux) generates visuals; MoviePy composites audio + video + captions + background music |

The pipeline uses a JSON checkpoint (`output/<slug>/pipeline_state.json`) so a crash mid-run resumes from the last completed stage automatically.

## Prerequisites

- Python 3.11+
- `ffmpeg` installed and on your `$PATH`

### API Keys

Copy `.env.example` to `.env` and fill in:

```
ANTHROPIC_API_KEY=...    # Claude — research + scripting
TAVILY_API_KEY=...       # Web search
ELEVENLABS_API_KEY=...   # AI voiceover
REPLICATE_API_TOKEN=...  # Image generation (Flux Schnell)
```

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Basic
python run.py --topic "Top 10 Dangerous Animals"

# Custom output directory
python run.py --topic "Top 10 Fastest Cars" --output-dir ./my_output

# Restart from scratch (ignore checkpoint)
python run.py --topic "Top 10 Deepest Oceans" --no-resume

# Verbose / debug logging
python run.py --topic "Top 10 Ancient Wonders" -v
```

### Output

All artifacts are written to `output/<slugified-topic>/`:

```
output/top_10_dangerous_animals/
├── pipeline_state.json     # Checkpoint (resume state)
├── narration.mp3           # Full narration audio
├── segment_timestamps.json # Per-segment timing
├── segments/               # Individual segment MP3s
│   ├── segment_00.mp3
│   └── ...
└── final_video.mp4         # Ready-to-upload video
```

## Configuration

Edit `config.yaml` to tune the pipeline without touching code:

```yaml
research:
  item_count: 10              # Number of ranked items
  tavily_search_depth: advanced

script:
  words_per_segment: 40       # ~40 words ≈ 20 seconds narration
  model: claude-3-5-sonnet-20241022

voice:
  voice_id: "21m00Tcm4TlvDq8ikWAM"  # ElevenLabs voice ("Rachel")
  stability: 0.5
  similarity_boost: 0.75

visuals:
  replicate_model: "black-forest-labs/flux-schnell"
  width: 1280
  height: 720

music:
  search_query: "epic cinematic background"
  narration_volume: 1.0
  music_volume: 0.15         # Background music at 15%

video:
  fps: 24
  codec: libx264
```

## Project Structure

```
Top10Youtube/
├── run.py            # CLI entry point
├── pipeline.py       # Orchestrator + checkpoint state machine
├── config.yaml       # All tuneable settings
├── requirements.txt
└── modules/
    ├── research.py   # Tavily search + Claude ranking
    ├── script.py     # Claude script writer
    ├── voice.py      # ElevenLabs TTS + timestamps
    └── assembler.py  # MoviePy video assembly
```

## Resuming a Crashed Run

If the pipeline crashes mid-run, just re-run the same command. It reads `pipeline_state.json` and picks up from the last completed stage. To force a full restart, pass `--no-resume`.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `ffmpeg not found` | Install ffmpeg: `brew install ffmpeg` (macOS) or `apt install ffmpeg` |
| `ANTHROPIC_API_KEY not set` | Add it to your `.env` file |
| Pipeline stuck at VOICING | Check your ElevenLabs quota / voice ID in `config.yaml` |
| Blank images in video | Replicate `max_retries` in `config.yaml` controls retry count |
