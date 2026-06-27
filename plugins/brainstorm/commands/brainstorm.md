---
description: Run a multi-agent ideation session (alias for the brainstorm skill)
argument-hint: [tier] [topic]
---

Invoke the `brainstorm` skill ONCE, passing the entire string `$ARGUMENTS` verbatim as the skill's argument. Do not split `$ARGUMENTS` into separate parameters — the skill's own parser handles tier + topic extraction.

After invoking the skill, do NOT invoke it again under any circumstance. The skill drives the full pipeline itself.

If `$ARGUMENTS` is empty, still invoke the skill once with empty args — it will ask the user interactively.
