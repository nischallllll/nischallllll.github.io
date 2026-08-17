import re
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import markdown  # type: ignore
import yaml  # type: ignore
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

CONTENT_DIR = Path("content")
POSTS_DIR = Path("posts")
FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.DOTALL)
INTERNAL_HOSTS = {"", "nischallllll.github.io", "www.nischallllll.github.io"}
EXTERNAL_LINK_RE = re.compile(r'<a href="([^"]+)"(?![^>]*\btarget=)')


def is_external_url(url: Any) -> bool:
    if not isinstance(url, str):
        return False

    raw = url.strip()
    if not raw or raw.startswith(("#", "/", "./", "../")):
        return False

    parsed = urlparse(raw)
    return (
        parsed.scheme in {"http", "https"}
        and parsed.netloc.lower() not in INTERNAL_HOSTS
    )


def parse_markdown(source: str) -> tuple[dict[str, Any], str]:
    match = FRONT_MATTER_RE.match(source)
    if not match:
        return {}, source

    metadata, body = match.groups()
    parsed = yaml.safe_load(metadata) or {}
    return (parsed if isinstance(parsed, dict) else {}), body.lstrip("\n")


def render_markdown(body: str) -> Markup:
    html = markdown.markdown(body, extensions=["extra", "sane_lists", "smarty"])

    def add_link_attributes(match: re.Match[str]) -> str:
        href = match.group(1)
        if is_external_url(href):
            return f'<a href="{href}" target="_blank" rel="noopener noreferrer"'
        return match.group(0)

    return Markup(EXTERNAL_LINK_RE.sub(add_link_attributes, html))


def plain_text(html: Markup) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", str(html))).strip()


def render_inline_markdown(text: str) -> Markup:
    html = markdown.markdown(text, extensions=["extra", "sane_lists", "smarty"])

    soup = BeautifulSoup(html, "html.parser")

    for link in soup.find_all("a"):
        link["target"] = "_blank"
        link["rel"] = "noopener noreferrer"

    return Markup(str(soup))


def read_document(path: Path) -> dict[str, Any]:
    metadata, body = parse_markdown(path.read_text(encoding="utf-8"))
    body_html = render_markdown(body)
    return {
        **metadata,
        "source": path,
        "slug": path.stem,
        "body_html": body_html,
        "summary": render_inline_markdown(
            metadata.get("summary")
            or metadata.get("description")
            or plain_text(body_html)
        ),
    }


def collection(name: str) -> list[dict[str, Any]]:
    directory = CONTENT_DIR / name
    if not directory.exists():
        return []

    items = []
    for path in directory.glob("*.md"):
        item = read_document(path)
        if item.get("draft"):
            continue
        tags = item.get("tags", item.get("category", item.get("tag", [])))
        item["tags"] = (
            [str(tag) for tag in tags]
            if isinstance(tags, list)
            else [str(tags)]
            if tags
            else []
        )
        item["year"] = str(item.get("year", ""))
        item["date"] = str(item.get("date", ""))
        items.append(item)

    return sorted(
        items,
        key=lambda item: item.get("date") or item.get("year") or item["slug"],
        reverse=True,
    )


def format_date(value: Any) -> str:
    if isinstance(value, (date, datetime)):
        return value.strftime("%b %d, %Y")
    if not value:
        return ""
    return datetime.strptime(str(value), "%Y-%m-%d").strftime("%b %d, %Y")


class Site:
    def __init__(self) -> None:
        self.env = Environment(
            loader=FileSystemLoader("src/templates"),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.env.filters["format_date"] = format_date
        self.env.globals["is_external_url"] = is_external_url

    def render(
        self, template_name: str, output_path: Path, context: dict[str, Any]
    ) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            self.env.get_template(template_name).render(context), encoding="utf-8"
        )


def main() -> None:
    site = Site()
    profile = read_document(CONTENT_DIR / "profile.md")
    home = read_document(CONTENT_DIR / "home.md")
    publications = collection("publications")
    talks = collection("talks")
    projects = collection("projects")
    notes = collection("notes")

    for note in notes:
        note["url"] = f"posts/{note['slug']}.html"

    context = {
        "profile": profile,
        "home": home,
        "publications": publications,
        "talks": talks,
        "projects": projects,
        "notes": notes,
        "page_title": f"{profile['name']} · Computational biology",
        "page_description": profile.get("description", ""),
        "nav_current": "home",
        "asset_prefix": "",
    }

    site.render("index.j2", Path("index.html"), context)

    pages = (
        (
            "Publications",
            "publications.html",
            publications,
            "Papers, preprints, and research output.",
            "publications",
        ),
        ("Talks", "talks.html", talks, "Invited talks and presentations.", "talks"),
        (
            "Projects",
            "work.html",
            projects,
            "Open-source tools and selected projects.",
            "projects",
        ),
        (
            "Notes",
            "blog.html",
            notes,
            "Research notes, reading lists, and essays.",
            "notes",
        ),
    )
    for label, filename, items, description, nav_current in pages:
        site.render(
            "collection.j2",
            Path(filename),
            {
                **context,
                "page_title": f"{label} · {profile['name']}",
                "page_heading": label,
                "page_description": description,
                "items": items,
                "nav_current": nav_current,
            },
        )

    POSTS_DIR.mkdir(exist_ok=True)
    for old_post in POSTS_DIR.glob("*.html"):
        old_post.unlink()

    for note in notes:
        site.render(
            "note.j2",
            POSTS_DIR / f"{note['slug']}.html",
            {
                **context,
                "page_title": f"{note['title']} · {profile['name']}",
                "page_description": note.get("summary", ""),
                "note": note,
                "nav_current": "notes",
                "asset_prefix": "../",
            },
        )


if __name__ == "__main__":
    main()
