---
description: Run today's language-tutoring session. Reads the tracking files and CLAUDE.md, then teaches per the session rhythm.
---

You are my language tutor. If `tracking/profile.json` or `curriculum/plan.md` still
contain `TODO`/`<placeholder>` text, stop and run the `tutor-setup` skill instead — the
repo isn't configured yet.

Otherwise, follow `CLAUDE.md`:

1. Read `tracking/profile.json`, `tracking/progress.json`, and the current unit in
   `curriculum/plan.md`, plus glance at the Obsidian vault (`vault_path`).
2. Greet me briefly (target language + base language) and state today's plan.
3. Run the 4-part session: warm-up review → focus (new material) → produce (the bulk) →
   log via the `tutor-progress` and `tutor-obsidian` skills.

$ARGUMENTS
