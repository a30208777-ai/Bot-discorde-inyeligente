# ================= LEMBRETE =================
# A IA tem acesso ao dispositivo, mas somente à pasta dedicada abaixo (PASTA_IA).
# Tudo fica nessa pasta, exceto a conversa, que fica no Supabase (tabela conversas).
# Ela pode criar, ler e editar arquivos dentro da pasta, mas NÃO apaga nada sem
# pedir permissão. A regra está no código: apagar_arquivo() exige confirmação.

import os
import re
import shutil
from datetime import datetime
from pathlib import Path

import requests

# ================= CONFIGURAÇÃO =================
# ----- COLE SUAS CHAVES AQUI (entre as aspas) -----
# Não envie este arquivo com as chaves preenchidas para o GitHub.
CHAVE_SUPABASE = os.getenv("CHAVE_SUPABASE", "")     # ex: "sua_anon_key"
CHAVE_MODELO_1 = os.getenv("CHAVE_MODELO_1", "")     # ex: "sua_chave"
CHAVE_MODELO_2 = os.getenv("CHAVE_MODELO_2", "")     # ex: "sua_chave"
CHAVE_AION = os.getenv("CHAVE_AION", "")         # chave da Aion Labs
CHAVE_COHERE = os.getenv("CHAVE_COHERE", "")       # chave de teste da Cohere
CHAVE_GEMINI = os.getenv("CHAVE_GEMINI", "")       # chave do Google AI Studio (Gemini)
CHAVE_MISTRAL = os.getenv("CHAVE_MISTRAL", "")      # chave da Mistral AI
CHAVE_ZAI = os.getenv("CHAVE_ZAI", "")          # chave da Z AI (Zhipu AI)
CHAVE_GONKA = os.getenv("CHAVE_GONKA", "")        # chave do Corretor Gonka
CHAVE_GROQ = os.getenv("CHAVE_GROQ", "")         # chave da Groq
CHAVE_MODELSCOPE = os.getenv("CHAVE_MODELSCOPE", "")   # token do ModelScope (conta com verificação)
CHAVE_NVIDIA = os.getenv("CHAVE_NVIDIA", "")       # chave da NVIDIA NIM (nvapi-...)
CHAVE_OPENROUTER = os.getenv("CHAVE_OPENROUTER", "")   # chave do OpenRouter (sk-or-...)
CHAVE_SILICONFLOW = os.getenv("CHAVE_SILICONFLOW", "")  # chave da SiliconFlow (conta com verificação)
# --------------------------------------------------

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://auytitpxyqlvafiaznlx.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", CHAVE_SUPABASE)
NOME_USUARIO = os.getenv("NOME_USUARIO", "Usuario")

# ----- PASTA DA IA (escolhida pelo usuário) -----
# Ordem: variável PASTA_IA > pasta salva antes > pergunta no primeiro uso.
ARQUIVO_CONFIG_PASTA = Path(os.path.expanduser("~/.chat_ias_pasta.txt"))


def escolher_pasta() -> Path:
    env = os.getenv("PASTA_IA", "").strip()
    if env:
        return Path(env).expanduser().resolve()

    if ARQUIVO_CONFIG_PASTA.exists():
        return Path(ARQUIVO_CONFIG_PASTA.read_text(encoding="utf-8").strip()).expanduser().resolve()

    print("Onde a IA deve guardar os arquivos?")
    print("Exemplo: /storage/emulated/0/Download/IA_arquivos")
    print("(No Termux, rode 'termux-setup-storage' antes para liberar o acesso ao armazenamento.)")
    while True:
        caminho = input("Caminho da pasta: ").strip()
        if not caminho:
            continue
        pasta = Path(caminho).expanduser().resolve()
        try:
            pasta.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            print(f"Não consegui criar essa pasta: {e}. Tente outro caminho.")
            continue
        ARQUIVO_CONFIG_PASTA.write_text(str(pasta), encoding="utf-8")
        print(f"Pasta salva: {pasta}\n")
        return pasta


PASTA_IA = escolher_pasta()
PASTA_IA.mkdir(parents=True, exist_ok=True)
PASTA_LIXEIRA = PASTA_IA / ".lixeira"


def guardar_copia(alvo: Path) -> Path:
    """Copia o arquivo para a lixeira antes de sobrescrever ou apagar."""
    PASTA_LIXEIRA.mkdir(parents=True, exist_ok=True)
    destino = PASTA_LIXEIRA / f"{datetime.now():%Y%m%d-%H%M%S}_{alvo.name}"
    shutil.copy2(alvo, destino)
    return destino


def mover_para_lixeira(alvo: Path) -> Path:
    """Em vez de apagar de verdade, move para a lixeira (dá para recuperar)."""
    PASTA_LIXEIRA.mkdir(parents=True, exist_ok=True)
    destino = PASTA_LIXEIRA / f"{datetime.now():%Y%m%d-%H%M%S}_{alvo.name}"
    shutil.move(str(alvo), str(destino))
    return destino

# ================= MODELOS (ordem: do melhor para o mais simples) =================
# Cada item: (nome do modelo, URL do chat/completions, chave)
# Exemplo:
# ("nome-do-modelo", "https://api.provedor.com/v1/chat/completions", CHAVE_MODELO_1),
AION_URL = "https://api.aionlabs.ai/v1/chat/completions"

MODELOS = [
    ("aion-labs/aion-3.0", AION_URL, CHAVE_AION),
    ("aion-labs/aion-2.0", AION_URL, CHAVE_AION),
    ("aion-labs/aion-3.0-mini", AION_URL, CHAVE_AION),
    ("aion-labs/aion-rp-llama-3.1-8b", AION_URL, CHAVE_AION),
]

# Cohere: usa o endpoint compatível com OpenAI (o formato de resposta é o mesmo do script).
COHERE_URL = "https://api.cohere.ai/compatibility/v1/chat/completions"

MODELOS += [
    ("command-a-reasoning-08-2025", COHERE_URL, CHAVE_COHERE),
    ("command-a-03-2025", COHERE_URL, CHAVE_COHERE),
    ("command-r-plus-08-2024", COHERE_URL, CHAVE_COHERE),
    ("command-a-vision-07-2025", COHERE_URL, CHAVE_COHERE),
    ("command-r-08-2024", COHERE_URL, CHAVE_COHERE),
    ("command-r7b-12-2024", COHERE_URL, CHAVE_COHERE),
    ("command-a-translate-08-2025", COHERE_URL, CHAVE_COHERE),
    ("command-r7b-arabic-02-2025", COHERE_URL, CHAVE_COHERE),
    ("c4ai-aya-expanse-32b", COHERE_URL, CHAVE_COHERE),
    ("c4ai-aya-vision-32b", COHERE_URL, CHAVE_COHERE),
]

# Google Gemini: endpoint compatível com OpenAI (a URL base v1beta + /openai/chat/completions).
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"

MODELOS += [
    ("gemini-3.8-flash", GEMINI_URL, CHAVE_GEMINI),
    ("gemini-3.6-flash", GEMINI_URL, CHAVE_GEMINI),
    ("gemini-3.5-flash-lite", GEMINI_URL, CHAVE_GEMINI),
    ("gemini-3.1-flash-lite", GEMINI_URL, CHAVE_GEMINI),
    ("gemini-2.5-flash", GEMINI_URL, CHAVE_GEMINI),
    ("gemini-2.5-flash-lite", GEMINI_URL, CHAVE_GEMINI),
    ("gemma-4-31b-it", GEMINI_URL, CHAVE_GEMINI),
    ("gemma-4-26b-a4b-it", GEMINI_URL, CHAVE_GEMINI),
]

# Mistral AI: endpoint padrão OpenAI (base https://api.mistral.ai/v1).
MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"

MODELOS += [
    ("mistral-medium-latest", MISTRAL_URL, CHAVE_MISTRAL),
    ("mistral-large-latest", MISTRAL_URL, CHAVE_MISTRAL),
    ("mistral-small-latest", MISTRAL_URL, CHAVE_MISTRAL),
    ("codestral-latest", MISTRAL_URL, CHAVE_MISTRAL),
    ("ministral-8b-latest", MISTRAL_URL, CHAVE_MISTRAL),
    ("ministral-3b-latest", MISTRAL_URL, CHAVE_MISTRAL),
]

# Z AI (Zhipu AI): endpoint padrão OpenAI (base https://open.bigmodel.cn/api/paas/v4).
ZAI_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

MODELOS += [
    ("glm-4.7-flash", ZAI_URL, CHAVE_ZAI),
    ("glm-4.6v-flash", ZAI_URL, CHAVE_ZAI),
    ("glm-4.5-flash", ZAI_URL, CHAVE_ZAI),
]

# Corretor Gonka: endpoint padrão OpenAI (base https://proxy.gonkabroker.com/v1).
# BAAI/bge-m3 é de embeddings (não conversa), então não entra na lista.
GONKA_URL = "https://proxy.gonkabroker.com/v1/chat/completions"

MODELOS += [
    ("MiniMaxAI/MiniMax-M2.7", GONKA_URL, CHAVE_GONKA),
    ("deepseek-ai/DeepSeek-V4-Flash-0731", GONKA_URL, CHAVE_GONKA),
    ("zai-org/GLM-5.3-Flash", GONKA_URL, CHAVE_GONKA),
]

# Groq: endpoint padrão OpenAI (base https://api.groq.com/openai/v1).
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

MODELOS += [
    ("openai/gpt-oss-120b", GROQ_URL, CHAVE_GROQ),
    ("openai/gpt-oss-20b", GROQ_URL, CHAVE_GROQ),
    ("qwen/qwen3.8-27b", GROQ_URL, CHAVE_GROQ),
]


SUPABASE_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
}

INSTRUCAO_SISTEMA = (
    "Você é um assistente útil. Responda em português. "
    f"Você só pode acessar arquivos dentro da pasta {PASTA_IA}. "
    "Nunca apague arquivos sem pedir permissão ao usuário."
)


# ================= ARQUIVOS (somente dentro de PASTA_IA) =================
def caminho_seguro(nome: str) -> Path:
    """Resolve o caminho e garante que ele continua dentro de PASTA_IA."""
    alvo = (PASTA_IA / nome).resolve()
    if PASTA_IA != alvo and PASTA_IA not in alvo.parents:
        raise PermissionError(f"Acesso negado fora de {PASTA_IA}: {nome}")
    return alvo


def ler_arquivo(nome: str) -> str:
    return caminho_seguro(nome).read_text(encoding="utf-8")


def escrever_arquivo(nome: str, conteudo: str):
    """Cria ou edita um arquivo dentro da pasta da IA."""
    alvo = caminho_seguro(nome)
    alvo.parent.mkdir(parents=True, exist_ok=True)
    alvo.write_text(conteudo, encoding="utf-8")


def listar_arquivos() -> list:
    return sorted(
        str(p.relative_to(PASTA_IA))
        for p in PASTA_IA.rglob("*")
        if p.is_file() and not any(parte.startswith(".") for parte in p.relative_to(PASTA_IA).parts)
    )


def apagar_arquivo(nome: str) -> bool:
    """Apaga só depois de o usuário confirmar. Sem 's', nada é apagado."""
    alvo = caminho_seguro(nome)
    if not alvo.exists():
        print(f"Arquivo não existe: {nome}")
        return False
    resposta = input(f"A IA quer apagar '{nome}'. Permitir? (s/n): ").strip().lower()
    if resposta != "s":
        print("Exclusão cancelada.")
        return False
    destino = mover_para_lixeira(alvo)
    print(f"Arquivo movido para a lixeira: {destino}")
    return True


# Kilo Code: gateway gratuito SEM chave (key = None).
KILO_URL = "https://api.kilo.ai/api/gateway/chat/completions"

MODELOS += [
    ("nvidia/nemotron-3-ultra-550b-a55b:free", KILO_URL, None),
    ("nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free", KILO_URL, None),
    ("poolside/laguna-s-2.1:free", KILO_URL, None),
    ("poolside/laguna-xs-2.1:free", KILO_URL, None),
    ("cohere/north-mini-code:free", KILO_URL, None),
    ("openrouter/free", KILO_URL, None),
    ("nvidia/nemotron-3.5-lightning:free", KILO_URL, None),
    ("liquid/lfm-2.5-2.6b:free", KILO_URL, None),
    ("kilo-auto/free", KILO_URL, None),
    ("dots-studio/dots-3-note-preview:free", KILO_URL, None),
    ("recursive/flint-v1.0:free", KILO_URL, None),
    ("xingchen-agi/xing4.0-29b-a4b:free", KILO_URL, None),
    ("nvidia/nemotron-3.5-super-vl:free", KILO_URL, None),
    ("reflection/beam-free", KILO_URL, None),
    ("stealth/glyph-cluster", KILO_URL, None),
]

# Chave None = provedor sem chave (anônimo). Chave vazia "" = chave não preenchida.
MODELOS = [m for m in MODELOS if m[2] is None or m[2]]

# LLM7.io: gateway com acesso anônimo (sem chave; key = None).
LLM7_URL = "https://api.llm7.io/v1/chat/completions"

MODELOS += [
    ("minimax-m2.7", LLM7_URL, None),
    ("gpt-oss:20b", LLM7_URL, None),
    ("nemotron-3-nano:30b", LLM7_URL, None),
    ("mistral-Nemo-Instruct-2407", LLM7_URL, None),
]

# ModelScope: endpoint padrão OpenAI (base https://api-inference.modelscope.cn/v1).
MODELSCOPE_URL = "https://api-inference.modelscope.cn/v1/chat/completions"

MODELOS += [
    ("Qwen/Qwen3.5-35B-A3B", MODELSCOPE_URL, CHAVE_MODELSCOPE),
    ("Qwen/Qwen3.5-27B", MODELSCOPE_URL, CHAVE_MODELSCOPE),
]

# NVIDIA NIM: endpoint padrão OpenAI (base https://integrate.api.nvidia.com/v1).
NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

MODELOS += [
    ("nvidia/nemotron-3-ultra-550b-a55b", NVIDIA_URL, CHAVE_NVIDIA),
    ("openai/gpt-oss-20b", NVIDIA_URL, CHAVE_NVIDIA),
    ("google/gemma-4-31b-it", NVIDIA_URL, CHAVE_NVIDIA),
]

# OpenRouter: endpoint padrão OpenAI (base https://openrouter.ai/api/v1).
# O de moderação (content-safety) fica de fora, pois não conversa.
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

MODELOS += [
    ("google/gemma-4-31b-it:free", OPENROUTER_URL, CHAVE_OPENROUTER),
    ("google/gemma-4-26b-a4b-it:free", OPENROUTER_URL, CHAVE_OPENROUTER),
    ("cohere/north-mini-code:free", OPENROUTER_URL, CHAVE_OPENROUTER),
    ("poolside/laguna-s-2.1:free", OPENROUTER_URL, CHAVE_OPENROUTER),
    ("poolside/laguna-xs-2.1:free", OPENROUTER_URL, CHAVE_OPENROUTER),
    ("dots-studio/dots-3-note-preview:free", OPENROUTER_URL, CHAVE_OPENROUTER),
    ("liquid/lfm-2.5-2.6b:free", OPENROUTER_URL, CHAVE_OPENROUTER),
    ("nvidia/nemotron-3.5-lightning:free", OPENROUTER_URL, CHAVE_OPENROUTER),
    ("thinkingmachines/inkling:free", OPENROUTER_URL, CHAVE_OPENROUTER),
    ("nvidia/nemotron-3-ultra-550b-a55b:free", OPENROUTER_URL, CHAVE_OPENROUTER),
    ("recursive/flint-v1.0:free", OPENROUTER_URL, CHAVE_OPENROUTER),
    ("xingchen-agi/xing4.0-29b-a4b:free", OPENROUTER_URL, CHAVE_OPENROUTER),
    ("nvidia/nemotron-3.5-super-vl:free", OPENROUTER_URL, CHAVE_OPENROUTER),
    ("nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free", OPENROUTER_URL, CHAVE_OPENROUTER),
    ("thinkingmachines/inkling-small:free", OPENROUTER_URL, CHAVE_OPENROUTER),
]

# OVHcloud AI Endpoints: acesso anônimo (sem chave; key = None), 2 RPM por IP por modelo.
OVH_URL = "https://oai.endpoints.kepler.ai.cloud.ovh.net/v1/chat/completions"

MODELOS += [
    ("gpt-oss-120b", OVH_URL, None),
    ("gpt-oss-20b", OVH_URL, None),
    ("Qwen3.5-397B-A17B", OVH_URL, None),
    ("Qwen3.6-27B", OVH_URL, None),
    ("Qwen3.8-27B", OVH_URL, None),
    ("Qwen3.5-9B", OVH_URL, None),
    ("Mistral-Nemo-Instruct-2407", OVH_URL, None),
]

# SiliconFlow: endpoint padrão OpenAI (base https://api.siliconflow.cn/v1).
SILICONFLOW_URL = "https://api.siliconflow.cn/v1/chat/completions"

MODELOS += [
    ("tencent/Hunyuan-MT-7B", SILICONFLOW_URL, CHAVE_SILICONFLOW),
    ("XingChenAGI/Xing4.0-29B", SILICONFLOW_URL, CHAVE_SILICONFLOW),
]

# ================= SUPABASE =================
def salvar(usuario: int, msg: str, name: str):
    """usuario: 1 = usuário, 0 = IA. msg: texto. name: nome do usuário ou do modelo."""
    try:
        requests.post(
            f"{SUPABASE_URL}/rest/v1/conversas",
            headers=SUPABASE_HEADERS,
            json={"usuario": usuario, "msg": msg, "name": name},
            timeout=15,
        )
    except requests.RequestException as e:
        print(f"[aviso] não consegui salvar no Supabase: {e}")


# ================= IA =================
def limite_atingido(resp: requests.Response) -> bool:
    """Só é limite de verdade: 429/402, ou 403 com texto de quota/limite."""
    if resp.status_code in (429, 402):
        return True
    if resp.status_code == 403:
        texto = resp.text.lower()
        return any(p in texto for p in ("quota", "rate limit", "exceeded"))
    return False


def cabecalhos(key):
    """Sem chave (None) manda só o Content-Type; com chave, manda o Bearer."""
    h = {"Content-Type": "application/json"}
    if key:
        h["Authorization"] = f"Bearer {key}"
    return h


def chamar_modelo(nome: str, url: str, key: str, historico: list):
    """Retorna (texto, None) em sucesso ou (None, motivo) em falha."""
    try:
        resp = requests.post(
            url,
            headers=cabecalhos(key),
            json={"model": nome, "messages": historico},
            timeout=60,
        )
    except requests.RequestException as e:
        return None, f"erro de conexão: {e}"

    if resp.status_code == 200:
        try:
            return resp.json()["choices"][0]["message"]["content"], None
        except (KeyError, IndexError, ValueError):
            return None, "resposta inesperada"

    if limite_atingido(resp):
        return None, f"limite HTTP {resp.status_code}: {resp.text[:120]}"
    return None, f"erro HTTP {resp.status_code}: {resp.text[:120]}"


# ================= ESCOLHA DE MODELO (/modelo) =================
PREFERIDO = None              # modelo escolhido pelo usuário (None = ordem automática)
ESCOLHAS_PENDENTES = None     # lista de nomes esperando o usuário escolher


def modelos_em_ordem():
    """O modelo escolhido vai primeiro; os outros seguem na ordem normal."""
    if not PREFERIDO:
        return MODELOS
    escolhido = [m for m in MODELOS if m[0] == PREFERIDO]
    return escolhido + [m for m in MODELOS if m[0] != PREFERIDO]


def comando_modelo(entrada: str):
    """Trata /modelo e a escolha pendente. Devolve a mensagem do sistema, ou None se não for para ele."""
    global PREFERIDO, ESCOLHAS_PENDENTES
    texto = entrada.strip()

    if ESCOLHAS_PENDENTES:
        escolha = None
        if texto.isdigit() and 1 <= int(texto) <= len(ESCOLHAS_PENDENTES):
            escolha = ESCOLHAS_PENDENTES[int(texto) - 1]
        else:
            iguais = [n for n in ESCOLHAS_PENDENTES if n.lower() == texto.lower()]
            escolha = iguais[0] if iguais else None
        if escolha:
            PREFERIDO = escolha
            ESCOLHAS_PENDENTES = None
            return f"Modelo escolhido: {PREFERIDO}. Ele vai responder primeiro."
        ESCOLHAS_PENDENTES = None  # o usuário mudou de assunto: cancela a escolha

    if not re.match(r"^/modelo(\s|$)", texto, re.I):
        return None

    termo = texto[len("/modelo"):].strip()
    if not termo:
        PREFERIDO = None
        return "Voltei para a ordem automática dos modelos."

    nomes = list(dict.fromkeys(m[0] for m in MODELOS if termo.lower() in m[0].lower()))
    if not nomes:
        return f"Nenhum modelo tem '{termo}' no nome."
    if len(nomes) == 1:
        PREFERIDO = nomes[0]
        return f"Modelo escolhido: {PREFERIDO}. Ele vai responder primeiro."

    ESCOLHAS_PENDENTES = nomes
    lista = "\n".join(f"{i}) {n}" for i, n in enumerate(nomes, 1))
    return f"Qual? Tem estes modelos com '{termo}':\n{lista}\nQual vocês querem? Responda com o número."


def perguntar(historico: list):
    """Percorre os modelos (o escolhido primeiro) até um responder."""
    lista = modelos_em_ordem()
    total = len(lista)
    for i, (nome, url, key) in enumerate(lista, start=1):
        texto, erro = chamar_modelo(nome, url, key, historico)
        if texto is not None:
            return nome, texto
        if erro.startswith("limite") and i < total:
            proximo = lista[i][0]
            print(f"[{nome}] {erro}")
            print(f"limite de tokens atingido indo para outro modelo: "
                  f"nível:({i + 1}/{total}) nome:({proximo})")
        else:
            print(f"[{nome}] falhou ({erro}), tentando o próximo...")
    return None, None


# ================= AÇÕES DA IA (arquivos) =================
FORMATO_ACOES = """
Você pode mexer nos arquivos da sua pasta usando estes comandos, cada um em sua própria linha:
[LISTAR]
[LER: caminho/arquivo.txt]
[ESCREVER: caminho/arquivo.txt]
conteúdo do arquivo
[/ESCREVER]
[CRIAR_PASTA: nome_da_pasta]
[APAGAR: caminho/arquivo.txt]
Use só caminhos relativos à sua pasta. Para apagar, o usuário precisa confirmar; mesmo assim o arquivo só vai para a lixeira. Ao sobrescrever, uma cópia é guardada. Nunca sobrescreva um arquivo com conteúdo vazio.
Depois de um comando, o resultado chega numa mensagem que começa com RESULTADO. Responda normalmente ao usuário depois disso.
"""

PADRAO_ACOES = re.compile(
    r"\[ESCREVER:\s*(.+?)\]\n(.*?)\n?\[/ESCREVER\]"
    r"|\[LER:\s*(.+?)\]"
    r"|\[LISTAR\]"
    r"|\[CRIAR_PASTA:\s*(.+?)\]"
    r"|\[APAGAR:\s*(.+?)\]",
    re.S,
)


def instrucao() -> str:
    """Mensagem de sistema com a pasta, os arquivos atuais e os comandos disponíveis."""
    atuais = ", ".join(listar_arquivos()) or "(nenhum)"
    return (
        "Você é a UP, uma assistente útil. Responda em português. "
        f"Pasta da IA: {PASTA_IA}. Arquivos atuais: {atuais}.\n" + FORMATO_ACOES
    )


def executar_acoes(texto: str, confirmar=None):
    """Executa os comandos escritos pela IA. Devolve (resultados, texto limpo)."""
    resultados = []
    for m in PADRAO_ACOES.finditer(texto):
        try:
            if m.group(1):
                nome, conteudo = m.group(1).strip(), m.group(2)
                alvo = caminho_seguro(nome)
                if alvo.is_file():
                    if not conteudo.strip():
                        raise PermissionError(f"não vou sobrescrever {nome} com conteúdo vazio")
                    if not (confirmar and confirmar(f"sobrescrever '{nome}' (uma cópia de segurança será guardada)")):
                        raise PermissionError(f"sobrescrever {nome} não foi autorizado pelo usuário")
                    copia = guardar_copia(alvo)
                    resultados.append(f"Cópia de segurança de {nome}: {copia.name}")
                escrever_arquivo(nome, conteudo)
                resultados.append(f"Arquivo salvo: {nome}")
            elif m.group(3):
                nome = m.group(3).strip()
                resultados.append(f"Conteúdo de {nome}:\n{ler_arquivo(nome)[:4000]}")
            elif m.group(0) == "[LISTAR]":
                resultados.append("Arquivos: " + (", ".join(listar_arquivos()) or "(nenhum)"))
            elif m.group(4):
                nome = m.group(4).strip()
                caminho_seguro(nome).mkdir(parents=True, exist_ok=True)
                resultados.append(f"Pasta criada: {nome}")
            elif m.group(5):
                nome = m.group(5).strip()
                if confirmar and confirmar(f"apagar '{nome}'"):
                    alvo = caminho_seguro(nome)
                    if alvo == PASTA_IA:
                        raise PermissionError("não é permitido apagar a pasta inteira")
                    if alvo.exists():
                        mover_para_lixeira(alvo)
                        resultados.append(f"Movido para a lixeira: {nome}")
                else:
                    resultados.append(f"Exclusão de {nome} NÃO autorizada pelo usuário.")
        except Exception as e:
            resultados.append(f"Erro: {e}")
    return resultados, PADRAO_ACOES.sub("", texto).strip()


def conversar(historico: list, confirmar=None, max_rodadas: int = 4):
    """Chama os modelos, executa os comandos de arquivo e devolve o resultado à IA.
    Devolve (nome do modelo, texto final, log das ações). Se nenhum modelo responder,
    devolve (None, None, []) e remove o que foi acrescentado ao histórico."""
    tamanho_inicial = len(historico)
    log = []
    for _ in range(max_rodadas):
        historico[0] = {"role": "system", "content": instrucao()}
        nome, resposta = perguntar(historico)
        if resposta is None:
            del historico[tamanho_inicial:]
            return None, None, []
        historico.append({"role": "assistant", "content": resposta})
        resultados, texto_limpo = executar_acoes(resposta, confirmar)
        if not resultados:
            return nome, texto_limpo, log
        log.extend(resultados)
        historico.append({"role": "user", "content": "RESULTADO:\n" + "\n".join(resultados)})
    return nome, texto_limpo, log


# ================= COMANDOS DO USUÁRIO =================
def tratar_comando(entrada: str) -> bool:
    """Comandos de arquivo digitados pelo usuário. Retorna True se era comando."""
    partes = entrada.split(maxsplit=2)
    cmd = partes[0].lower()

    if cmd == "/arquivos":
        print("\n".join(listar_arquivos()) or "(pasta vazia)")
    elif cmd == "/ler" and len(partes) >= 2:
        print(ler_arquivo(partes[1]))
    elif cmd == "/escrever" and len(partes) == 3:
        escrever_arquivo(partes[1], partes[2])
        print(f"Arquivo salvo: {partes[1]}")
    elif cmd == "/apagar" and len(partes) >= 2:
        apagar_arquivo(partes[1])
    else:
        return False
    return True


# ================= LEITURA DE PASTAS PERMITIDAS (SOMENTE LEITURA) =================
# Pode ler qualquer pasta do aparelho. Nada é gravado nem apagado por este recurso.
# Todo acesso fica registrado em .acessos.log na pasta da IA.
ARQUIVO_LOG_ACESSOS = PASTA_IA / ".acessos.log"
TAMANHO_MAX_LEITURA = 10 * 1024  # 10 KB


# Pseudo-arquivos do sistema: ler trava ou não faz sentido.
PREFIXOS_BLOQUEADOS = ("/proc", "/sys", "/dev")


def pode_ler(caminho: Path) -> bool:
    """Leitura liberada em qualquer pasta do aparelho, exceto pseudo-arquivos do sistema."""
    alvo = caminho.resolve()
    return not any(str(alvo) == p or str(alvo).startswith(p + "/") for p in PREFIXOS_BLOQUEADOS)


def registrar_acesso(caminho: str, acao: str):
    from datetime import datetime
    with open(ARQUIVO_LOG_ACESSOS, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} | {acao} | {caminho}\n")


def listar_pasta_leitura(caminho: str) -> str:
    alvo = Path(caminho).expanduser()
    if not pode_ler(alvo) or not alvo.is_dir():
        registrar_acesso(caminho, "listar_negado")
        return "Acesso negado ou não é uma pasta permitida."
    registrar_acesso(caminho, "listar")
    linhas = []
    for e in sorted(alvo.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
        if e.is_dir():
            linhas.append(f"[pasta] {e.name}")
        else:
            linhas.append(f"[arquivo] {e.name} ({e.stat().st_size // 1024} KB)")
    return f"Conteúdo de {alvo.resolve()}:\n" + ("\n".join(linhas) or "(vazio)")


def ler_arquivo_leitura(caminho: str) -> str:
    alvo = Path(caminho).expanduser()
    if not pode_ler(alvo) or not alvo.is_file():
        registrar_acesso(caminho, "ler_negado")
        return "Acesso negado ou não é um arquivo permitido."
    registrar_acesso(caminho, "ler")
    with open(alvo, "r", encoding="utf-8", errors="ignore") as f:
        conteudo = f.read(TAMANHO_MAX_LEITURA)
    return f"Arquivo: {alvo.name} ({alvo.stat().st_size // 1024} KB)\n\n{conteudo}"


def tratar_leitura(entrada: str):
    """Comandos *ls e *cat (somente leitura). Devolve o texto ou None."""
    if entrada.startswith("*ls "):
        return listar_pasta_leitura(entrada[4:].strip())
    if entrada.startswith("*cat "):
        return ler_arquivo_leitura(entrada[5:].strip())
    return None


# ================= CHAT =================
def confirmar_cli(acao: str) -> bool:
    return input(f"A IA quer {acao}. Permitir? (s/n): ").strip().lower() == "s"


def main():
    if not MODELOS:
        print("Nenhum modelo configurado. Adicione os modelos na lista MODELOS.")
        return

    print(f"Chat iniciado com {len(MODELOS)} modelos. Pasta da IA: {PASTA_IA}")
    print("Comandos: /modelo NOME, /modelo (volta ao automático), /arquivos, /ler NOME, /escrever NOME TEXTO, /apagar NOME, *ls CAMINHO, *cat CAMINHO, sair\n")
    historico = [{"role": "system", "content": instrucao()}]

    while True:
        entrada = input(f"{NOME_USUARIO}: ").strip()
        if not entrada:
            continue
        if entrada.lower() == "sair":
            break

        leitura = tratar_leitura(entrada)
        if leitura is not None:
            print(leitura + "\n")
            continue

        msg_sistema = comando_modelo(entrada)
        if msg_sistema is not None:
            print(f"[sistema] {msg_sistema}\n")
            continue

        try:
            if entrada.startswith("/") and tratar_comando(entrada):
                continue
        except (PermissionError, OSError) as e:
            print(f"[erro] {e}\n")
            continue

        historico.append({"role": "user", "content": entrada})
        salvar(1, entrada, NOME_USUARIO)

        nome, texto, log = conversar(historico, confirmar=confirmar_cli)
        if nome is None:
            print("Nenhum modelo disponível no momento. Tente mais tarde.\n")
            historico.pop()
            continue

        if log:
            print("[ações] " + " | ".join(log))
        salvar(0, texto, nome)
        print(f"{nome}: {texto}\n")


if __name__ == "__main__":
    main()
