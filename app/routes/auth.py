from __future__ import annotations

from html import escape

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from core.auth.service import authenticate
from core.auth.session_store import create_session, delete_session

router = APIRouter(tags=["auth"])


def _login_html(error: str | None = None) -> str:
    error_block = ""
    if error:
        error_block = f'<div class="error">{escape(error)}</div>'

    return f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <title>Login • AgentAI-TOTEM</title>
  <link rel="stylesheet" href="/static/css/app.css" />
  <style>
    body {{
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #0f172a;
    }}
    .login-card {{
      width: min(420px, 92vw);
      background: #ffffff;
      color: #111827;
      border-radius: 18px;
      padding: 28px;
      box-shadow: 0 20px 50px rgba(0,0,0,.25);
    }}
    .login-card h1 {{
      margin: 0 0 8px;
      font-size: 26px;
    }}
    .login-card p {{
      margin: 0 0 22px;
      color: #4b5563;
    }}
    .login-card label {{
      display: block;
      margin-top: 14px;
      font-weight: 700;
    }}
    .login-card input[type="text"],
    .login-card input[type="password"] {{
      width: 100%;
      box-sizing: border-box;
      margin-top: 6px;
      padding: 12px;
      border-radius: 10px;
      border: 1px solid #d1d5db;
    }}
    .lgpd {{
      display: flex;
      gap: 8px;
      align-items: flex-start;
      margin-top: 16px;
      font-weight: 400;
    }}
    .error {{
      background: #fee2e2;
      color: #991b1b;
      border: 1px solid #fecaca;
      padding: 10px;
      border-radius: 10px;
      margin-bottom: 14px;
      font-weight: 700;
    }}
    .login-btn {{
      width: 100%;
      margin-top: 20px;
      padding: 12px;
      border: 0;
      border-radius: 10px;
      background: #2563eb;
      color: white;
      font-weight: 800;
      cursor: pointer;
    }}
  </style>
</head>
<body>
  <main class="login-card">
    <h1>AgentAI-TOTEM</h1>
    <p>Acesso administrativo e empresarial.</p>

    {error_block}

    <form method="post" action="/login">
      <label>Usuário</label>
      <input name="username" type="text" autocomplete="username" required />

      <label>Senha</label>
      <input name="password" type="password" autocomplete="current-password" required />

      <label class="lgpd">
        <input type="checkbox" name="lgpd" required />
        <span>Aceito os termos LGPD e o uso dos dados para autenticação e auditoria de acesso.</span>
      </label>

      <button class="login-btn" type="submit">Entrar</button>
    </form>
  </main>
</body>
</html>
"""


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return HTMLResponse(_login_html())


@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    lgpd: str = Form("off"),
):
    if lgpd != "on":
        return HTMLResponse(_login_html("Aceite LGPD obrigatório."), status_code=400)

    user = authenticate(username.strip(), password)

    if not user:
        return HTMLResponse(_login_html("Credenciais inválidas."), status_code=401)

    session_id = create_session(user)

    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        samesite="lax",
    )

    return response


@router.get("/logout")
def logout(request: Request):
    session_id = request.cookies.get("session_id")

    if session_id:
        delete_session(session_id)

    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie("session_id")

    return response
