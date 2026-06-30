"""
notify.py — notificações opt-in (Telegram, Slack) via stdlib (urllib).

Tier 3 (CA-302/304). Best-effort: se não houver canal configurado ou token, faz
nada e avisa — nunca derruba o fluxo. Config em multiagents-decanting.toml [notify]
ou via env vars. WhatsApp Business API (CA-303) fica como stub documentado (exige
conta/credencial de Business; não há caminho stdlib trivial).

Config (toml [notify] ou env):
  telegram_bot_token / TELEGRAM_BOT_TOKEN
  telegram_chat_id   / TELEGRAM_CHAT_ID
  slack_webhook_url  / SLACK_WEBHOOK_URL
  enabled = true|false

Uso: python scripts/mad.py notify "feature-007 concluída por pipeline-dev"
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _utils as u  # noqa: E402


def _cfg(root: Path | None = None) -> dict:
    cfg = u.load_config(root).get("notify", {}) if root or u.find_project_root() else {}
    # env vars sobrescrevem o toml
    return {
        "enabled": cfg.get("enabled", True),
        "telegram_bot_token": os.environ.get("TELEGRAM_BOT_TOKEN") or cfg.get("telegram_bot_token", ""),
        "telegram_chat_id": os.environ.get("TELEGRAM_CHAT_ID") or cfg.get("telegram_chat_id", ""),
        "slack_webhook_url": os.environ.get("SLACK_WEBHOOK_URL") or cfg.get("slack_webhook_url", ""),
    }


def _post(url: str, payload: dict, timeout: float = 5.0) -> bool:
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return 200 <= r.status < 300
    except Exception:
        return False


def send_telegram(token: str, chat_id: str, text: str) -> bool:
    if not token or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    return _post(url, {"chat_id": chat_id, "text": text})


def send_slack(webhook: str, text: str) -> bool:
    if not webhook:
        return False
    return _post(webhook, {"text": text})


def notify(message: str, root: Path | None = None) -> dict:
    """Envia para todos os canais configurados. Retorna o que deu certo."""
    root = root or u.find_project_root()
    cfg = _cfg(root)
    result = {"telegram": False, "slack": False, "enabled": bool(cfg["enabled"])}
    if not cfg["enabled"]:
        return result
    result["telegram"] = send_telegram(cfg["telegram_bot_token"], cfg["telegram_chat_id"], message)
    result["slack"] = send_slack(cfg["slack_webhook_url"], message)
    u.emit_span("notify.sent", {"channels": [k for k, v in result.items() if v is True]}, root=root)
    return result


def cli(message: str) -> int:
    res = notify(message)
    sent = [k for k in ("telegram", "slack") if res.get(k)]
    if not res["enabled"]:
        print(u.c("○ notificações desligadas ([notify].enabled = false).", "dim"))
        return 0
    if sent:
        print(u.c(f"✓ notificado em: {', '.join(sent)}", "green"))
        return 0
    print(u.c("▲ nenhum canal configurado/atingido. Configure [notify] no toml ou "
              "as env vars (TELEGRAM_BOT_TOKEN/CHAT_ID, SLACK_WEBHOOK_URL).", "yellow"))
    return 1


if __name__ == "__main__":
    sys.exit(cli(sys.argv[1] if len(sys.argv) > 1 else "(sem mensagem)"))
