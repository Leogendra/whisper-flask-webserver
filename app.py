from werkzeug.utils import secure_filename
import imageio_ffmpeg as iio_ffmpeg
from flask import (
    Flask,
    request,
    render_template,
    send_from_directory,
)
import traceback
import requests
import whisper
import torch
import time
import json
import os

CUDA_AVAILABLE = torch.cuda.is_available()
DEVICE = "cuda" if CUDA_AVAILABLE else "cpu"
print(f"Whisper device: {DEVICE}, cuda_available: {CUDA_AVAILABLE}")


app = Flask(__name__)
MODEL_SIZES = ["tiny", "base", "small", "medium", "large"]
LANG_CODES = ["fr", "en"]
ALLOWED_EXT = {"mp3", "wav", "m4a", "flac", "ogg"}
UPLOAD_DIR = "audios"
RESULTS_DIR = "results"

_MODEL_INSTANCE = None
_MODEL_INSTANCE_SIZE = None
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_DIR
app.config["OUTPUT_FOLDER"] = RESULTS_DIR

# Setup ffmpeg binary from imageio-ffmpeg
try:
    ffmpeg_exe = iio_ffmpeg.get_ffmpeg_exe()
    ffmpeg_dir = os.path.dirname(ffmpeg_exe)
    os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
    app.config["FFMPEG_BINARY"] = ffmpeg_exe
    app.config["FFMPEG_EXISTS"] = os.path.exists(ffmpeg_exe)
    app.config["FFMPEG_EXECUTABLE"] = os.access(ffmpeg_exe, os.X_OK)
except Exception:
    app.config["FFMPEG_BINARY"] = None
    print("Warning: Could not set FFMPEG_BINARY. Ensure ffmpeg is installed and in PATH.")
    app.config["FFMPEG_EXISTS"] = False
    app.config["FFMPEG_EXECUTABLE"] = False




def get_model(size: str) -> whisper.Whisper:
    global _MODEL_INSTANCE, _MODEL_INSTANCE_SIZE

    # Reuse existing model if it's already loaded with the requested size
    if _MODEL_INSTANCE is not None and _MODEL_INSTANCE_SIZE == size:
        return _MODEL_INSTANCE

    load_kwargs = {"device": DEVICE}
    model = whisper.load_model(size, **load_kwargs)
    _MODEL_INSTANCE = model
    _MODEL_INSTANCE_SIZE = size

    return model


def transcribe_audio(audio_path: str, model_size: str = "small", lang: str = "fr") -> tuple[str, str]:
    model = get_model(model_size)
    start_time = time.time()

    # Ensure whisper uses the absolute ffmpeg binary provided by imageio-ffmpeg
    try:
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        ffmpeg_exe = None

    if ffmpeg_exe:
        try:
            import whisper.audio as _wa
            import subprocess as _sub

            def _run_with_abs_ffmpeg(cmd, *a, **kw):
                if isinstance(cmd, (list, tuple)):
                    cmd2 = [ffmpeg_exe if (isinstance(c, str) and c == "ffmpeg") else c for c in cmd]
                elif isinstance(cmd, str):
                    # Only replace the first occurrence at start to be safe
                    if cmd.startswith("ffmpeg"):
                        cmd2 = cmd.replace("ffmpeg", ffmpeg_exe, 1)
                    else:
                        cmd2 = cmd
                else:
                    cmd2 = cmd
                return _sub.run(cmd2, *a, **kw)

            # Monkeypatch whisper.audio.run to ensure absolute ffmpeg usage
            _wa.run = _run_with_abs_ffmpeg
        except Exception:
            pass

    # load and transcribe
    result = model.transcribe(audio_path, language=lang)
    transcription = result.get("text", "").strip()

    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    out_name = f"transcription_{timestamp}.json"
    output_path = os.path.join(RESULTS_DIR, out_name)

    file_name = os.path.basename(audio_path)
    try:
        audio_arr = whisper.load_audio(audio_path)
        duration_s = len(audio_arr) / 16000.0
    except Exception:
        duration_s = 0

    metadata = {
        "timestamp": timestamp,
        "audio_filename": file_name,
        "audio_duration_s": round(duration_s, 0),
        "model_size": model_size,
        "language": lang,
        "generation_time_s": round(time.time() - start_time, 1),
        "text": transcription,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    return transcription, out_name


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


@app.route("/")
def index():
    return render_template("index.html", model_sizes=MODEL_SIZES, langs=LANG_CODES)


@app.route("/transcribe", methods=["POST"])
def transcribe():
    try:
        model_size = request.form.get("model_size", "small")
        lang = request.form.get("lang", "fr")
        audio_url = request.form.get("audio_url", "").strip()

        print(f"Received transcription request:\n   model_size={model_size}\n   lang={lang}\n   audio_url={audio_url}")

        audio_file = (
            request.files.get("audio_file") if "audio_file" in request.files else None
        )

        # handle file upload or url
        if audio_url:
            resp = requests.get(audio_url, stream=True, timeout=30)
            resp.raise_for_status()
            url_name = (
                os.path.basename(audio_url.split("?")[0])
                or f"download_{int(time.time())}.mp3"
            )
            filename = secure_filename(url_name)
            if not allowed_file(filename):
                return (
                    render_template(
                        "result.html", error="Unsupported file format."
                    ),
                    400,
                )

            saved_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            with open(saved_path, "wb") as f:
                for chunk in resp.iter_content(8192):
                    f.write(chunk)
        elif audio_file and audio_file.filename:
            filename = secure_filename(audio_file.filename)
            if not allowed_file(filename):
                return (
                    render_template(
                        "result.html", error="Unsupported file format."
                    ),
                    400,
                )
            saved_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            audio_file.save(saved_path)
        else:
            return (
                render_template("result.html", error="No file or URL provided."),
                400,
            )

        transcription, out_name = transcribe_audio(
            saved_path, model_size=model_size, lang=lang
        )

        return render_template(
            "result.html",
            transcription=transcription,
            out_filename=out_name,
            model_size=model_size,
            lang=lang,
        )
    except Exception as e:
        tb = traceback.format_exc()
        debug_info = {
            "error": str(e),
            "traceback": tb,
            "cwd": os.getcwd(),
            "uid": getattr(os, 'getuid', lambda: None)(),
            "gid": getattr(os, 'getgid', lambda: None)(),
            "env_path": os.environ.get('PATH'),
        }

        return render_template(
            "result.html",
            error=str(e)
        ), 500


@app.route("/outputs/<path:filename>")
def outputs(filename):
    return send_from_directory(
        app.config["OUTPUT_FOLDER"], filename, as_attachment=True
    )




if __name__ == "__main__":
    print("Starting Flask server on http://127.0.0.1:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)