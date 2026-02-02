# 🎬 AI Video Generator

Generate stunning AI videos from a single text prompt using HuggingFace models.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-red.svg)
![HuggingFace](https://img.shields.io/badge/🤗-HuggingFace-yellow.svg)

## Features

- 🎨 **Premium Dark UI** - Sleek glassmorphism design
- 🤖 **Multiple Models** - CogVideoX-5B & ModelScope T2V
- ⚙️ **Customizable** - Frames, quality, FPS settings
- 📚 **History Gallery** - Browse previous generations
- ⬇️ **Download** - Save videos as MP4

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

Open http://localhost:8501 in your browser.

## Models

| Model | VRAM | Quality | Speed |
|-------|------|---------|-------|
| ModelScope T2V | ~8GB | 256x256 | Fast |
| CogVideoX-5B | ~24GB | 720p | Slower |

## License

MIT License
