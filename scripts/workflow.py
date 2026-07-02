"""
workflow.py — state machine do workflow do mad (v1.3).

O CORAÇÃO do enforcement. Instrução em prosa pra LLM é sugestão; este módulo +
os hooks são garantia. Aqui vivem: os estados, os sub-estados de feature, os
gates (funções PURAS que leem o filesystem e retornam (bool, msg)), a classe
WorkflowState (load/save atômico + lock), a decisão de tool permitida por estado
(usada pelo hook PreToolUse) e o log estruturado de workflow.

Stdlib + _utils apenas. Fail-closed: em dúvida, bloqueia.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _utils as u  # noqa: E402

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
PHASES = ["BOOTSTRAP", "DISCOVERY", "ESPEC_V1", "SETUP_TIME",
          "LOOP_FEATURES", "PRE_RELEASE", "PILOTO"]
# transição linear de fase (PILOTO pode reentrar LOOP_FEATURES em extensão)
NEXT_PHASE = {
    "BOOTSTRAP": "DISCOVERY", "DISCOVERY": "ESPEC_V1", "ESPEC_V1": "SETUP_TIME",
    "SETUP_TIME": "LOOP_FEATURES", "LOOP_FEATURES": "PRE_RELEASE",
    "PRE_RELEASE": "PILOTO", "PILOTO": "LOOP_FEATURES",
}
SUBPHASES = ["spec_pendente", "spec_validada", "executando",
             "validando", "aprovacao_humano", "concluida"]

# --- CAMADA HUMANA: o usuário é leigo. NUNCA mostre os nomes técnicos acima.
# (rótulo curto, o-que-estamos-fazendo em linguagem de gente)
PHASE_HUMAN = {
    "BOOTSTRAP":     ("Preparando", "preparando o terreno do projeto"),
    "DISCOVERY":     ("Entendendo sua ideia", "esclarecer o que você quer: o problema, o objetivo e para quem é"),
    "ESPEC_V1":      ("Definindo o que construir", "transformar a ideia numa lista clara de coisas a fazer"),
    "SETUP_TIME":    ("Montando o time", "escolher quais assistentes vão trabalhar — e conversar sobre o custo disso"),
    "LOOP_FEATURES": ("Construindo", "construir item por item: você acompanha, opina e libera cada passo"),
    "PRE_RELEASE":   ("Testando e validando", "testar e validar tudo antes de considerar pronto"),
    "PILOTO":        ("No ar", "está em uso; ideias novas reiniciam o ciclo"),
}
SUBPHASE_HUMAN = {
    "spec_pendente":    "descrevendo o próximo item a construir",
    "spec_validada":    "esperando você aprovar a descrição do item",
    "executando":       "um assistente está construindo o item",
    "validando":        "conferindo se ficou como você queria",
    "aprovacao_humano": "esperando você aprovar (é algo difícil de desfazer)",
    "concluida":        "item entregue; partindo pro próximo",
}
# pergunta ao usuário SEM jargão (para adoção incerta). Mapeia p/ fase interna.
HUMAN_WHERE_OPTIONS = [
    ("a", "Ainda estou pensando na ideia / no problema.", "DISCOVERY"),
    ("b", "Já sei o que quero; falta detalhar a lista de tarefas.", "ESPEC_V1"),
    ("c", "Já tenho a lista de tarefas; falta montar o time.", "SETUP_TIME"),
    ("d", "Já estou construindo as coisas.", "LOOP_FEATURES"),
]


def human_label(phase: str) -> str:
    return PHASE_HUMAN.get(phase, (phase, ""))[0]


def human_doing(phase: str) -> str:
    return PHASE_HUMAN.get(phase, ("", ""))[1]


# Guia DIDÁTICO do workflow — alimenta o "mapa do workflow" no dashboard.
# Para cada fase: ícone, o-que-acontece, o-que-faz-avançar, e pra-onde-pode-ir
# (ramificações com a CONDIÇÃO anotada). Tudo em linguagem de gente.
PHASE_GUIDE = {
    "BOOTSTRAP": {
        "icon": "🌱",
        "detail": "Arrumando a casa: criando a estrutura do projeto pra tudo começar organizado.",
        "advance": "assim que o preparo termina, partimos pra entender sua ideia.",
        "goes_to": [{"to": "DISCOVERY", "when": "preparo pronto"}],
    },
    "DISCOVERY": {
        "icon": "💡",
        "detail": "Conversamos pra descobrir o que você quer de verdade: o problema, "
                  "para quem é e o que seria sucesso. Nada de código ainda.",
        "advance": "quando a ideia está clara e você confirma, seguimos.",
        "goes_to": [{"to": "ESPEC_V1", "when": "ideia entendida"}],
    },
    "ESPEC_V1": {
        "icon": "📝",
        "detail": "Transformamos a ideia numa lista clara de coisas a construir "
                  "(o que vem primeiro, o que pode esperar).",
        "advance": "com a lista combinada, montamos o time.",
        "goes_to": [{"to": "SETUP_TIME", "when": "lista pronta"}],
    },
    "SETUP_TIME": {
        "icon": "🧑‍🤝‍🧑",
        "detail": "Escolhemos quais assistentes vão trabalhar — e conversamos sobre "
                  "custo e velocidade (mais assistentes/paralelo = mais rápido).",
        "advance": "com o time montado, começamos a construir.",
        "goes_to": [{"to": "LOOP_FEATURES", "when": "time pronto"}],
    },
    "LOOP_FEATURES": {
        "icon": "🔨",
        "detail": "O coração do projeto: cada item da lista vira realidade, um a um. "
                  "Você acompanha ao vivo, opina e libera. Ao terminar um, já começa o próximo.",
        "advance": "quando todos os itens estão prontos, vamos testar e validar.",
        "goes_to": [
            {"to": "LOOP_FEATURES", "when": "ainda há itens → próximo item"},
            {"to": "PRE_RELEASE", "when": "lista concluída"},
        ],
    },
    "PRE_RELEASE": {
        "icon": "🧪",
        "detail": "Conferimos e testamos tudo o que foi feito, e auditamos a coerência "
                  "(a documentação bate com o sistema? — /mad-audit), pra garantir que "
                  "funciona de verdade e está bem documentado antes de valer.",
        "advance": "passando nos testes e na auditoria de coerência, vai pro ar.",
        "goes_to": [
            {"to": "PILOTO", "when": "tudo validado"},
            {"to": "LOOP_FEATURES", "when": "achamos algo pra ajustar → volta a construir"},
        ],
    },
    "PILOTO": {
        "icon": "🚀",
        "detail": "Está no ar, em uso real. Ideias novas viram novos itens e "
                  "reiniciam o ciclo.",
        "advance": "uma ideia nova recomeça o ciclo.",
        "goes_to": [{"to": "DISCOVERY", "when": "nova ideia"}],
    },
}

# Guia do sub-loop de cada item (dentro de "Construindo").
SUBPHASE_GUIDE = [
    {"id": "spec_pendente", "label": "Descrevendo", "icon": "✍️",
     "detail": "O Arquiteto descreve o próximo item a construir."},
    {"id": "spec_validada", "label": "Você aprova", "icon": "👍",
     "detail": "Se o item é arriscado (difícil de desfazer), você confere e aprova. "
               "Itens simples seguem sozinhos."},
    {"id": "executando", "label": "Construindo", "icon": "⚙️",
     "detail": "Um assistente constrói o item enquanto você acompanha ao vivo."},
    {"id": "validando", "label": "Conferindo", "icon": "🔎",
     "detail": "O Arquiteto confere se ficou como combinado."},
    {"id": "concluida", "label": "Entregue", "icon": "✅",
     "detail": "Item entregue. Vai pro próximo — ou de volta a construir se algo faltou."},
]


def phase_guide() -> dict:
    """Fases (nome humano) + guia didático, prontas pro mapa do dashboard."""
    out = []
    for p in PHASES:
        g = PHASE_GUIDE.get(p, {})
        out.append({
            "id": p,
            "label": PHASE_HUMAN.get(p, (p, ""))[0],
            "doing": PHASE_HUMAN.get(p, ("", ""))[1],
            "icon": g.get("icon", "•"),
            "detail": g.get("detail", ""),
            "advance": g.get("advance", ""),
            "goes_to": g.get("goes_to", []),
        })
    return {"phases": out, "subloop": SUBPHASE_GUIDE}


NEXT_SUBPHASE = {
    "spec_pendente": "spec_validada", "spec_validada": "executando",
    "executando": "validando", "validando": "aprovacao_humano",
    "aprovacao_humano": "concluida", "concluida": "spec_pendente",
}
BLAST_REVERSIBLE = ("reversivel_baixo", "reversivel_medio")
STATE_FILE = ".mad/workflow_state.json"
LOCK_FILE = ".mad/workflow_state.lock"


def _hostname() -> str:
    try:
        import socket
        return socket.gethostname()
    except Exception:
        return "?"


def _lock_owner_dead(lock: Path) -> bool:
    """True se o dono do lock claramente morreu (mesmo host + PID inexistente),
    ou se o lock está ilegível/antigo. Conservador entre hosts: não rouba."""
    try:
        info = json.loads(lock.read_text())
    except Exception:
        return True  # formato antigo/corrompido -> pode roubar
    pid, host = info.get("pid"), info.get("host")
    if host and host != _hostname():
        return False  # outro host — não dá pra checar, não rouba
    if not pid:
        return True
    try:
        os.kill(int(pid), 0)
        return False  # processo vivo
    except ProcessLookupError:
        return True   # morto
    except PermissionError:
        return False  # existe (de outro user)
    except Exception:
        return True
LOG_FILE = "logs/workflow.jsonl"

SPEC_REQUIRED_FIELDS = ["objetivo", "critério", "blast", "especialista"]
SECRET_RE = re.compile(
    r"(AKIA[0-9A-Z]{12,}|-----BEGIN[^-]*PRIVATE KEY|ghp_[0-9A-Za-z]{20,}|"
    r"xox[baprs]-[0-9A-Za-z-]{10,}|sk-[0-9A-Za-z]{20,}|"
    r"(password|api[_-]?key|secret|token)\s*[:=]\s*\S{6,})",
    re.IGNORECASE)


# ---------------------------------------------------------------------------
# Log estruturado (append-only, sanitizado, com id único)
# ---------------------------------------------------------------------------
def _sanitize(v):
    if isinstance(v, str):
        v = SECRET_RE.sub("[REDACTED]", v)
        return v if len(v) <= 300 else v[:299] + "…"
    if isinstance(v, dict):
        return {k: _sanitize(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_sanitize(x) for x in v[:50]]
    return v


def _last_log_hash(root: Path) -> str:
    f = root / LOG_FILE
    if not f.is_file():
        return "genesis"
    last = ""
    try:
        for line in u.read_text(f).splitlines():
            if line.strip():
                last = line
    except Exception:
        return "genesis"
    if not last:
        return "genesis"
    try:
        return json.loads(last).get("hash", "genesis")
    except Exception:
        return "genesis"


def log_event(root: Path, event_type: str, **fields) -> dict:
    import hashlib
    ev = {
        "id": uuid.uuid4().hex,
        "ts": u.iso_now(),
        "event": event_type,
        **{k: _sanitize(val) for k, val in fields.items()},
    }
    # cadeia de hash: cada evento amarra o hash do anterior -> log tamper-evident
    ev["prev"] = _last_log_hash(root)
    ev["hash"] = hashlib.sha256(
        json.dumps(ev, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]
    u.append_text(root / LOG_FILE, json.dumps(ev, ensure_ascii=False) + "\n")
    return ev


def verify_log_chain(root: Path) -> tuple[bool, str]:
    """Verifica a integridade da cadeia de hash do audit log."""
    import hashlib
    f = root / LOG_FILE
    if not f.is_file():
        return True, "sem log ainda"
    prev = "genesis"
    n = 0
    for i, line in enumerate(u.read_text(f).splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            return False, f"linha {i} ilegível"
        if "hash" not in ev:  # eventos legados (pré-encadeamento) — tolera
            prev = ev.get("hash", prev)
            continue
        if ev.get("prev") != prev:
            return False, f"cadeia quebrada na linha {i} (evento {ev.get('event')})"
        h = ev.pop("hash")
        calc = hashlib.sha256(
            json.dumps(ev, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]
        if calc != h:
            return False, f"hash adulterado na linha {i} (evento {ev.get('event')})"
        prev = h
        n += 1
    return True, f"{n} eventos íntegros"


# ---------------------------------------------------------------------------
# Gates — funções puras (root: Path) -> (bool, msg)
# ---------------------------------------------------------------------------
def _decisoes_count(root: Path) -> int:
    f = root / "docs" / "DECISOES.md"
    if not f.is_file():
        return 0
    return len(re.findall(r"(?m)^##\s+\d{4}-\d{2}-\d{2}", u.read_text(f)))


def gate_bootstrap_done(root: Path):
    need = [root / u.CONFIG_FILENAME, root / "docs",
            root / "memory" / "arquiteto" / "identity.md", root / STATE_FILE]
    missing = [str(p.relative_to(root)) for p in need if not p.exists()]
    if missing:
        return False, "Falta: " + ", ".join(missing)
    return True, ""


def gate_discovery_done(root: Path):
    obj = root / "docs" / "00_OBJETIVO.md"
    chars = len(u.read_text(obj)) if obj.is_file() else 0
    dc = _decisoes_count(root)
    if chars < 200:
        return False, f"docs/00_OBJETIVO.md precisa de >200 chars (tem {chars})."
    if dc < 3:
        return False, f"docs/DECISOES.md precisa de ≥3 decisões (tem {dc})."
    return True, ""


def gate_espec_done(root: Path):
    bl = root / "docs" / "BACKLOG_V1.md"
    if not bl.is_file():
        return False, "Falta docs/BACKLOG_V1.md."
    feats = parse_backlog(root)
    if not feats:
        return False, "BACKLOG_V1.md sem features no formato F-NNN."
    # DAG: dependências devem existir e não formar ciclo
    ids = {f["id"] for f in feats}
    for f in feats:
        missing = [d for d in (f.get("depends_on") or []) if d not in ids]
        if missing:
            return False, f"{f['id']} depende de feature inexistente: {', '.join(missing)}."
    cyc = has_cycle(feats)
    if cyc:
        return False, f"dependências formam um ciclo: {cyc}. Quebre o ciclo no backlog."
    return True, ""


def gate_setup_done(root: Path):
    ad = root / ".claude" / "agents"
    roles = [p.stem for p in ad.glob("*.md")] if ad.is_dir() else []
    others = [r for r in roles if r != "arquiteto"]
    if not others:
        return False, "Nenhum especialista além do arquiteto. Rode /mad-enable <role>."
    for r in others:
        if not (root / "memory" / r / "identity.md").is_file():
            return False, f"memory/{r}/identity.md ausente."
    return True, ""


def _spec_path(root: Path, nnn: str) -> Path | None:
    num = nnn.replace("F-", "").lstrip("0").zfill(3)
    hits = list((root / "specs").glob(f"feature-{num}-*.md")) if (root / "specs").is_dir() else []
    return hits[0] if hits else None


def gate_spec_written(root: Path, nnn: str):
    sp = _spec_path(root, nnn)
    if sp is None:
        return False, f"specs/feature-{nnn}-*.md não existe."
    text = u.read_text(sp).lower()
    miss = [f for f in SPEC_REQUIRED_FIELDS if f not in text]
    if miss:
        return False, f"Spec {nnn} sem campos: {', '.join(miss)}."
    return True, ""


def _log_has(root: Path, event: str, feature: str) -> bool:
    f = root / LOG_FILE
    if not f.is_file():
        return False
    for line in u.read_text(f).splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("event") == event and ev.get("feature") == feature and ev.get("by") == "human":
            return True
    return False


def gate_human_approve_spec(root: Path, nnn: str):
    if _log_has(root, "approve_spec", nnn):
        return True, ""
    return False, f"Spec {nnn} não aprovada. Rode /mad-phase approve-spec {nnn}."


def gate_execution_done(root: Path, nnn: str, agent: str = ""):
    rd = root / "reports" / f"feature-{nnn.replace('F-', '').lstrip('0').zfill(3)}"
    reports = list(rd.glob("*.md")) if rd.is_dir() else []
    if not reports:
        return False, f"Sem report em reports/feature-{nnn}/."
    return True, ""


def gate_arquiteto_validated(root: Path, nnn: str):
    num = nnn.replace("F-", "").lstrip("0").zfill(3)
    m = root / "reports" / f"feature-{num}" / "arquiteto-merge.md"
    if not m.is_file():
        return False, f"Falta reports/feature-{num}/arquiteto-merge.md."
    text = u.read_text(m)
    checked = re.findall(r"- \[[xX]\]", text)
    unchecked = re.findall(r"- \[ \]", text)
    if not checked:
        return False, "arquiteto-merge.md sem NENHUM critério marcado [x]."
    if unchecked and "WAIVER:" not in text.upper():
        return False, (f"{len(unchecked)} critério(s) ainda [ ] (não atendidos). "
                       f"Atenda-os, ou justifique com uma linha 'WAIVER: <motivo>'. "
                       f"Feature não fecha com critério de aceite em aberto (Art. 4).")
    return True, ""


def gate_docs_synced(root: Path, nnn: str):
    """Constituição Art. 1: feature não fecha sem spec+docs espelhando o código."""
    num = nnn.replace("F-", "").lstrip("0").zfill(3)
    f = root / "reports" / f"feature-{num}" / "docs-sync.md"
    if not f.is_file():
        return False, (
            f"Falta reports/feature-{num}/docs-sync.md. A feature NÃO fecha sem "
            f"provar que spec e docs espelham o código (Constituição, Art. 1). "
            f"O registro precisa de 3 seções: (1) spec as-built atualizada; "
            f"(2) docs vivos atualizados (ou 'nenhum afetado'); (3) a decisão real.")
    t = u.read_text(f).lower()
    checks = [(("as-built" in t) or ("as build" in t) or ("spec" in t), "seção da spec as-built"),
              ("doc" in t, "seção de docs vivos"),
              ("decis" in t, "seção de decisão")]
    missing = [d for ok, d in checks if not ok]
    if missing:
        return False, "docs-sync.md incompleto: falta " + ", ".join(missing) + "."
    if len(t.strip()) < 120:
        return False, "docs-sync.md muito curto — descreva de verdade o que foi sincronizado."
    return True, ""


def gate_tests_green(root: Path, nnn: str):
    """Teste é ground-truth executável. Se [verify].test_cmd está setado, a
    feature não fecha sem verify.json com all_passed=true."""
    cfg = u.load_config(root).get("verify", {})
    if not str(cfg.get("test_cmd", "") or "").strip() \
       and not str(cfg.get("lint_cmd", "") or "").strip() \
       and not str(cfg.get("typecheck_cmd", "") or "").strip():
        return True, ""  # nada configurado -> nada a rodar (projeto sem testes ainda)
    num = nnn.replace("F-", "").lstrip("0").zfill(3)
    vj = u.read_json(root / "reports" / f"feature-{num}" / "verify.json", None)
    if not isinstance(vj, dict):
        return False, ("Falta reports/feature-{}/verify.json — rode /mad-verify {} "
                       "(teste real, não prosa).".format(num, nnn))
    if vj.get("all_passed") is not True:
        fails = [r.get("name") for r in vj.get("results", []) if not r.get("passed")]
        return False, f"verificação falhou em: {', '.join(fails) or '?'}. Corrija e re-rode /mad-verify."
    return True, ""


def gate_independent_review(root: Path, nnn: str):
    """Autor != verificador. Uma feature não fecha sem VEREDITO de aprovação de um
    agente DIFERENTE do que a construiu (separação de deveres)."""
    cfg = u.load_config(root).get("verify", {})
    if not cfg.get("require_independent_review", True):
        return True, ""
    st = WorkflowState.load(root)
    author = (st.feature or {}).get("agent_assigned", "")
    num = nnn.replace("F-", "").lstrip("0").zfill(3)
    rdir = root / "reports" / f"feature-{num}"
    if not rdir.is_dir():
        return False, f"Sem reports/feature-{num}/ — falta a revisão independente."
    for md in rdir.glob("*.md"):
        reviewer = md.stem
        if reviewer in ("arquiteto-merge", "docs-sync") or reviewer == author:
            continue
        t = u.read_text(md)
        if re.search(r"VEREDITO:\s*aprovar", t, re.IGNORECASE):
            return True, ""
    rev = cfg.get("independent_reviewer", "qa-tester")
    return False, (f"Falta revisão independente: um agente != {author or 'autor'} "
                   f"(ex.: {rev}) precisa escrever reports/feature-{num}/<agente>.md "
                   f"com uma linha 'VEREDITO: aprovar'. Autor não valida o próprio trabalho.")


def gate_human_approve_merge(root: Path, nnn: str):
    if _log_has(root, "approve_merge", nnn):
        return True, ""
    return False, f"Merge {nnn} não aprovado. Rode /mad-phase approve-merge {nnn}."


def gate_feature_closed(root: Path, nnn: str):
    ok, _ = gate_arquiteto_validated(root, nnn)
    return (ok, "" if ok else f"Feature {nnn} ainda não validada.")


def gate_pre_release_ready(root: Path):
    st = WorkflowState.load(root)
    pend = [f for f in st.data.get("backlog_features", []) if f.get("status") != "concluida"]
    if pend:
        return False, f"{len(pend)} feature(s) do backlog não concluídas."
    return True, ""


def gate_pilot_ready(root: Path):
    f = root / "reports" / "backtesting" / "v1.md"
    if not f.is_file():
        return False, "Falta reports/backtesting/v1.md."
    # CONSTITUIÇÃO Art. 1: não vai ao ar sem auditoria de coerência (doc↔código).
    ad = root / "reports" / "audits"
    audits = list(ad.glob("*.md")) if ad.is_dir() else []
    if not audits:
        return False, ("Falta a auditoria de coerência. Rode /mad-audit e gere "
                       "reports/audits/<data>-coerencia.md antes de ir ao ar (Art. 1).")
    return True, ""


PHASE_GATES = {
    "BOOTSTRAP": gate_bootstrap_done,
    "DISCOVERY": gate_discovery_done,
    "ESPEC_V1": gate_espec_done,
    "SETUP_TIME": gate_setup_done,
    "LOOP_FEATURES": gate_pre_release_ready,
    "PRE_RELEASE": gate_pilot_ready,
}


# ---------------------------------------------------------------------------
# WorkflowState
# ---------------------------------------------------------------------------
def initial_state(project_name: str) -> dict:
    return {
        "version": "1.0",
        "project_name": project_name,
        "current_phase": "BOOTSTRAP",
        "phase_entered_at": u.iso_now(),
        "phase_transitions": [],
        "active_feature": None,
        "active_features": [],   # engine="dag": features rodando em paralelo
        "backlog_features": [],
        "team_enabled": [],
        "last_hook_event": None,
        "warnings": [],
    }


class WorkflowState:
    def __init__(self, root: Path, data: dict):
        self.root = root
        self.data = data

    # ---- load / save (atômico + lock) ----
    @classmethod
    def path(cls, root: Path) -> Path:
        return root / STATE_FILE

    @classmethod
    def exists(cls, root: Path) -> bool:
        return cls.path(root).is_file()

    @classmethod
    def load(cls, root: Path) -> "WorkflowState":
        data = u.read_json(cls.path(root), None)
        if not isinstance(data, dict) or data.get("current_phase") not in PHASES:
            # auto-recuperação: tenta o backup antes de desistir
            bak = cls.path(root).parent / (cls.path(root).name + ".bak")
            bdata = u.read_json(bak, None)
            if isinstance(bdata, dict) and bdata.get("current_phase") in PHASES:
                return cls(root, bdata)
            raise ValueError("workflow_state.json ausente ou corrompido "
                             "(e sem .bak válido). Rode /mad-doctor.")
        return cls(root, data)

    def _acquire_lock(self, timeout: float = 60.0):
        lock = self.root / LOCK_FILE
        lock.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + timeout
        while True:
            try:
                fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, json.dumps({"pid": os.getpid(),
                                         "host": _hostname(),
                                         "ts": u.iso_now()}).encode())
                os.close(fd)
                return lock
            except FileExistsError:
                # só rouba o lock se o DONO morreu (não por tempo cego).
                if _lock_owner_dead(lock):
                    try:
                        lock.unlink()
                    except OSError:
                        pass
                    continue
                if time.monotonic() > deadline:
                    # dono vivo mas preso além do timeout — desiste, não corrompe.
                    raise RuntimeError(
                        "workflow_state.lock preso por processo vivo "
                        f"({u.read_text(lock)[:120] if lock.exists() else '?'}). "
                        "Se travou de vez: /mad-doctor.")
                time.sleep(0.05)

    def save(self):
        assert self.data["current_phase"] in PHASES
        lock = self._acquire_lock()
        try:
            p = self.path(self.root)
            if p.is_file():  # rotaciona backup antes de sobrescrever
                try:
                    (p.parent / (p.name + ".bak")).write_bytes(p.read_bytes())
                except OSError:
                    pass
            u.write_json(p, self.data)
        finally:
            try:
                lock.unlink()
            except OSError:
                pass

    # ---- consultas ----
    @property
    def phase(self) -> str:
        return self.data["current_phase"]

    @property
    def feature(self) -> dict | None:
        return self.data.get("active_feature")

    @property
    def subphase(self) -> str | None:
        f = self.feature
        return f.get("subphase") if f else None

    # ---- motor: sequential (default) | dag (paralelo) ----
    @property
    def engine(self) -> str:
        return str(u.load_config(self.root).get("workflow", {})
                   .get("engine", "sequential")).lower()

    @property
    def max_parallel(self) -> int:
        return int(u.load_config(self.root).get("workflow", {})
                   .get("max_parallel_features", 3) or 3)

    def active_list(self) -> list:
        """Features ativas: em dag, a lista paralela; em sequential, a única (compat)."""
        if self.engine == "dag":
            return self.data.get("active_features", []) or []
        f = self.feature
        return [f] if f else []

    def feature_by_id(self, fid: str) -> dict | None:
        fid = fid if fid.startswith("F-") else "F-" + fid.zfill(3)
        for f in self.active_list():
            if f.get("id") == fid:
                return f
        return None

    def _new_substate(self, f: dict) -> dict:
        return {
            "id": f["id"], "slug": f.get("slug", ""),
            "subphase": "spec_pendente", "subphase_entered_at": u.iso_now(),
            "spec_path": None, "report_path": None,
            "agent_assigned": f.get("agent", "") or f.get("agent_assigned", ""),
            "blast_radius": f.get("blast_radius", "reversivel_baixo"),
            "touches": f.get("touches", []),
            "approvals": {"spec_approved_by_human": False, "spec_approved_at": None,
                          "merge_approved_by_human": False, "merge_approved_at": None},
            "subphase_transitions": [],
        }

    # ---- decisão de tool (usada pelo hook PreToolUse) ----
    def decide_tool(self, tool_name: str, tool_input: dict) -> tuple[bool, str, str]:
        """Retorna (allow, reason, suggestion). Fail-closed em dúvida controlada."""
        phase = self.phase
        cmd = ""
        if tool_name == "Bash":
            cmd = (tool_input or {}).get("command", "")

        # guardrail catastrófico sempre (independe de fase)
        if tool_name == "Bash" and _is_catastrophic(cmd):
            if not (self.subphase == "concluida"):
                return (False, "Ação irreversível/catastrófica detectada.",
                        "Requer aprovação humana: /mad-phase approve-merge <NNN>.")

        agent_tools = ("Agent", "Task")

        if phase in ("BOOTSTRAP", "DISCOVERY", "ESPEC_V1", "SETUP_TIME"):
            if tool_name in agent_tools:
                return (False, f"Em {phase} não se despacha especialista.",
                        f"Próximo: {self.next_action()}")
            if tool_name == "Bash" and re.search(r"\bgit\s+push\b", cmd):
                return (False, f"Em {phase} não há o que publicar.", "Avance as fases antes.")
            return (True, "", "")

        if phase == "PRE_RELEASE":
            if tool_name in agent_tools:
                return (False, "Loop pausado para validação (PRE_RELEASE).",
                        "Conclua o backtesting.")
            return (True, "", "")

        if phase == "PILOTO":
            return (True, "", "")

        # LOOP_FEATURES — depende da sub-fase
        if self.engine == "dag":
            return self._dag_decide(tool_name, tool_input)
        sp = self.subphase
        assigned = (self.feature or {}).get("agent_assigned", "")
        if tool_name in agent_tools:
            if sp is None:
                return (False, "Nenhuma feature ativa no loop.",
                        "Ative uma: /mad-phase activate <F-NNN> (ou /mad-phase next).")
            if sp == "spec_pendente":
                return (False, "Sem spec de feature ativa.",
                        "Escreva specs/feature-NNN.md primeiro.")
            if sp == "spec_validada":
                nnn = (self.feature or {}).get("id", "NNN")
                return (False, "Spec aguardando aprovação humana.",
                        f"Rode /mad-phase approve-spec {nnn}.")
            if sp == "executando":
                stype = (tool_input or {}).get("subagent_type", "")
                want = f"mad:{assigned}"
                if assigned and stype and stype not in (want, assigned):
                    return (False, f"A spec atribui a feature a '{assigned}', não a '{stype}'.",
                            f"Chame subagent_type={want} ou ajuste a spec.")
                return (True, "", "")
            if sp in ("validando", "aprovacao_humano"):
                return (False, "Feature já entregue; em validação/aprovação.",
                        "Marque critérios em arquiteto-merge.md.")
        # writes durante aprovacao_humano
        if sp == "aprovacao_humano" and tool_name in ("Write", "Edit", "MultiEdit"):
            nnn = (self.feature or {}).get("id", "NNN")
            return (False, "Aguardando aprovação humana de merge.",
                    f"Rode /mad-phase approve-merge {nnn}.")
        return (True, "", "")

    def _dag_decide(self, tool_name: str, tool_input: dict) -> tuple[bool, str, str]:
        """Enforcement paralelo: libera o especialista de QUALQUER feature ativa em
        'executando'; bloqueia despacho quando nenhuma está pronta pra construir."""
        active = self.active_list()
        if tool_name in ("Agent", "Task"):
            if not active:
                return (False, "Nenhuma feature ativa no loop.",
                        "Rode /mad-phase next para ativar a fronteira.")
            execing = [f for f in active if f.get("subphase") == "executando"]
            if not execing:
                pend = ", ".join(f["id"] for f in active
                                 if f.get("subphase") in ("spec_pendente", "spec_validada"))
                return (False, "Nenhuma feature em construção ainda.",
                        f"Escreva/aprove a spec das ativas ({pend}) — /mad-phase next <F-NNN>.")
            role = (tool_input or {}).get("subagent_type", "").replace("mad:", "")
            if not role:
                return (True, "", "")  # sem tipo declarado — o Arquiteto sabe qual feature
            if any(f.get("agent_assigned", "") == role for f in execing):
                return (True, "", "")
            alvos = ", ".join(f"{f['id']}→{f.get('agent_assigned')}" for f in execing)
            return (False, f"Nenhuma feature em construção atribuída a '{role}'.",
                    f"Em construção agora: {alvos}.")
        # escritas: o escopo por-feature é do hook write-scope; aqui libera.
        return (True, "", "")

    def next_action(self) -> str:
        phase = self.phase
        nexts = {
            "BOOTSTRAP": "Rode /mad-init para criar a estrutura.",
            "DISCOVERY": "Conduza a discovery: preencha docs/00_OBJETIVO.md e registre ≥3 decisões em docs/DECISOES.md. Depois /mad-phase next.",
            "ESPEC_V1": "Escreva docs/BACKLOG_V1.md com features F-001..F-NNN (objetivo + critério de aceite cada). Depois /mad-phase next.",
            "SETUP_TIME": "Habilite ≥1 especialista com /mad-enable <role>. Depois /mad-phase next.",
            "PRE_RELEASE": "Rode o backtesting e gere reports/backtesting/v1.md. Depois /mad-phase next-phase.",
            "PILOTO": "Projeto em piloto. Novas features reentram em LOOP_FEATURES.",
        }
        if phase != "LOOP_FEATURES":
            return nexts.get(phase, "Consulte /mad-phase status.")
        sp = self.subphase
        f = self.feature or {}
        nnn = f.get("id", "F-NNN")
        agent = f.get("agent_assigned", "<especialista>")
        return {
            None: "Ative a próxima feature do backlog: /mad-phase activate <F-NNN>.",
            "spec_pendente": f"Escreva specs/feature-{nnn}-*.md (objetivo, inputs, outputs, critérios, blast_radius, especialista).",
            "spec_validada": f"Aguardando o humano: /mad-phase approve-spec {nnn}.",
            "executando": f"Chame o Agent tool com subagent_type=mad:{agent}, referenciando a spec, exigindo decanting.",
            "validando": f"Leia o report e marque os critérios em reports/feature-{nnn}/arquiteto-merge.md. Depois /mad-phase next (ou rework).",
            "aprovacao_humano": f"Aguardando o humano: /mad-phase approve-merge {nnn}.",
            "concluida": "Feature concluída. Ative a próxima.",
        }.get(sp, "Consulte /mad-phase status.")

    def allowed_summary(self) -> tuple[list[str], list[str]]:
        """(permitidas, bloqueadas) em linguagem natural, para o SessionStart."""
        phase = self.phase
        if phase in ("BOOTSTRAP", "DISCOVERY", "ESPEC_V1", "SETUP_TIME"):
            return (["Read", "Write em docs/ e memory/", "comandos /mad-*"],
                    ["Agent tool (não há despacho nesta fase)", "git push"])
        if phase == "PRE_RELEASE":
            return (["Read", "scripts de eval/backtesting"], ["Agent tool", "git push --force"])
        if phase == "PILOTO":
            return (["tudo com guardrails padrão"], ["git push --force main"])
        sp = self.subphase
        agent = (self.feature or {}).get("agent_assigned", "<especialista>")
        table = {
            "spec_pendente": (["Write em specs/feature-NNN.md", "Read"],
                              ["Agent tool", "escrita fora de specs/"]),
            "spec_validada": (["Read", "mostrar a spec ao humano"],
                              ["Agent tool até /mad-phase approve-spec"]),
            "executando": ([f"Agent tool com subagent_type=mad:{agent}", "Write em reports/ e memory/"],
                           ["Agent com outro especialista", "escrita fora dos paths da spec"]),
            "validando": (["Read", "Write em reports/feature-NNN/arquiteto-merge.md"],
                          ["Agent tool", "git commit"]),
            "aprovacao_humano": (["apenas Read"], ["toda escrita até /mad-phase approve-merge"]),
            "concluida": (["Write em trust.json, DECISOES.md, backlog"], []),
        }
        return table.get(sp, (["Read"], []))

    # ---- transições ----
    def gate_for_phase(self):
        return PHASE_GATES.get(self.phase)

    def can_advance_phase(self) -> tuple[bool, str]:
        g = self.gate_for_phase()
        if g is None:
            return False, "Fase final; sem transição automática."
        return g(self.root)

    def advance_phase(self, by: str = "human") -> tuple[bool, str]:
        ok, msg = self.can_advance_phase()
        if not ok:
            log_event(self.root, "gate_check_failed", phase=self.phase, reason=msg)
            return False, msg
        target = NEXT_PHASE[self.phase]
        # ao sair de ESPEC_V1, popula backlog_features do BACKLOG_V1.md
        if self.phase == "ESPEC_V1" and not self.data.get("backlog_features"):
            self.data["backlog_features"] = parse_backlog(self.root)
        self.data["phase_transitions"].append({
            "from": self.phase, "to": target, "at": u.iso_now(),
            "by": by, "gates_checked": [self.gate_for_phase().__name__],
        })
        self.data["current_phase"] = target
        self.data["phase_entered_at"] = u.iso_now()
        if target == "LOOP_FEATURES" and self.data.get("active_feature") is None:
            self._activate_next_from_backlog()
        self.save()
        log_event(self.root, "transition_phase", **{"from": self.data["phase_transitions"][-1]["from"],
                                                     "to": target, "by": by})
        return True, target

    def _dag_refresh(self):
        """engine=dag: ativa a fronteira paralela (deps ok + paths disjuntos, também
        contra as já ativas) até max_parallel. active_feature espelha a 1ª (compat UI)."""
        backlog = self.data.get("backlog_features", [])
        active = self.data.setdefault("active_features", [])
        active_touches = [a.get("touches", []) for a in active]
        for f in parallel_frontier(backlog, self.max_parallel):
            if len(active) >= self.max_parallel:
                break
            if any(a["id"] == f["id"] for a in active):
                continue
            if any(_touches_overlap(f.get("touches", []), t) for t in active_touches):
                continue
            active.append(self._new_substate(f))
            active_touches.append(f.get("touches", []))
            for bf in backlog:
                if bf["id"] == f["id"]:
                    bf["status"] = "em_andamento"
        self.data["active_feature"] = active[0] if active else None

    def _activate_next_from_backlog(self):
        if self.engine == "dag":
            self._dag_refresh()
            return
        for f in self.data.get("backlog_features", []):
            if f.get("status") == "pendente":
                self.data["active_feature"] = {
                    "id": f["id"], "slug": f.get("slug", ""),
                    "subphase": "spec_pendente", "subphase_entered_at": u.iso_now(),
                    "spec_path": None, "report_path": None,
                    "agent_assigned": f.get("agent", ""),
                    "blast_radius": f.get("blast_radius", "reversivel_baixo"),
                    "approvals": {"spec_approved_by_human": False, "spec_approved_at": None,
                                  "merge_approved_by_human": False, "merge_approved_at": None},
                    "subphase_transitions": [],
                }
                f["status"] = "em_andamento"
                return

    def set_subphase(self, target: str, by: str, fid: str | None = None):
        # em dag, opera na feature indicada (ou na 1ª ativa); mantém active_feature em sincronia
        f = self.feature_by_id(fid) if (fid and self.engine == "dag") else self.data.get("active_feature")
        if not f:
            return
        f["subphase_transitions"].append({
            "from": f["subphase"], "to": target, "at": u.iso_now(), "by": by,
        })
        f["subphase"] = target
        f["subphase_entered_at"] = u.iso_now()
        if self.engine == "dag":  # active_feature reflete a feature recém-operada (compat UI)
            self.data["active_feature"] = f
        self.save()
        log_event(self.root, "transition_subphase", feature=f["id"],
                  **{"from": f["subphase_transitions"][-1]["from"], "to": target, "by": by})


def parse_backlog(root: Path) -> list[dict]:
    """Extrai features de docs/BACKLOG_V1.md, com dependências (DAG).

    Uma feature é uma linha que COMEÇA com F-NNN (após #, -, * ou espaço) — assim
    menção inline (ex.: 'Depende: F-002') não vira feature fantasma. Dependências
    saem de uma linha 'Depende:/Deps:' no bloco da feature (retrocompatível: sem
    essa linha, sem dependências)."""
    bl = root / "docs" / "BACKLOG_V1.md"
    if not bl.is_file():
        return []
    text = u.read_text(bl)
    matches = list(re.finditer(r"(?m)^[#\-*\s]*\bF-(\d{3})\b\s*[—:\-]?\s*([^\n]*)", text))
    out, seen = [], set()
    for i, m in enumerate(matches):
        fid = "F-" + m.group(1)
        if fid in seen:
            continue
        seen.add(fid)
        slug = re.sub(r"[^a-z0-9]+", "-", m.group(2).strip().lower()).strip("-")[:40] or "feature"
        block = text[m.end():(matches[i + 1].start() if i + 1 < len(matches) else len(text))]
        deps = []
        dm = re.search(r"(?im)^[#\-*\s]*(?:depende|deps|depends?)\s*:?\**\s*(.+)$", block)
        if dm:
            deps = [d for d in re.findall(r"F-\d{3}", dm.group(1)) if d != fid]
        touches = []
        tm = re.search(r"(?im)^[#\-*\s]*(?:toca|touches?|paths?|arquivos?)\s*:?\**\s*(.+)$", block)
        if tm:
            touches = [t.strip() for t in re.split(r"[,\s]+", tm.group(1).strip()) if t.strip()]
        out.append({"id": fid, "slug": slug, "status": "pendente",
                    "concluded_at": None, "depends_on": deps, "touches": touches})
    return out


def _touches_overlap(a: list, b: list) -> bool:
    """Duas features colidem se declaram paths que se sobrepõem (prefixo comum).
    Sem 'touches' declarado (lista vazia) = assume que PODE colidir (conservador)."""
    if not a or not b:
        return True  # sem declaração -> não arrisca paralelizar
    for pa in a:
        for pb in b:
            if pa == pb or pa.startswith(pb) or pb.startswith(pa):
                return True
    return False


def parallel_frontier(features: list[dict], max_parallel: int = 3) -> list[dict]:
    """Fronteira SEGURA pra rodar em paralelo: features prontas (deps concluídas) e
    com paths mutuamente disjuntos, até max_parallel. Greedy por ordem do backlog."""
    frontier = []
    for f in ready_features(features):
        if len(frontier) >= max_parallel:
            break
        if all(not _touches_overlap(f.get("touches", []), g.get("touches", []))
               for g in frontier):
            frontier.append(f)
    return frontier


def has_cycle(features: list[dict]) -> str | None:
    """Retorna descrição do 1º ciclo achado no DAG de dependências, ou None."""
    graph = {f["id"]: list(f.get("depends_on", []) or []) for f in features}
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {k: WHITE for k in graph}

    def dfs(node, stack):
        color[node] = GRAY
        for dep in graph.get(node, []):
            if dep not in graph:
                continue  # dependência inexistente — tratada em gate_espec
            if color[dep] == GRAY:
                return " → ".join(stack + [dep])
            if color[dep] == WHITE:
                r = dfs(dep, stack + [dep])
                if r:
                    return r
        color[node] = BLACK
        return None

    for n in graph:
        if color[n] == WHITE:
            r = dfs(n, [n])
            if r:
                return r
    return None


def ready_features(features: list[dict]) -> list[dict]:
    """Fronteira: features pendentes cujas dependências estão todas concluídas."""
    done = {f["id"] for f in features if f.get("status") == "concluida"}
    return [f for f in features
            if f.get("status") == "pendente"
            and all(d in done for d in (f.get("depends_on") or []))]


def _is_catastrophic(cmd: str) -> bool:
    if not cmd:
        return False
    pats = [r"git\s+push\s+.*--force.*\b(main|master)\b",
            r"terraform\s+destroy", r"aws\s+.*\b(delete|rm)\b",
            r"psql.*drop", r"rm\s+-rf\s+.*(memory|docs|specs|reports)"]
    return any(re.search(p, cmd) for p in pats)


# ---------------------------------------------------------------------------
# helper para hooks: carregar estado a partir de um cwd
# ---------------------------------------------------------------------------
def find_root(start: Path | None = None) -> Path | None:
    cur = (start or Path.cwd()).resolve()
    for c in [cur, *cur.parents]:
        if (c / STATE_FILE).is_file() or (c / u.CONFIG_FILENAME).is_file():
            return c
    return None
