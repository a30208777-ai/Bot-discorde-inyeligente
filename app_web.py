# ================= UP MODELOS (site local) =================
# Roda só no seu celular (127.0.0.1). Não pede senha.
# Precisa estar na mesma pasta do chat_ias.py.
# Instalar no Termux:  pip install flask
# Rodar:               python app_web.py   e abra http://127.0.0.1:5000 no navegador

import os
from pathlib import Path

from flask import Flask, request, redirect, url_for, render_template_string, abort

import chat_ias as core

app = Flask(__name__)

# ================= CONFIGURAÇÃO DA UP =================
# Nível de cada modelo (10 = melhor, 1 = pior). Preencha como quiser.
# Ex.: NIVEIS = {"aion-labs/aion-3.0": 9, "Qwen/Qwen3.5-27B": 7}
NIVEIS = {}
NIVEL_PADRAO = 5

# A maioria das APIs não informa o saldo de tokens de forma padrão.
# Preencha aqui (ou pela variável de ambiente TOKENS_DISPONIVEIS).
TOKENS_DISPONIVEIS = os.getenv("TOKENS_DISPONIVEIS", "não informado")

MENSAGENS = []   # (autor, texto) mostrados na tela
HISTORICO = [{"role": "system", "content": core.instrucao()}]


def modelo_atual() -> str:
    if core.PREFERIDO:
        return core.PREFERIDO
    return core.MODELOS[0][0] if core.MODELOS else "nenhum"


def nivel_do(nome: str) -> int:
    return NIVEIS.get(nome, NIVEL_PADRAO)


def boas_vindas() -> str:
    nome = modelo_atual()
    return (
        f"Bem-vindo à UP modelos! Eu sou {nome} e são {len(core.MODELOS)} modelos. "
        f"Meu nível é {nivel_do(nome)} (10 é o melhor e 1 o pior). "
        f"Eu tenho {TOKENS_DISPONIVEIS} tokens disponíveis. Pode me chamar de UP."
    )


def listar(pasta: str):
    base = core.caminho_seguro(pasta)
    if not base.is_dir():
        abort(404)
    pastas, arquivos = [], []
    for p in sorted(base.iterdir()):
        (pastas if p.is_dir() else arquivos).append(p.name)
    return pastas, arquivos


def juntar(pasta: str, nome: str) -> str:
    return f"{pasta}/{nome}" if pasta else nome


def migalhas(pasta: str):
    """Lista de pastas até a atual, para mostrar o caminho na tela."""
    partes, acumulado = [], ""
    for nome in [p for p in pasta.split("/") if p]:
        acumulado = juntar(acumulado, nome)
        partes.append({"nome": nome, "caminho": acumulado})
    return partes


# ================= TELA =================
@app.route("/")
def index():
    pasta = request.args.get("pasta", "").strip("/")
    pastas, arquivos = listar(pasta)
    return render_template_string(
        PAGINA,
        pasta=pasta,
        pai=os.path.dirname(pasta),
        pastas=pastas,
        arquivos=arquivos,
        boas_vindas=boas_vindas(),
        mensagens=MENSAGENS,
        total_modelos=len(core.MODELOS),
        nivel=nivel_do(modelo_atual()),
        tokens=TOKENS_DISPONIVEIS,
        partes=migalhas(pasta),
    )


@app.route("/upload", methods=["POST"])
def upload():
    pasta = request.form.get("pasta", "")
    core.caminho_seguro(pasta)  # garante que a pasta está dentro da área da IA
    for arquivo in request.files.getlist("arquivos"):
        if arquivo.filename:
            nome = Path(arquivo.filename).name
            arquivo.save(core.caminho_seguro(juntar(pasta, nome)))
    return redirect(url_for("index", pasta=pasta))


@app.route("/nova-pasta", methods=["POST"])
def nova_pasta():
    pasta = request.form.get("pasta", "")
    nome = request.form.get("nome", "").strip()
    if nome and nome not in (".", "..") and "/" not in nome and "\\" not in nome:
        core.caminho_seguro(juntar(pasta, nome)).mkdir(parents=True, exist_ok=True)
    return redirect(url_for("index", pasta=pasta))


@app.route("/apagar", methods=["POST"])
def apagar():
    pasta = request.form.get("pasta", "")
    nome = request.form.get("nome", "")
    # A tela pede confirmação ao usuário; sem o "sim" o servidor não apaga nada.
    if request.form.get("confirmar") != "sim":
        return redirect(url_for("index", pasta=pasta))
    alvo = core.caminho_seguro(juntar(pasta, nome))
    if alvo == core.PASTA_IA:
        abort(400)
    if alvo.exists():
        core.mover_para_lixeira(alvo)
    return redirect(url_for("index", pasta=pasta))


@app.route("/chat", methods=["POST"])
def chat():
    pasta = request.form.get("pasta", "")
    texto = request.form.get("mensagem", "").strip()
    if texto:
        MENSAGENS.append(("Você", texto))
        msg_sistema = core.comando_modelo(texto)
        if msg_sistema is not None:
            MENSAGENS.append(("Sistema", msg_sistema))
            return redirect(url_for("index", pasta=pasta))
        HISTORICO.append({"role": "user", "content": texto})
        core.salvar(1, texto, core.NOME_USUARIO)

        # Pela tela, a IA não apaga sozinha: apagar só pelo botão Apagar da lista.
        nome, resposta, log = core.conversar(HISTORICO, confirmar=lambda _nome: False)
        if nome is None:
            MENSAGENS.append(("UP", "Nenhum modelo disponível no momento. Tente mais tarde."))
        else:
            if log:
                MENSAGENS.append(("Sistema", "\n".join(log)))
            core.salvar(0, resposta, nome)
            MENSAGENS.append((nome, resposta))
    return redirect(url_for("index", pasta=pasta))


# ================= HTML =================
PAGINA = """
<!doctype html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#0f1115">
<title>UP modelos</title>
<style>
  :root {
    --bg: #0f1115; --card: #171a21; --card2: #1e222b; --borda: #2a2f3a;
    --texto: #e7e9ee; --sub: #8b93a7; --acento: #6d7cff; --acento2: #4f5fe0;
    --perigo: #e5484d; --ok: #30a46c;
  }
  * { box-sizing: border-box; }
  html, body { height: 100%; }
  body {
    margin: 0; font-family: -apple-system, system-ui, "Segoe UI", Roboto, sans-serif;
    background: var(--bg); color: var(--texto); display: flex; flex-direction: column;
  }
  header {
    position: sticky; top: 0; z-index: 10;
    display: flex; align-items: center; gap: 10px;
    padding: calc(12px + env(safe-area-inset-top)) 16px 12px;
    background: rgba(15,17,21,.9); backdrop-filter: blur(8px);
    border-bottom: 1px solid var(--borda);
  }
  .logo {
    width: 36px; height: 36px; border-radius: 10px; display: grid; place-items: center;
    background: linear-gradient(135deg, var(--acento), #b56cff); font-weight: 800; font-size: 14px;
  }
  .titulo { flex: 1; min-width: 0; }
  .titulo b { display: block; font-size: 16px; }
  .titulo span { display: block; font-size: 12px; color: var(--sub);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

  main { flex: 1; padding: 16px; padding-bottom: 120px; max-width: 720px; width: 100%; margin: 0 auto; }

  .boas-vindas {
    background: linear-gradient(160deg, #1d2140, #171a21); border: 1px solid var(--borda);
    border-radius: 16px; padding: 16px; margin-bottom: 16px;
  }
  .boas-vindas h2 { margin: 0 0 6px; font-size: 17px; }
  .boas-vindas p { margin: 0; color: #c9cedb; font-size: 14px; line-height: 1.5; }
  .chips { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
  .chip { font-size: 12px; padding: 5px 10px; border-radius: 999px; background: var(--card2);
    border: 1px solid var(--borda); color: #c9cedb; }

  .secao { font-size: 12px; text-transform: uppercase; letter-spacing: .08em; color: var(--sub);
    margin: 20px 4px 8px; }

  .caminho { display: flex; align-items: center; gap: 8px; background: var(--card);
    border: 1px solid var(--borda); border-radius: 12px; padding: 10px 12px; font-size: 13px;
    color: var(--sub); overflow-x: auto; white-space: nowrap; }
  .caminho a { color: var(--acento); text-decoration: none; font-weight: 600; }

  .lista { background: var(--card); border: 1px solid var(--borda); border-radius: 14px; overflow: hidden; }
  .item { display: flex; align-items: center; gap: 12px; padding: 12px 14px; border-bottom: 1px solid var(--borda); }
  .item:last-child { border-bottom: 0; }
  .icone { width: 38px; height: 38px; border-radius: 10px; display: grid; place-items: center; font-size: 18px;
    background: var(--card2); flex-shrink: 0; }
  .icone.pasta { background: rgba(109,124,255,.15); }
  .info { flex: 1; min-width: 0; }
  .info a, .info span.nome { display: block; color: var(--texto); text-decoration: none; font-weight: 600;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 15px; }
  .info small { color: var(--sub); font-size: 12px; }
  .vazio { padding: 24px; text-align: center; color: var(--sub); font-size: 14px; }

  .btn { border: 0; border-radius: 10px; padding: 9px 14px; font-size: 14px; font-weight: 600;
    cursor: pointer; color: #fff; background: var(--acento); }
  .btn:active { transform: scale(.97); }
  .btn-perigo { background: transparent; color: var(--perigo); border: 1px solid rgba(229,72,77,.4); padding: 7px 11px; }
  .btn-ghost { background: var(--card2); color: var(--texto); border: 1px solid var(--borda); }

  .msgs { display: flex; flex-direction: column; gap: 10px; margin-bottom: 8px; }
  .bolha { max-width: 85%; padding: 10px 14px; border-radius: 16px; line-height: 1.5; font-size: 15px;
    white-space: pre-wrap; word-wrap: break-word; }
  .bolha .autor { display: block; font-size: 11px; color: var(--sub); margin-bottom: 4px; font-weight: 600; }
  .bolha.voce { align-self: flex-end; background: var(--acento2); border-bottom-right-radius: 4px; }
  .bolha.up { align-self: flex-start; background: var(--card2); border: 1px solid var(--borda); border-bottom-left-radius: 4px; }

  /* Barra inferior fixa */
  .barra {
    position: fixed; left: 0; right: 0; bottom: 0; z-index: 20;
    padding: 10px 12px calc(10px + env(safe-area-inset-bottom));
    background: rgba(15,17,21,.95); backdrop-filter: blur(8px); border-top: 1px solid var(--borda);
  }
  .barra-linha { max-width: 720px; margin: 0 auto; display: flex; align-items: flex-end; gap: 8px; }
  .mais {
    width: 46px; height: 46px; border-radius: 14px; border: 1px solid var(--borda);
    background: var(--card2); color: var(--texto); font-size: 26px; line-height: 1; cursor: pointer;
    flex-shrink: 0; transition: transform .2s;
  }
  .mais.aberto { transform: rotate(45deg); background: var(--acento); border-color: var(--acento); color: #fff; }
  .campo {
    flex: 1; resize: none; background: var(--card2); color: var(--texto); border: 1px solid var(--borda);
    border-radius: 14px; padding: 12px 14px; font-size: 15px; font-family: inherit; max-height: 120px;
    outline: none;
  }
  .campo:focus { border-color: var(--acento); }
  .enviar { height: 46px; padding: 0 18px; }

  /* Menu do + */
  .painel {
    position: fixed; left: 12px; right: 12px; bottom: calc(76px + env(safe-area-inset-bottom));
    max-width: 696px; margin: 0 auto; z-index: 15;
    background: var(--card); border: 1px solid var(--borda); border-radius: 18px; padding: 14px;
    box-shadow: 0 -10px 40px rgba(0,0,0,.4);
    display: none; flex-direction: column; gap: 12px;
  }
  .painel.aberto { display: flex; }
  .painel h4 { margin: 0; font-size: 13px; color: var(--sub); font-weight: 600; }
  .painel form { display: flex; gap: 8px; margin: 0; }
  .painel input[type=file] { flex: 1; color: var(--sub); font-size: 13px; min-width: 0; }
  .painel input[type=text] {
    flex: 1; min-width: 0; background: var(--card2); color: var(--texto); border: 1px solid var(--borda);
    border-radius: 10px; padding: 10px 12px; font-size: 14px; outline: none;
  }
  .divisor { height: 1px; background: var(--borda); }
</style>
</head>
<body>

<header>
  <div class="logo">UP</div>
  <div class="titulo">
    <b>UP modelos</b>
    <span>{{ '/' + pasta if pasta else 'Início' }}</span>
  </div>
</header>

<main>
  <section class="boas-vindas">
    <h2>Bem-vindo à UP modelos</h2>
    <p>{{ boas_vindas }}</p>
    <div class="chips">
      <span class="chip">{{ total_modelos }} modelos</span>
      <span class="chip">Nível {{ nivel }}/10</span>
      <span class="chip">{{ tokens }} tokens</span>
    </div>
  </section>

  {% if mensagens %}
    <div class="secao">Conversa</div>
    <div class="msgs">
      {% for autor, texto in mensagens %}
        <div class="bolha {{ 'voce' if autor == 'Você' else 'up' }}">
          <span class="autor">{{ autor }}</span>{{ texto }}
        </div>
      {% endfor %}
    </div>
  {% endif %}

  <div class="secao">Arquivos</div>
  <div class="caminho">
    <span>📂</span>
    <a href="{{ url_for('index') }}">início</a>
    {% for parte in partes %}
      <span>/</span>
      <a href="{{ url_for('index', pasta=parte.caminho) }}">{{ parte.nome }}</a>
    {% endfor %}
  </div>

  <div class="lista" style="margin-top:10px">
    {% if pasta %}
      <div class="item">
        <div class="icone">⬅️</div>
        <div class="info"><a href="{{ url_for('index', pasta=pai) }}">Voltar</a></div>
      </div>
    {% endif %}

    {% for p in pastas %}
      <div class="item">
        <div class="icone pasta">📁</div>
        <div class="info">
          <a href="{{ url_for('index', pasta=juntar(pasta, p)) }}">{{ p }}</a>
          <small>Pasta</small>
        </div>
        <form method="post" action="{{ url_for('apagar') }}" style="margin:0"
              onsubmit='return confirm({{ ("UP: posso apagar a pasta " ~ p ~ " e tudo dentro dela?") | tojson }})'>
          <input type="hidden" name="pasta" value="{{ pasta }}">
          <input type="hidden" name="nome" value="{{ p }}">
          <input type="hidden" name="confirmar" value="sim">
          <button class="btn btn-perigo" type="submit">Apagar</button>
        </form>
      </div>
    {% endfor %}

    {% for a in arquivos %}
      <div class="item">
        <div class="icone">📄</div>
        <div class="info">
          <span class="nome">{{ a }}</span>
          <small>Arquivo</small>
        </div>
        <form method="post" action="{{ url_for('apagar') }}" style="margin:0"
              onsubmit='return confirm({{ ("UP: posso apagar " ~ a ~ "?") | tojson }})'>
          <input type="hidden" name="pasta" value="{{ pasta }}">
          <input type="hidden" name="nome" value="{{ a }}">
          <input type="hidden" name="confirmar" value="sim">
          <button class="btn btn-perigo" type="submit">Apagar</button>
        </form>
      </div>
    {% endfor %}

    {% if not pastas and not arquivos and not pasta %}
      <div class="vazio">Nenhum arquivo ainda. Toque em + para enviar ou criar uma pasta.</div>
    {% elif not pastas and not arquivos %}
      <div class="vazio">Esta pasta está vazia.</div>
    {% endif %}
  </div>
</main>

<!-- Painel do + (enviar arquivos e criar pasta) -->
<div id="painel" class="painel">
  <h4>Enviar arquivos</h4>
  <form method="post" action="{{ url_for('upload') }}" enctype="multipart/form-data">
    <input type="hidden" name="pasta" value="{{ pasta }}">
    <input type="file" name="arquivos" multiple>
    <button class="btn" type="submit">Enviar</button>
  </form>
  <div class="divisor"></div>
  <h4>Nova pasta</h4>
  <form method="post" action="{{ url_for('nova_pasta') }}">
    <input type="hidden" name="pasta" value="{{ pasta }}">
    <input type="text" name="nome" placeholder="Nome da pasta">
    <button class="btn btn-ghost" type="submit">Criar</button>
  </form>
</div>

<!-- Barra inferior: + e conversa -->
<div class="barra">
  <form class="barra-linha" method="post" action="{{ url_for('chat') }}">
    <input type="hidden" name="pasta" value="{{ pasta }}">
    <button type="button" class="mais" id="botaoMais" aria-label="Mais opções">+</button>
    <textarea class="campo" name="mensagem" rows="1" placeholder="Digite uma mensagem ou comando"></textarea>
    <button class="btn enviar" type="submit">Enviar</button>
  </form>
</div>

<script>
  const botao = document.getElementById('botaoMais');
  const painel = document.getElementById('painel');
  botao.addEventListener('click', () => {
    painel.classList.toggle('aberto');
    botao.classList.toggle('aberto');
  });
</script>
</body>
</html>
"""


@app.context_processor
def utilitarios():
    return {"juntar": juntar}


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
