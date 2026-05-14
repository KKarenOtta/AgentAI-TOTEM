import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import timedelta
from flask import session
from dotenv import load_dotenv

load_dotenv()


def configure_security(app):
    app.secret_key = os.getenv("FLASK_SECRET_KEY")
    app.permanent_session_lifetime = timedelta(minutes=10)

    app.config["SESSION_COOKIE_SECURE"] = True
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Strict"

    admin_user = os.getenv("TOTEM_ADMIN_USER")
    admin_password = os.getenv("TOTEM_ADMIN_PASSWORD")

    if not app.secret_key:
        raise RuntimeError("FLASK_SECRET_KEY nao configurada no ambiente.")

    if not admin_user or not admin_password:
        raise RuntimeError("Credenciais administrativas nao configuradas no ambiente.")

    return app


def configure_logging():
    logger = logging.getLogger("totem")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        file_handler = RotatingFileHandler(
            "totem.log",
            maxBytes=1024 * 1024,
            backupCount=3
        )
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def is_admin_logged():
    return session.get("admin_logged") is True


def validate_login_input(username, password):
    username = (username or "").strip()
    password = password or ""

    if not username or not password:
        return False, "Preencha usuario e senha."

    if len(username) > 50 or len(password) > 100:
        return False, "Entrada invalida."

    return True, ""