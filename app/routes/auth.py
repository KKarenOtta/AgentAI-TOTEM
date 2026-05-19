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
        error_block = f"""
        <div class="login-alert">
          <p>{escape(error)}</p>
        </div>
        """

    return f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Login administrativo</title>
  <link rel="stylesheet" href="/static/css/app.css" />
  <style>
    body.login-body {{
      min-height: 100vh;
      margin: 0;
      background:
        radial-gradient(circle at top, rgba(56, 189, 248, 0.16), transparent 30%),
        linear-gradient(180deg, #08111f 0%, #0f172a 45%, #111827 100%);
      color: #e5eefb;
      font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}

    .login-page {{
      min-height: 100vh;
      display: grid;
      place-items: center;
      padding: 24px;
      box-sizing: border-box;
    }}

    .login-screen {{
      width: 100%;
      max-width: 1120px;
      display: grid;
      grid-template-columns: minmax(280px, 420px) minmax(320px, 520px);
      align-items: center;
      justify-content: center;
      gap: 48px;
    }}

    .login-pulse-wrap {{
      position: relative;
      width: min(38vw, 340px);
      aspect-ratio: 1;
      margin: 0 auto;
      display: grid;
      place-items: center;
    }}

    .login-pulse-ring,
    .login-pulse-core {{
      position: absolute;
      border-radius: 50%;
    }}

    .login-pulse-ring {{
      inset: 0;
      border: 1px solid rgba(125, 211, 252, 0.22);
      box-shadow: 0 0 80px rgba(14, 165, 233, 0.12);
      animation: loginPulse 3.8s ease-in-out infinite;
    }}

    .login-pulse-ring.ring-2 {{
      inset: 12%;
      animation-delay: .6s;
    }}

    .login-pulse-core {{
      width: 34%;
      aspect-ratio: 1;
      background:
        radial-gradient(circle at 30% 30%, #7dd3fc, #0ea5e9 45%, #0f172a 100%);
      box-shadow:
        0 0 0 18px rgba(14, 165, 233, 0.08),
        0 0 60px rgba(14, 165, 233, 0.45);
    }}

    .login-card {{
      position: relative;
      background: rgba(15, 23, 42, 0.72);
      border: 1px solid rgba(148, 163, 184, 0.18);
      border-radius: 28px;
      padding: 32px;
      backdrop-filter: blur(18px);
      box-shadow: 0 28px 80px rgba(2, 8, 23, 0.45);
    }}

    .login-eyebrow {{
      margin: 0 0 10px;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: .24em;
      text-transform: uppercase;
      color: #38bdf8;
    }}

    .login-title {{
      margin: 0;
      font-size: clamp(2rem, 4vw, 3.2rem);
      line-height: 1.05;
      color: #f8fafc;
    }}

    .login-subtitle {{
      margin: 14px 0 24px;
      color: #cbd5e1;
      font-size: 1rem;
      line-height: 1.65;
    }}

    .login-alert {{
      margin-bottom: 18px;
      border: 1px solid rgba(248, 113, 113, 0.4);
      background: rgba(127, 29, 29, 0.28);
      color: #fecaca;
      border-radius: 14px;
      padding: 12px 14px;
    }}

    .login-alert p {{
      margin: 0;
    }}

    .login-form {{
      display: grid;
      gap: 16px;
    }}

    .login-field {{
      display: grid;
      gap: 8px;
    }}

    .login-field label {{
      font-size: .92rem;
      font-weight: 600;
      color: #dbeafe;
    }}

    .login-field input {{
      width: 100%;
      padding: 14px 16px;
      border-radius: 14px;
      border: 1px solid rgba(148, 163, 184, 0.26);
      background: rgba(15, 23, 42, 0.75);
      color: #f8fafc;
      outline: none;
      transition: border-color .2s ease, box-shadow .2s ease, transform .2s ease;
      box-sizing: border-box;
    }}

    .login-field input::placeholder {{
      color: #94a3b8;
    }}

    .login-field input:focus {{
      border-color: rgba(56, 189, 248, 0.75);
      box-shadow: 0 0 0 4px rgba(14, 165, 233, 0.14);
      transform: translateY(-1px);
    }}

    .login-check {{
      display: flex;
      align-items: flex-start;
      gap: 10px;
      margin-top: 4px;
      color: #cbd5e1;
      font-size: .92rem;
      line-height: 1.5;
    }}

    .login-check input {{
      margin-top: 4px;
      accent-color: #0ea5e9;
    }}

    .login-button {{
      margin-top: 4px;
      width: 100%;
      border: 0;
      border-radius: 16px;
      padding: 14px 18px;
      font-size: 1rem;
      font-weight: 700;
      color: #eff6ff;
      background: linear-gradient(135deg, #0ea5e9, #2563eb);
      box-shadow: 0 20px 40px rgba(37, 99, 235, 0.28);
      cursor: pointer;
      transition: transform .2s ease, box-shadow .2s ease, filter .2s ease;
    }}

    .login-button:hover {{
      transform: translateY(-1px);
      filter: brightness(1.04);
      box-shadow: 0 24px 44px rgba(37, 99, 235, 0.34);
    }}

    .login-back {{
      display: inline-flex;
      margin-top: 18px;
      color: #7dd3fc;
      text-decoration: none;
      font-weight: 600;
    }}

    .login-back:hover {{
      color: #bae6fd;
    }}

    @keyframes loginPulse {{
      0%, 100% {{
        transform: scale(0.96);
        opacity: .55;
      }}
      50% {{
        transform: scale(1.04);
        opacity: 1;
      }}
    }}

    @media (max-width: 900px) {{
      .login-screen {{
        grid-template-columns: 1fr;
        gap: 24px;
      }}

      .login-pulse-wrap {{
        width: min(62vw, 240px);
      }}

      .login-card {{
        padding: 24px;
      }}
    }}
  </style>
</head>
<body class="login-body">
  <main class="login-page">
    <section class="login-screen">
      <div class="login-pulse-wrap" aria-hidden="true">
        <span class="login-pulse-ring ring-1"></span>
        <span class="login-pulse-ring ring-2"></span>
        <span class="login-pulse-core"></span>
      </div>

      <div class="login-card">
        <p class="login-eyebrow">FLEXMEDIA TOTEM</p>
        <h1 class="login-title">Área administrativa</h1>
        <p class="login-subtitle">
          Entre com suas credenciais para acessar o painel técnico do totem.
        </p>

        {error_block}

        <form method="post" action="/login" class="login-form">
          <div class="login-field">
            <label for="username">Usuário</label>
            <input id="username" name="username" type="text" autocomplete="username" required maxlength="50" />
          </div>

          <div class="login-field">
            <label for="password">Senha</label>
            <input id="password" name="password" type="password" autocomplete="current-password" required maxlength="100" />
          </div>

          <!--
          <label class="login-check">
            <input type="checkbox" name="lgpd" required />
            <span>Aceito os termos LGPD e o uso dos dados para autenticação e auditoria de acesso.</span>
          </label>
          -->

          <button class="login-button" type="submit">Entrar</button>
        </form>

        <a href="/integration" class="login-back">Voltar ao totem</a>
      </div>
    </section>
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
    # lgpd: str = Form("off"),
):
    # if lgpd != "on":
    #     return HTMLResponse(_login_html("Aceite LGPD obrigatório."), status_code=400)

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
