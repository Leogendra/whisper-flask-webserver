from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from functools import wraps
from flask import (
    Flask,
    request,
    render_template,
    send_from_directory,
    redirect,
    url_for,
    session,
    flash,
)
import requests
import whisper
import time
import os


load_dotenv()
SITE_PASSWORD = os.getenv("PASSWORD")

app = Flask(__name__)
MODEL_SIZES = ["tiny", "base", "small", "medium", "large"]
LANG_CODES = ["fr", "en"]
ALLOWED_EXT = {"mp3", "wav", "m4a", "flac", "ogg"}
UPLOAD_DIR = "audios"
RESULTS_DIR = "results"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_DIR
app.config["OUTPUT_FOLDER"] = RESULTS_DIR
app.secret_key = SITE_PASSWORD

_MODEL_CACHE = {}




def get_model(size: str) -> whisper.Whisper:
    size = size if size in MODEL_SIZES else "small"
    if size in _MODEL_CACHE:
        return _MODEL_CACHE[size]

    model = whisper.load_model(size)
    _MODEL_CACHE[size] = model
    return model


def transcribe_audio(audio_path: str, model_size: str = "small", lang: str = "fr"):
    model = get_model(model_size)

    result = model.transcribe(audio_path, language=lang)
    transcription = result.get("text", "")

    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    out_name = f"transcription_{timestamp}.txt"
    output_path = os.path.join(RESULTS_DIR, out_name)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(transcription)

    return transcription, out_name


def require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get("authed"):
            return f(*args, **kwargs)
        return redirect(url_for("login", next=request.path))

    return wrapper




@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        pwd = request.form.get("password", "")
        if (SITE_PASSWORD and pwd == SITE_PASSWORD):
            session["authed"] = True
            next_url = request.args.get("next") or url_for("index")
            time.sleep(1)
            return redirect(next_url)
        time.sleep(3)
        flash("Mot de passe incorrect.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("authed", None)
    return redirect(url_for("login"))


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


@app.route("/")
@require_auth
def index():
    return render_template("index.html", model_sizes=MODEL_SIZES, langs=LANG_CODES)


@app.route("/transcribe", methods=["POST"])
@require_auth
def transcribe():
    model_size = request.form.get("model_size", "small")
    lang = request.form.get("lang", "fr")
    audio_url = request.form.get("audio_url", "").strip()

    print(f"Received transcription request: model_size={model_size}, lang={lang}, audio_url={audio_url}")

    audio_file = (
        request.files.get("audio_file") if "audio_file" in request.files else None
    )

    try:
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
                        "result.html", error="Format de fichier non supporté."
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
                        "result.html", error="Format de fichier non supporte."
                    ),
                    400,
                )
            saved_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            audio_file.save(saved_path)
        else:
            return (
                render_template("result.html", error="Aucun fichier ou URL fournis."),
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
        return render_template("result.html", error=str(e)), 500


@app.route("/outputs/<path:filename>")
@require_auth
def outputs(filename):
    return send_from_directory(
        app.config["OUTPUT_FOLDER"], filename, as_attachment=True
    )




if __name__ == "__main__":
    print("Starting Flask server on http://127.0.0.1:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)