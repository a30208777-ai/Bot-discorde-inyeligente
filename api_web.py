# ================= API DO SITE (roda no RENDER) =================
# Só fala com o Supabase e com o login do Discord (OAuth2, para descobrir o ID do usuário).
# NÃO conecta no Discord como bot e NÃO usa APIs de IA. O bot roda no celular.
#
# Variáveis de ambiente no Render:
#   SUPABASE_URL, CHAVE_SUPABASE
#   DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET
#   DISCORD_REDIRECT_URI   ex.: https://SEU-SERVICO.onrender.com/auth/callback
#   SITE_URL               ex.: https://survival-word-entrada-discorde-links.lovable.app
#   PORT                   o Render define sozinho

import hashlib
import json
import os
import random
import secrets
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlencode, urlparse, parse_qs

import requests

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("CHAVE_SUPABASE", "")
CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "")
REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "")
SITE_URL = os.getenv("SITE_URL", "*")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}
FAIXA_SAQUE = (100, 5000)   # valor sorteado, múltiplos de 100
FUSO_BRASILIA = timezone(timedelta(hours=-3))  # Brasil sem horário de verão


def _sha(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def _get(tabela, params):
    r = requests.get(f"{SUPABASE_URL}/rest/v1/{tabela}", headers={**HEADERS, "Prefer": ""}, params=params, timeout=10)
    r.raise_for_status()
    return r.json()


def _post(tabela, dados, extra_prefer="return=minimal", on_conflict=None):
    url = f"{SUPABASE_URL}/rest/v1/{tabela}" + (f"?on_conflict={on_conflict}" if on_conflict else "")
    return requests.post(url, headers={**HEADERS, "Prefer": extra_prefer}, json=dados, timeout=10)


def _agora_brasilia():
    return datetime.now(FUSO_BRASILIA)


# ---------- senha e config (mesmo que antes) ----------
def guild_da_chave(chave):
    if not chave:
        return None
    linhas = _get("servidores", {"chave_hash": f"eq.{_sha(chave)}", "select": "guild_id"})
    return linhas[0]["guild_id"] if linhas else None


def api_senha(chave):
    gid = guild_da_chave(chave)
    if gid is None:
        return 401, {"pass": "erro", "mensagem": "Chave inválida."}
    return 200, {"pass": "ok", "id": gid}


def api_config_get(chave):
    gid = guild_da_chave(chave)
    if gid is None:
        return 401, {"erro": "Chave inválida."}
    linhas = _get("configs_servidor", {"guild_id": f"eq.{gid}", "select": "prompt_geral,prompt_evento"})
    cfg = linhas[0] if linhas else {"prompt_geral": None, "prompt_evento": None}
    return 200, {"id": gid, **cfg}


def api_config_set(corpo):
    gid = guild_da_chave(str(corpo.get("pass", "")))
    if gid is None:
        return 401, {"erro": "Chave inválida."}
    dados = {"guild_id": gid, "atualizado": datetime.utcnow().isoformat() + "Z"}
    for campo in ("prompt_geral", "prompt_evento"):
        if campo in corpo:
            dados[campo] = str(corpo[campo] or "")[:8000]
    _post("configs_servidor", dados, "resolution=merge-duplicates,return=minimal", "guild_id")
    return 200, {"ok": True}


# ---------- login com Discord (OAuth2) ----------
def url_login_discord():
    params = {"client_id": CLIENT_ID, "redirect_uri": REDIRECT_URI, "response_type": "code", "scope": "identify"}
    return "https://discord.com/oauth2/authorize?" + urlencode(params)


def login_callback(codigo):
    """Troca o código pelo token do Discord, pega o ID do usuário e cria uma sessão do site."""
    r = requests.post(
        "https://discord.com/api/oauth2/token",
        data={
            "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET, "grant_type": "authorization_code",
            "code": codigo, "redirect_uri": REDIRECT_URI,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )
    if r.status_code != 200:
        return None
    acesso = r.json().get("access_token")
    u = requests.get("https://discord.com/api/users/@me", headers={"Authorization": f"Bearer {acesso}"}, timeout=10)
    if u.status_code != 200:
        return None
    user_id = u.json()["id"]
    token = secrets.token_urlsafe(32)
    _post("sessoes_site", {
        "token_hash": _sha(token),
        "discord_user_id": user_id,
        "expira_em": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
    }, "resolution=merge-duplicates,return=minimal", "token_hash")
    return token


def usuario_da_sessao(cabecalho_auth):
    if not cabecalho_auth or not cabecalho_auth.startswith("Bearer "):
        return None
    token = cabecalho_auth[len("Bearer "):].strip()
    linhas = _get("sessoes_site", {"token_hash": f"eq.{_sha(token)}", "select": "discord_user_id,expira_em"})
    if not linhas:
        return None
    expira = datetime.fromisoformat(linhas[0]["expira_em"].replace("Z", "+00:00"))
    if expira < datetime.now(timezone.utc):
        return None
    return linhas[0]["discord_user_id"]


# ---------- saldo e saque ----------
def api_saldo(user_id):
    linhas = _get("moedas_ia", {"discord_user_id": f"eq.{user_id}", "select": "saldo"})
    saldo = int(linhas[0]["saldo"]) if linhas else 0
    hoje = _agora_brasilia().date().isoformat()
    sacou = _get("saques", {"discord_user_id": f"eq.{user_id}", "dia": f"eq.{hoje}", "select": "valor"})
    return 200, {"saldo": saldo, "pode_sacar_hoje": not sacou}


def api_sacar(user_id):
    hoje = _agora_brasilia().date().isoformat()
    valor = random.randrange(FAIXA_SAQUE[0], FAIXA_SAQUE[1] + 1, 100)
    # A tabela tem UNIQUE (discord_user_id, dia): se já sacou hoje, o banco recusa (409).
    r = _post("saques", {"discord_user_id": str(user_id), "valor": valor, "dia": hoje})
    if r.status_code == 409:
        return 429, {"erro": "Você já sacou hoje. Um novo saque libera à meia-noite (horário de Brasília)."}
    r.raise_for_status()
    linhas = _get("moedas_ia", {"discord_user_id": f"eq.{user_id}", "select": "saldo,nome"})
    atual = int(linhas[0]["saldo"]) if linhas else 0
    _post("moedas_ia", {
        "discord_user_id": str(user_id),
        "nome": (linhas[0].get("nome") if linhas else "") or "",
        "saldo": atual + valor,
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }, "resolution=merge-duplicates,return=minimal", "discord_user_id")
    return 200, {"sacou": valor, "saldo": atual + valor}


# ---------- servidor HTTP ----------
class Handler(BaseHTTPRequestHandler):
    def _enviar(self, codigo, dados=None, redirecionar=None):
        if redirecionar:
            self.send_response(302)
            self.send_header("Location", redirecionar)
            self.end_headers()
            return
        corpo = json.dumps(dados or {}, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", SITE_URL)
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(corpo)

    def do_OPTIONS(self):
        self._enviar(200, {})

    def do_GET(self):
        url = urlparse(self.path)
        q = parse_qs(url.query)
        try:
            if url.path in ("/", ""):
                return self._enviar(200, {"status": "API do site online."})
            if url.path == "/api/v1/senha":
                return self._enviar(*api_senha(q.get("pass", [""])[0]))
            if url.path == "/api/v1/config":
                return self._enviar(*api_config_get(q.get("pass", [""])[0]))
            if url.path == "/auth/discord":
                return self._enviar(302, redirecionar=url_login_discord())
            if url.path == "/auth/callback":
                token = login_callback(q.get("code", [""])[0])
                if not token:
                    return self._enviar(400, {"erro": "Não foi possível fazer login com o Discord."})
                return self._enviar(302, redirecionar=f"{SITE_URL}#token={token}")
            if url.path == "/api/v1/saldo":
                uid = usuario_da_sessao(self.headers.get("Authorization"))
                if not uid:
                    return self._enviar(401, {"erro": "Faça login com o Discord."})
                return self._enviar(*api_saldo(uid))
            return self._enviar(404, {"erro": "Rota não encontrada."})
        except requests.RequestException as e:
            return self._enviar(503, {"erro": f"Serviço indisponível: {e}"})

    def do_POST(self):
        url = urlparse(self.path)
        tamanho = int(self.headers.get("Content-Length", 0) or 0)
        try:
            corpo = json.loads(self.rfile.read(tamanho) or b"{}")
        except ValueError:
            return self._enviar(400, {"erro": "JSON inválido."})
        try:
            if url.path == "/api/v1/config":
                return self._enviar(*api_config_set(corpo))
            if url.path == "/api/v1/sacar":
                uid = usuario_da_sessao(self.headers.get("Authorization"))
                if not uid:
                    return self._enviar(401, {"erro": "Faça login com o Discord."})
                return self._enviar(*api_sacar(uid))
            return self._enviar(404, {"erro": "Rota não encontrada."})
        except requests.RequestException as e:
            return self._enviar(503, {"erro": f"Serviço indisponível: {e}"})

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    porta = int(os.getenv("PORT", "10000"))
    print(f"API do site na porta {porta}")
    HTTPServer(("0.0.0.0", porta), Handler).serve_forever()
