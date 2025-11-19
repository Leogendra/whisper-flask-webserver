# Whisper Flask Webserver

A small Flask web UI to run OpenAI Whisper transcriptions.

Features
- Upload audio file or provide a direct audio URL
- Choose language (EN/FR) and model size (tiny/base/small/medium/large)
- Password protection

Requirements
- Python 3.8+
- See `requirements.txt`

Quick setup
1. (Recommended) Create and activate a virtual environment:
```
python -m venv venv
venv\Scripts\Activate.ps1
```

2. Install dependencies:
```
pip install -r requirements.txt
```

3. Create a `.env` file at repository root with at least:
```
PASSWORD=your_site_password_here
```

4. Run the server:
```
python .\app.py
```

5. Open your browser at `http://127.0.0.1:5000`. You will be asked to log in with the password set in `.env`.

Usage
- On the homepage, either upload an audio file or paste a direct URL to an audio file.
- Choose language and model size, then click `Transcribe`.
- When transcription completes, you'll see the text in the browser and a download link for the JSON result file.

Output / JSON schema
- Results are saved to the `results/` directory with names like `transcription_YYYY-MM-DD_HH-MM-SS.json`.

Example JSON
```json
{
  "timestamp": "2025-11-19_14-30-12",
  "generation_time_s": 12.345,
  "model_size": "small",
  "language": "en",
  "text": "Slammed out the SVR..."
}
```