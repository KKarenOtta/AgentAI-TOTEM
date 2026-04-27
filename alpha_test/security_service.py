import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import timedelta
from flask import session

ADMIN_USER = os.getenv("TOTEM_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("TOTEM_ADMIN_PASSWORD", "admin123")


def configure_security(app):
    app.config.from_prefixed_env()
    app.secret_key = app.config.get("SECRET_KEY") or os.getenv("FLASK_SECRET_KEY", "FLX001")
    app.permanent_session_lifetime = timedelta(minutes=10)
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


def authenticate(username, password):
    return username == ADMIN_USER and password == ADMIN_PASSWORD