---
description: "Transcreve um arquivo de áudio localmente (faster-whisper opcional) para virar texto/intent."
argument-hint: "<caminho-do-audio.wav|mp3|m4a>"
---

Transcreva o áudio em `$ARGUMENTS` localmente (privado, sem nuvem) e use o texto.

1. Rode `python3 scripts/mad.py voice "$ARGUMENTS"` (fallback `python`).
2. Se `faster-whisper` não estiver instalado, a CLI avisa — explique ao usuário que
   é **opt-in** e roda 100% local: `pip install faster-whisper`. Não force a instalação
   sem perguntar.
3. Com o texto transcrito em mãos, trate-o como entrada do usuário: se for a descrição
   de uma feature, conduza o discovery (`mad-discovery`) a partir dele; se for um
   comando, execute.

Gravação de microfone é específica de plataforma — o usuário grava o áudio com a
ferramenta dele e passa o arquivo. TTS (voz de saída) é roadmap.
