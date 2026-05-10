from flask import Flask, render_template, jsonify, request, redirect, url_for, session, flash
import os
import time
from datetime import timedelta
from dotenv import load_dotenv
import sensor_service
from werkzeug.security import generate_password_hash, check_password_hash
import db_service

load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv("FLASK_SECRET_KEY")
if not app.secret_key:
    raise RuntimeError("FLASK_SECRET_KEY nao configurada.")

use_https = os.getenv("USE_HTTPS", "false").lower() == "true"

app.config["SESSION_COOKIE_HTTPONLY"] = os.getenv("SESSION_COOKIE_HTTPONLY", "true").lower() == "true"
app.config["SESSION_COOKIE_SECURE"] = use_https and os.getenv("SESSION_COOKIE_SECURE", "true").lower() == "true"
app.config["SESSION_COOKIE_SAMESITE"] = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(
    minutes=int(os.getenv("ADMIN_SESSION_MINUTES", "20"))
)

db_service.init_db()

LOGIN_RATE_LIMIT = int(os.getenv("LOGIN_RATE_LIMIT", "5"))
LOGIN_RATE_WINDOW_SECONDS = int(os.getenv("LOGIN_RATE_WINDOW_SECONDS", "60"))
login_attempts = {}


def is_admin_logged():
    return session.get("admin_logged_in") is True


def validate_login_input(username, password):
    username = (username or "").strip()
    password = password or ""

    if not username or not password:
        return False, "Preencha usuario e senha."

    if len(username) > 50 or len(password) > 100:
        return False, "Entrada invalida."

    return True, ""


def authenticate(username, password):
    user = db_service.get_admin_user_by_username(username)

    if not user:
        return False

    password_hash = user["password_hash"]
    return check_password_hash(password_hash, password)


def login_required(view):
    from functools import wraps

    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not is_admin_logged():
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped_view


def get_client_ip():
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.remote_addr or "unknown"


def is_rate_limited(ip_address):
    now = time.time()
    attempts = login_attempts.get(ip_address, [])

    attempts = [ts for ts in attempts if now - ts < LOGIN_RATE_WINDOW_SECONDS]
    login_attempts[ip_address] = attempts

    return len(attempts) >= LOGIN_RATE_LIMIT


def register_login_attempt(ip_address):
    now = time.time()
    attempts = login_attempts.get(ip_address, [])
    attempts = [ts for ts in attempts if now - ts < LOGIN_RATE_WINDOW_SECONDS]
    attempts.append(now)
    login_attempts[ip_address] = attempts


def clear_login_attempts(ip_address):
    login_attempts.pop(ip_address, None)


@app.after_request
def apply_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

    if request.is_secure:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    if request.path in ["/login", "/admin"]:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"

    return response


@app.before_request
def force_https_redirect():
    force_https = os.getenv("FORCE_HTTPS_REDIRECT", "false").lower() == "true"
    forwarded_proto = request.headers.get("X-Forwarded-Proto", "http")

    if force_https and use_https and not request.is_secure and forwarded_proto != "https" and not app.debug:
        return redirect(request.url.replace("http://", "https://", 1), code=301)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def api_status():
    full = sensor_service.update_system_state()
    ultrassons = full.get("ultrassons", [])

    payload = {
        "totem_state": full.get("totem_state", "espera"),
        "message": full.get("message", "Aguardando visitante"),
        "temperature": full.get("temperature"),
        "humidity": full.get("humidity"),
        "distance_sensor_1_cm": ultrassons[0].get("distance_cm") if len(ultrassons) >= 1 else None,
        "distance_sensor_2_cm": ultrassons[1].get("distance_cm") if len(ultrassons) >= 2 else None,
        "distance_sensor_3_cm": ultrassons[2].get("distance_cm") if len(ultrassons) >= 3 else None,
        "led": full.get("led")
    }

    return jsonify(payload)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        ip_address = get_client_ip()

        if is_rate_limited(ip_address):
            flash("Muitas tentativas de login. Aguarde 1 minuto e tente novamente.")
            return render_template("login.html"), 429

        username = request.form.get("username")
        password = request.form.get("password")

        valid, message = validate_login_input(username, password)
        if not valid:
            register_login_attempt(ip_address)
            flash(message)
            return render_template("login.html"), 400

        if authenticate(username, password):
            clear_login_attempts(ip_address)
            session.clear()
            session.permanent = True
            session["admin_logged_in"] = True
            session["admin_user"] = username
            return redirect(url_for("admin"))

        register_login_attempt(ip_address)
        flash("Usuario ou senha invalidos.")
        return render_template("login.html"), 401

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/admin")
def admin():
    if not is_admin_logged():
        return redirect(url_for("login"))
    return render_template("admin.html")

@app.route("/admin/users/create", methods=["POST"])
def create_admin_user_route():
    if not is_admin_logged():
        return redirect(url_for("login"))

    username = (request.form.get("new_username") or "").strip()
    password = request.form.get("new_password") or ""

    if not username or not password:
        flash("Preencha usuario e senha do novo administrador.")
        return redirect(url_for("admin"))

    if len(username) > 50 or len(password) > 100:
        flash("Dados do novo usuario invalidos.")
        return redirect(url_for("admin"))

    password_hash = generate_password_hash(password)

    success, error_message = db_service.create_admin_user(username, password_hash)

    if not success:
        flash(error_message or "Nao foi possivel criar o usuario.")
        return redirect(url_for("admin"))

    flash("Novo usuario administrador criado com sucesso.")
    return redirect(url_for("admin"))

def get_ssl_context():
    if not use_https:
        return None

    cert_file = os.getenv("SSL_CERT")
    key_file = os.getenv("SSL_KEY")

    if not cert_file or not key_file:
        raise RuntimeError("SSL_CERT e SSL_KEY precisam estar definidos no .env quando USE_HTTPS=true.")

    if not os.path.exists(cert_file):
        raise RuntimeError(f"Certificado nao encontrado: {cert_file}")

    if not os.path.exists(key_file):
        raise RuntimeError(f"Chave SSL nao encontrada: {key_file}")

    return (cert_file, key_file)


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=False,
        ssl_context=get_ssl_context()
    )
