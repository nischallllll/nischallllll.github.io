<!-- markdownlint-disable MD033 MD036 MD041 MD045 MD046 -->
<div align="center">

<h1 style="border-bottom: none">
    <b><a href="https://nischallllll.github.io/">Personal Portfolio </a></b>
</h1>

## Build (generate HTML)

The live pages **`index.html`**, **`publications.html`**, **`talks.html`**, and **`work.html`** are produced by Jinja from YAML + templates. **Do not hand-edit those four files** if you use the generator—your changes will be overwritten.

1. Python 3.9+ recommended.
2. `pip install -r requirements.txt` (or use the project `.venv`).
3. Run:

```bash
python main.py
```

### What to edit

| Goal | Edit |
|------|------|
| Papers list | `config/publications.yml` |
| Talks list | `config/talks.yml` |
| Projects / portfolio | `config/projects.yml` |
| How many items show on the **home** page | `config/site.yml` → `LANDING` (`publications_max`, `talks_max`, `projects_max`). Use **`0`** for “show everything on home” (no “View all” link). |
| Publications **layout** (HTML) | `src/jinja/site/publications_landing.j2`, `publications_full_block.j2`, `_publication_card.j2` |
| Talks **layout** | `src/jinja/site/talks_landing.j2`, `talks_full_block.j2`, `_talk_card.j2` |
| Projects **layout** | `src/jinja/site/projects_landing.j2`, `projects_full_block.j2`, `_project_card.j2` |
| Whole homepage shell (hero, training, etc.) | `src/jinja/site/index.j2` |
| Profile / footer email | `config/profile.yml` (footer social links are in `src/jinja/site/footer_block.j2` for now) |

Full lists with category filters: **`publications.html`**, **`talks.html`**, **`work.html`**. The home page shows only the first *N* items (per `site.yml`) when *N* &gt; 0 and there are more than *N* entries.

**Note:** `src/jinja/index.j2` is an older multi-tab layout and is **not** used by `main.py` anymore.

