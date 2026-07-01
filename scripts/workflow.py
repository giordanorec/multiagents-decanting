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
NEXT_SUBPHASE = {
    "spec_pendente": "spec_validada", "spec_validada": "executando",
    "executando": "validando", "validando": "aprovacao_humano",
    "aprovacao_humano": "concluida", "concluida": "spec_pendente",
}
BLAST_REVERSIBLE = ("reversivel_baixo", "reversivel_medio")
STATE_FILE = ".mad/workflow_state.json"
LOCK_FILE = ".mad/workflow_state.lock"
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


def log_event(root: Path, event_type: str, **fields) -> dict:
    ev = {
        "id": uuid.uuid4().hex,
        "ts": u.iso_now(),
        "event": event_type,
        **{k: _sanitize(val) for k, val in fields.items()},
    }
    u.append_text(root / LOG_FILE, json.dumps(ev, ensure_ascii=False) + "\n")
    return ev


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
    feats = re.findall(r"(?m)^.*\bF-\d{3}\b.*$", u.read_text(bl))
    if not feats:
        return False, "BACKLOG_V1.md sem features no formato F-NNN."
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
    if not re.search(r"- \[[x ]\]", text):
        return False, "arquiteto-merge.md sem critérios marcados [x]/[ ]."
    return True, ""


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
            raise ValueError("workflow_state.json ausente ou corrompido")
        return cls(root, data)

    def _acquire_lock(self, timeout: float = 60.0):
        lock = self.root / LOCK_FILE
        lock.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + timeout
        while True:
            try:
                fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(fd)
                return lock
            except FileExistsError:
                if time.monotonic() > deadline:
                    try:
                        lock.unlink()  # lock velho, força
                    except OSError:
                        pass
                    continue
                time.sleep(0.05)

    def save(self):
        assert self.data["current_phase"] in PHASES
        lock = self._acquire_lock()
        try:
            u.write_json(self.path(self.root), self.data)
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

    def _activate_next_from_backlog(self):
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

    def set_subphase(self, target: str, by: str):
        f = self.data.get("active_feature")
        if not f:
            return
        f["subphase_transitions"].append({
            "from": f["subphase"], "to": target, "at": u.iso_now(), "by": by,
        })
        f["subphase"] = target
        f["subphase_entered_at"] = u.iso_now()
        self.save()
        log_event(self.root, "transition_subphase", feature=f["id"],
                  **{"from": f["subphase_transitions"][-1]["from"], "to": target, "by": by})


def parse_backlog(root: Path) -> list[dict]:
    """Extrai features F-NNN — <slug> de docs/BACKLOG_V1.md para o estado."""
    bl = root / "docs" / "BACKLOG_V1.md"
    if not bl.is_file():
        return []
    out, seen = [], set()
    for m in re.finditer(r"\bF-(\d{3})\b\s*[—:\-]?\s*([^\n]*)", u.read_text(bl)):
        fid = "F-" + m.group(1)
        if fid in seen:
            continue
        seen.add(fid)
        slug = re.sub(r"[^a-z0-9]+", "-", m.group(2).strip().lower()).strip("-")[:40] or "feature"
        out.append({"id": fid, "slug": slug, "status": "pendente", "concluded_at": None})
    return out


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
