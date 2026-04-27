from flask import Flask, render_template, jsonify, request, redirect, url_for, session, flash
import threading
import time

from sensor_service import update_system_state, get_public_status, get_full_status, set_led_state
from security_service import (
    configure_security,
    configure_logging,
    is_admin_logged,
    validate_login_input,
    authenticate
)

app = Flask(__name__)
configure_security(app)
logger = configure_logging()


def monitor():
    while True:
        try:
            update_system_state()
        except Exception:
            pass
        time.sleep(1)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def status():
    return jsonify(get_public_status())


@app.route("/admin-data")
def admin_data():
    if not is_admin_logged():
        logger.warning(
            "Acesso negado | rota=/admin-data | ip=%s",
            request.remote_addr
        )
        return jsonify({"ok": False, "error": "nao autorizado"}), 403

    return jsonify(get_full_status())


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        valid, message = validate_login_input(username, password)
        if not valid:
            logger.warning(
                "Tentativa de login invalida | usuario=%s | ip=%s",
                username,
                request.remote_addr
            )
            flash(message)
            return render_template("login.html")

        if authenticate(username, password):
            session.permanent = True
            session["admin_logged"] = True
            session["admin_user"] = username

            logger.info(
                "Login administrativo realizado com sucesso | usuario=%s | ip=%s",
                username,
                request.remote_addr
            )
            return redirect(url_for("admin"))

        logger.warning(
            "Tentativa de login sem sucesso | usuario=%s | ip=%s",
            username,
            request.remote_addr
        )
        flash("Credenciais invalidas.")

    return render_template("login.html")


@app.route("/logout")
def logout():
    if session.get("admin_user"):
        logger.info(
            "Logout administrativo | usuario=%s | ip=%s",
            session.get("admin_user"),
            request.remote_addr
        )

    session.clear()
    return redirect(url_for("index"))


@app.route("/admin")
def admin():
    if not is_admin_logged():
        logger.warning(
            "Acesso negado | rota=/admin | ip=%s",
            request.remote_addr
        )
        return redirect(url_for("login"))

    return render_template("admin.html")


@app.route("/admin/led", methods=["POST"])
def admin_led():
    if not is_admin_logged():
        logger.warning(
            "Acesso negado | rota=/admin/led | ip=%s",
            request.remote_addr
        )
        return jsonify({"ok": False, "error": "nao autorizado"}), 403

    action = (request.form.get("action") or "").strip().lower()
    if action not in ("on", "off"):
        logger.warning(
            "Acao administrativa invalida | funcao=controle_led | usuario=%s | ip=%s | action=%s",
            session.get("admin_user"),
            request.remote_addr,
            action
        )
        return jsonify({"ok": False, "error": "acao invalida"}), 400

    led_state = set_led_state(action == "on")

    logger.info(
        "Funcao administrativa acionada | funcao=controle_led | acao=%s | usuario=%s | ip=%s | led=%s",
        action,
        session.get("admin_user"),
        request.remote_addr,
        led_state
    )

    return jsonify({"ok": True, "led": led_state})


if __name__ == "__main__":
    sensor_thread = threading.Thread(target=monitor, daemon=True)
    sensor_thread.start()
    app.run(host="0.0.0.0", port=5000, debug=False)