# Contrato de Tema (skins) — dashboard `mad`

Este documento é o **contrato** entre a infraestrutura do dashboard e cada
arquivo de tema. Se você vai criar `themes/<slug>.css`, leia isto inteiro.
Seguindo o contrato, seu tema convive com os outros 19 sem nenhum conflito.

---

## 1. Regras de ouro (não-negociáveis)

1. **Um arquivo por tema:** `dashboard/themes/<slug>.css`. Nada fora dele.
2. **TUDO escopado sob `html[data-skin="<slug>"]`.** Nenhuma regra global,
   nenhum `:root {}` solto, nenhum seletor sem o prefixo. Isto é o que
   garante que trocar de tema no dropdown troca 100% do visual sem vazar.
3. **Não edite** `style.css`, `app.js`, `index.html`. A estrutura (HTML +
   layout base + JS) é fixa. Você só pinta.
4. **Vanilla CSS.** Zero build, zero import de fonte externa por `@import` de
   rede que bloqueie render (prefira `font-family` de fontes de sistema; se
   precisar de webfont, use `@font-face` com `font-display: swap` e um
   fallback de sistema). Zero JS.
5. **Respeite `prefers-reduced-motion`.** Se seu tema adiciona animação nova,
   envolva-a (ou desligue-a) em `@media (prefers-reduced-motion: reduce)`.
6. **O slug precisa estar cadastrado** no array `SKINS` de `app.js` (os 20 já
   estão). O loader injeta `<link href="themes/<slug>.css">` lazy e tolera o
   arquivo ainda não existir (`onerror`), então nada quebra enquanto você não
   entregou o CSS.

### Esqueleto mínimo

```css
/* themes/<slug>.css */
html[data-skin="<slug>"] {
  /* 1) redefina os tokens (muda ~80% do visual de graça) */
  --bg: #...;
  --surface: #...;
  --text: #...;
  --accent: #...;
  --border: #...;
  --radius: 0px;
  --shadow: none;
  --font-sans: "Helvetica Neue", Arial, sans-serif;
}

/* 2) refine os componentes que precisam de tratamento especial */
html[data-skin="<slug>"] .agent {
  border: 2px solid var(--border);
  box-shadow: none;
}
html[data-skin="<slug>"] .agent-term { /* ... */ }
/* etc. */
```

Sempre prefixe **cada** seletor com `html[data-skin="<slug>"] `. Para não
repetir, alguns autores usam um pré-processador — aqui é vanilla, então
repita mesmo. Copie/cole é ok.

---

## 2. Tokens (CSS custom properties)

A base (`style.css`) declara estes tokens em `:root` e **todos os
componentes os consomem**. Redefinir um token no seu bloco
`html[data-skin="..."]` propaga para o dashboard inteiro. Esta é a alavanca
principal do tema.

| Token | Papel | Default (dark) |
|---|---|---|
| `--bg` | fundo da página | `#1a1a28` |
| `--bg-soft` | fundo recuado (trilhos de barra, trust bar) | `#232336` |
| `--surface` | superfície de cards/painéis | `#2a2a3c` |
| `--surface-2` | superfície secundária (pílulas, bubble, inputs) | `#303045` |
| `--border` | cor de borda padrão | `#3a3a52` |
| `--text` | texto primário | `#e4e4ef` |
| `--text-dim` | texto secundário | `#a0a0b8` |
| `--text-faint` | texto terciário / labels | `#6c6c8a` |
| `--accent` | cor de marca / destaque primário | `#7aa2f7` |
| `--accent-2` | destaque secundário / gradientes | `#a68cf0` |
| `--gold` | semântico: decantando / custo | `#d4a04a` |
| `--orange` | semântico: aviso / controle humano | `#e08a3a` |
| `--red` | semântico: erro / ao-vivo / bypass | `#e05a5a` |
| `--green` | semântico: ok / concluído / online | `#5ac06a` |
| `--grey` | semântico: dormindo / neutro | `#8a8aa0` |
| `--radius` | raio de canto padrão (cards, botões) | `14px` |
| `--radius-lg` | raio grande (hero, modal) | `20px` |
| `--shadow` | sombra forte (hover, modal) | `0 4px 18px rgba(0,0,0,.35)` |
| `--shadow-soft` | sombra sutil (cards em repouso) | `0 2px 10px rgba(0,0,0,.22)` |
| `--gap` | espaçamento base do grid do time | `14px` |
| `--font-sans` | família sem serifa (UI) | `system-ui, …` |
| `--font-mono` | família monoespaçada (terminal, métricas) | `ui-monospace, …` |

### Aliases legados (não use em tema novo, mas existem)
`--panel` → `var(--surface)`, `--panel-2` → `var(--surface-2)`,
`--sans` → `var(--font-sans)`, `--mono` → `var(--font-mono)`.
Redefinir `--surface`/`--font-sans` já atualiza os aliases; **prefira sempre
os nomes canônicos** (`--surface`, `--surface-2`, `--font-sans`,
`--font-mono`).

### `--agent-color`
Cada card e o modal recebem `--agent-color` **inline via JS** (cor do agente,
de `assets/colors.json`). Use `var(--agent-color)` para acentos por agente
(anel do avatar, barra do topo do card, foco). Você **não** define esse token
no tema — ele vem por agente — mas pode consumi-lo à vontade.

### Tokens/atributos de estado que você NÃO controla mas pode estilizar
- `html[data-theme="light"|"dark"|"auto"]` — o toggle claro/escuro continua
  existindo e convive com as skins. Se quiser que seu tema reaja a
  claro/escuro, escope `html[data-skin="x"][data-theme="light"] { … }`. Se
  seu tema tem paleta fixa (ex.: terminal), simplesmente ignore o
  `data-theme` (é o comportamento padrão — sua paleta fixa vence).

---

## 3. Seletores de componente que um tema pode redefinir

Lista canônica. Prefixe todos com `html[data-skin="<slug>"] `.

### Topbar / chrome
- `.topbar`, `.brand`, `.brand-dot`, `.brand h1`
- `.conn`, `.conn-dot`, `.conn--online`, `.conn--connecting`, `.conn--offline`
- `.icon-btn` (toggle de tema)
- `.ctrl-btn` (filtro / som / avatar — injetados por JS)
- `.skin-picker`, `.skin-select` (o próprio dropdown de tema)

### Hero (etapa atual)
- `.hero`, `.hero-glow`, `.hero-eyebrow`, `.hero-title`, `.hero-doing`
- `.hero-aside`, `.hero-item`, `.hi-badge`, `.hi-text`, `.hi-slug`, `.hi-sub`
- `.hero-flags`, `.flag`, `.flag--warn`, `.flag--bypass`, `.hero-next`

### Mapa do workflow (jornada educativa — substitui o antigo stepper)
Um "state-machine map" temável: nós (fases) + arestas (com a condição
anotada) + ramificações + sub-loop de "Construindo" + painel explicador.
O JS aplica `is-done` / `is-current` / `is-future` nos nós/arestas conforme a
posição da fase atual, e `is-selected` no nó fixado por clique.

- **Contêiner:** `.wfmap-wrap`, `.wfmap-head`, `.wfmap-hint`, `.wfmap`
- **Nó (fase):** `.wfnode` (+ estados `.wfnode.is-done`, `.wfnode.is-current`,
  `.wfnode.is-future`, `.wfnode.is-selected`)
  - `.wfnode-btn` (o clicável), `.wfnode-badge` (círculo do ícone),
    `.wfnode-icon`, `.wfnode-check` (selo de concluído)
  - `.wfnode-label`, `.wfnode-here`, `.wfnode-here-dot`, `.wfnode-doing`
  - `.wfnode-branches`, `.wfnode-branch`, `.wfbr-arrow` (ramificações do nó)
- **Aresta (conector + condição):** `.wfedge` (+ `.wfedge.is-done`,
  `.wfedge.is-current`), `.wfedge-line` (a linha; a ponta da seta é
  `.wfedge-line::after`), `.wfedge-label` (chip com a condição `when`)
- **Trilho de retorno do ciclo:** `.wfreturn` (+ `.wfreturn.is-active`),
  `.wfreturn-arrow`, `.wfreturn-label`
- **Sub-loop de "Construindo":** `.wfsub`, `.wfsub-head`, `.wfsub-head-ic`,
  `.wfsub-track`, `.wfsub-step` (+ `.is-done`, `.is-current`, `.is-future`),
  `.wfsub-icon`, `.wfsub-label`, `.wfsub-arrow`, `.wfsub-loop`
- **Painel explicador:** `.wf-explainer`, `.wfx-head`, `.wfx-icon`,
  `.wfx-title`, `.wfx-tag` (+ `.wfx-tag--here`, `.wfx-tag--muted`),
  `.wfx-pin`, `.wfx-detail`, `.wfx-row` (+ `.wfx-advance`, `.wfx-goes`),
  `.wfx-k`, `.wfx-list`, `.wfx-when`, `.wfx-to`
- **Animações próprias da base** (redefiníveis no seu escopo, ou desligadas
  para o tema): `wf-pulse`, `wf-ping`, `wf-flow`, `wf-spin`. Reutiliza também
  `fadein`. Todas já respeitam `prefers-reduced-motion` via a regra global.
- **Responsivo:** abaixo de `760px` o mapa vira jornada **vertical**; se o seu
  tema mexe muito na aresta, teste nos dois eixos.

### Layout / seções
- `.content`, `.dash-grid`, `.side-col`
- `.section-title`, `.team-count`, `.live-dot`

### Paralelo (motor DAG — várias features ao mesmo tempo)
Só aparece quando `workflow.parallel` tem **mais de 1** item (modo `engine=dag`).
Com 0/1 item fica escondido (modo sequential de sempre). Cada card recebe
`--agent-color` inline via JS (cor do assistente daquela feature).
- `.parallel` (contêiner), `.parallel-title`, `.parallel-hint`, `.parallel-grid`
- `.pfeat` (card da feature) `> .pfeat-name (.pfeat-dot, .pfeat-slug),
  .pfeat-doing, .pfeat-agent (.pfeat-agent-ic, .pfeat-agent-name)`
- Animações próprias: `pfeat-in` (entrada), `pfeat-pulse` (ponto vivo) — ambas
  já neutralizadas pela regra global de `prefers-reduced-motion`.

### Card de agente (o coração)
- `.team`, `.team-empty`
- `.agent` (+ `.agent::before` = barra colorida do topo)
- `.agent-avatar`, `.agent-avatar::before` (anel de status), `.agent-avatar-inner`
- `.agent-name`, `.agent-status`, `.agent-status .glyph`, `.agent-bubble`
- `.agent-pin`, `.agent-open-hint`, `.zzz`
- **Estados** (o JS aplica a classe no card):
  `.agent--working`, `.agent--idle`, `.agent--decanting`,
  `.agent--human_driving`, `.agent--error`, `.agent--needs_recovery`,
  `.agent--sleeping`, `.agent--pinned`, `.agent.dragging`

### Mini-terminal / stream (no card e no modal)
- `.agent-term` (o container rolável)
- `.term-line`, `.term-ts`, `.term-ic`, `.term-tx`, `.term-add`
- **Cores por tipo de linha** — as classes são `.term--<kind>`, onde
  `<kind>` ∈ `read write edit bash grep web agent think decant ok error
  start say dim tool`. Ex.: `.term--read`, `.term--error`, `.term--ok`.
  (Observação: no `_CONTRATO` original a notação sugerida era
  `.term-line.kind-*`; a implementação real usa `.term-line.term--<kind>` —
  estilize por `.term--<kind>`.)

### Barra de confiança
- `.agent-trust`, `.agent-trust-head`, `.trust-bar`, `.trust-bar-fill`

### Métricas
- `.metrics-grid`, `.metric`, `.metric-head`, `.metric-label`
- `.metric-value`, `.metric-value--big`, `.metric-sub`
- `.bar`, `.bar-fill`, `.bar-fill--cost`, `.bar-fill.is-warn`, `.bar-fill.is-danger`

### Atividade (feed)
- `.activity-list`, `.activity-list li`, `.activity-empty`, `.act-new`
- `.act-ts`, `.act-icon`, `.act-text`
- `.act-icon[data-i="▶"|"◆"|"✓"|"✗"]` (cor do ícone por tipo)

### Fullscreen (tela cheia do agente)
- `.fullscreen-agent` (overlay), `.fs-backdrop`, `.fs-panel`
- `.fs-close`
- `.fs-head`, `.fs-avatar`, `.fs-avatar::before`, `.fs-avatar-inner`
- `.fs-meta`, `.fs-name`, `.fs-status`, `.fs-status .glyph`, `.fs-status-label`
- `.fs-trust`, `.fs-trust-head`, `.fs-trust-val`
- `.fs-bubble`
- `.fs-term-wrap`, `.fs-term-label`, `.fs-term-holder`, `.fs-term`, `.fs-term-empty`

### Outros
- `.offline-banner`
- `.sr-only` (não estilize — é utilitário de acessibilidade)

---

## 4. Animações da base (pode sobrescrever)

Keyframes existentes que você pode redefinir/estender **dentro do seu escopo**
(prefixe o seletor que consome, não o `@keyframes` — keyframes são globais;
para animação nova, dê um nome próprio prefixado, ex.: `swiss-blink`):
`pulse blink spin shake bob float-z typing fadein actin livepulse steppulse
drift fs-fade fs-expand`.

---

## 5. Estrutura HTML de referência (para saber onde cada classe cai)

```
.topbar
  .brand > .brand-dot, h1#title
  .topbar-actions
    (.ctrl-btn ×3 injetados)  #conn.conn  .skin-picker>select.skin-select  #theme-toggle.icon-btn
.content
  .hero#hero
  .wfmap-wrap#wfmap-wrap
    .wfmap-head > .section-title
    .wfmap#wfmap > (.wfnode[.is-done/.is-current/.is-future] , .wfedge)*
        .wfnode > .wfnode-btn(.wfnode-badge>.wfnode-icon/.wfnode-check, .wfnode-label),
                  .wfnode-here, .wfnode-doing, .wfnode-branches>.wfnode-branch
        .wfedge > .wfedge-line + .wfedge-label
    .wfreturn#wfreturn > .wfreturn-arrow + .wfreturn-label
    .wfsub#wfsub > .wfsub-head + .wfsub-track>.wfsub-step(.is-current/.is-done)
    .wf-explainer#wf-explainer > .wfx-head + .wfx-detail + .wfx-row*
  .dash-grid
    .team-col > .section-title, #team.team > .agent[.agent--<estado>]
        > .agent-pin, .agent-open-hint, .agent-avatar>.agent-avatar-inner,
          .agent-name, .agent-status>.glyph, .agent-bubble,
          .agent-term>.term-line.term--<kind>, .agent-trust>.trust-bar>.trust-bar-fill
    .side-col
      .metrics > .metrics-grid > .metric ...
      .activity > .activity-list > li > .act-ts/.act-icon/.act-text

(injetado no body ao abrir a tela cheia:)
.fullscreen-agent[role=dialog] > .fs-backdrop, .fs-panel
   > .fs-close, .fs-head(.fs-avatar,.fs-meta>.fs-name/.fs-status/.fs-trust),
     .fs-bubble, .fs-term-wrap>.fs-term-label + .fs-term-holder>.agent-term.fs-term
```

---

## 6. Checklist antes de entregar seu tema

- [ ] Arquivo é `themes/<slug>.css` e o slug bate com o do dropdown.
- [ ] **Toda** regra começa com `html[data-skin="<slug>"] `.
- [ ] Redefiniu ao menos: `--bg`, `--surface`, `--surface-2`, `--text`,
      `--text-dim`, `--accent`, `--border`, `--radius`, `--shadow`,
      `--font-sans`. (Quanto mais tokens, mais coeso.)
- [ ] Tratou `.agent`, `.agent-term`, `.hero`, `.metric`, `.activity-list`,
      `.fs-panel` — os blocos de maior área.
- [ ] Legibilidade: contraste texto/superfície ≥ WCAG AA.
- [ ] `prefers-reduced-motion` respeitado para qualquer animação nova.
- [ ] Testou trocando no dropdown e abrindo a tela cheia de um agente.
- [ ] É **radicalmente** diferente dos vizinhos — tipografia, cor,
      espaçamento, borda, sombra, canto, fundo. Não é "o mesmo com outra cor".

Referências de alto padrão já prontas (copie a régua):
`visionos.css`, `swiss.css`, `neobrutalism.css`, `terminal.css`.
