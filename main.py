from datetime import datetime
from html import escape
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple

import yaml  # type: ignore
from jinja2 import Environment, FileSystemLoader


def collect_categories(items: Optional[List[Dict[str, Any]]], field: str = "category") -> List[str]:
    out = set()
    for it in items or []:
        c = it.get(field)
        if isinstance(c, str) and c.strip():
            out.add(c.strip())
        elif isinstance(c, list):
            for x in c:
                if x:
                    out.add(str(x).strip())
    return sorted(out, key=lambda s: s.lower())


def sort_posts_by_date(posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    def date_key(post: Dict[str, Any]) -> datetime:
        raw = post.get("date")
        if isinstance(raw, str):
            try:
                return datetime.strptime(raw, "%Y-%m-%d")
            except ValueError:
                pass
        return datetime.min

    return sorted(posts, key=date_key, reverse=True)


FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.DOTALL)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
UL_ITEM_RE = re.compile(r"^\s*[-*+]\s+(.*)$")
OL_ITEM_RE = re.compile(r"^\s*\d+\.\s+(.*)$")
BLOCKQUOTE_RE = re.compile(r"^\s*>\s?(.*)$")
HR_RE = re.compile(r"^\s*([-*_])(?:\s*\1){2,}\s*$")


def parse_front_matter(content: str) -> Tuple[Dict[str, Any], str]:
    match = FRONT_MATTER_RE.match(content)
    if not match:
        return {}, content

    raw_meta, body = match.groups()
    meta = yaml.safe_load(raw_meta) or {}
    return (meta if isinstance(meta, dict) else {}), body.lstrip("\n")


def render_inline_markdown(text: str) -> str:
    placeholders: Dict[str, str] = {}
    escaped = escape(text, quote=False)

    def stash_code(match: re.Match[str]) -> str:
        key = f"__CODE_{len(placeholders)}__"
        placeholders[key] = f"<code>{escape(match.group(1))}</code>"
        return key

    escaped = re.sub(r"`([^`]+)`", stash_code, escaped)
    escaped = re.sub(
        r"!\[([^\]]*)\]\(([^)]+)\)",
        lambda m: (
            f'<img src="{escape(m.group(2), quote=True)}" '
            f'alt="{escape(m.group(1), quote=True)}" loading="lazy">'
        ),
        escaped,
    )
    escaped = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda m: f'<a href="{escape(m.group(2), quote=True)}">{m.group(1)}</a>',
        escaped,
    )
    escaped = re.sub(
        r"(\*\*|__)(.+?)\1",
        lambda m: f"<strong>{m.group(2)}</strong>",
        escaped,
    )
    escaped = re.sub(
        r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)",
        lambda m: f"<em>{m.group(1)}</em>",
        escaped,
    )
    escaped = re.sub(
        r"(?<!_)_(?!\s)(.+?)(?<!\s)_(?!_)",
        lambda m: f"<em>{m.group(1)}</em>",
        escaped,
    )

    for key, value in placeholders.items():
        escaped = escaped.replace(key, value)

    return escaped


def markdown_to_html(markdown: str) -> str:
    lines = markdown.splitlines()
    html_parts: List[str] = []
    paragraph_lines: List[str] = []
    unordered_items: List[str] = []
    ordered_items: List[str] = []
    blockquote_lines: List[str] = []
    code_lines: List[str] = []
    code_language = ""
    in_code_block = False

    def flush_paragraph() -> None:
        if not paragraph_lines:
            return
        text = " ".join(line.strip() for line in paragraph_lines).strip()
        html_parts.append(f"<p>{render_inline_markdown(text)}</p>")
        paragraph_lines.clear()

    def flush_unordered() -> None:
        if not unordered_items:
            return
        html_parts.append(
            "<ul>" + "".join(f"<li>{render_inline_markdown(item)}</li>" for item in unordered_items) + "</ul>"
        )
        unordered_items.clear()

    def flush_ordered() -> None:
        if not ordered_items:
            return
        html_parts.append(
            "<ol>" + "".join(f"<li>{render_inline_markdown(item)}</li>" for item in ordered_items) + "</ol>"
        )
        ordered_items.clear()

    def flush_blockquote() -> None:
        if not blockquote_lines:
            return
        html_parts.append(f"<blockquote>{markdown_to_html(chr(10).join(blockquote_lines))}</blockquote>")
        blockquote_lines.clear()

    def flush_code_block() -> None:
        nonlocal code_language
        if not code_lines:
            return
        class_attr = f' class="language-{escape(code_language, quote=True)}"' if code_language else ""
        html_parts.append(f"<pre><code{class_attr}>{escape(chr(10).join(code_lines))}</code></pre>")
        code_lines.clear()
        code_language = ""

    def flush_all() -> None:
        flush_paragraph()
        flush_unordered()
        flush_ordered()
        flush_blockquote()

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()

        if in_code_block:
            if stripped.startswith("```"):
                flush_code_block()
                in_code_block = False
            else:
                code_lines.append(raw_line)
            continue

        if stripped.startswith("```"):
            flush_all()
            in_code_block = True
            code_language = stripped[3:].strip()
            continue

        if not stripped:
            flush_all()
            continue

        heading_match = HEADING_RE.match(stripped)
        if heading_match:
            flush_all()
            level = len(heading_match.group(1))
            html_parts.append(f"<h{level}>{render_inline_markdown(heading_match.group(2).strip())}</h{level}>")
            continue

        if HR_RE.match(stripped):
            flush_all()
            html_parts.append("<hr>")
            continue

        blockquote_match = BLOCKQUOTE_RE.match(line)
        if blockquote_match:
            flush_paragraph()
            flush_unordered()
            flush_ordered()
            blockquote_lines.append(blockquote_match.group(1))
            continue
        flush_blockquote()

        ul_match = UL_ITEM_RE.match(line)
        if ul_match:
            flush_paragraph()
            flush_ordered()
            unordered_items.append(ul_match.group(1).strip())
            continue

        ol_match = OL_ITEM_RE.match(line)
        if ol_match:
            flush_paragraph()
            flush_unordered()
            ordered_items.append(ol_match.group(1).strip())
            continue

        flush_unordered()
        flush_ordered()
        paragraph_lines.append(stripped)

    if in_code_block:
        flush_code_block()

    flush_all()
    return "\n".join(html_parts)


class Portfolio:
    def __init__(self):
        self.config_files = {
            "profile": "config/profile.yml",
            "about": "config/about.yml",
            "resume": "config/resume.yml",
            "projects": "config/projects.yml",
            "publications": "config/publications.yml",
            "blog": "config/blog.yml",
            "contact": "config/contact.yml",
            "navbar": "config/navbar.yml",
            "talks": "config/talks.yml",
            "site": "config/site.yml",
        }
        self.env = Environment(loader=FileSystemLoader("src/jinja"))
        self.env.filters["format_date"] = self.format_date

    def read_file(self, file_path: str) -> str:
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()

    def write_file(self, file_path: str, content: str) -> None:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as file:
            file.write(content)

    def load_config_file(self, file_key: str) -> Dict[str, Any]:
        file_path = self.config_files.get(file_key)
        if not file_path:
            return {}
        content = self.read_file(file_path)
        data = yaml.load(content, Loader=yaml.FullLoader)
        return data if isinstance(data, dict) else {}

    def format_date(self, date_str: str) -> str:
        date_object = datetime.strptime(date_str, "%Y-%m-%d")
        return date_object.strftime("%b %d, %Y")

    def render_template(
        self, template_name: str, output_path: str, context: Dict[str, Any]
    ) -> None:
        template = self.env.get_template(template_name)
        html_render = template.render(context)
        self.write_file(output_path, html_render)

    def discover_markdown_posts(self, directory: str) -> List[Dict[str, Any]]:
        posts_dir = Path(directory)
        if not posts_dir.exists():
            return []

        out: List[Dict[str, Any]] = []
        for md_path in sorted(posts_dir.glob("*.md")):
            raw = self.read_file(str(md_path))
            meta, body = parse_front_matter(raw)
            if meta.get("draft"):
                continue

            output_path = str(md_path.with_suffix(".html"))
            out.append(
                {
                    "title": meta.get("title") or md_path.stem.replace("-", " ").title(),
                    "category": meta.get("category", ""),
                    "description": meta.get("description", ""),
                    "date": str(meta.get("date", "")),
                    "url": output_path,
                    "source": str(md_path),
                    "output_path": output_path,
                    "body_html": markdown_to_html(body),
                }
            )

        return out

    def build_context(self) -> Dict[str, Any]:
        context: Dict[str, Any] = {
            key: self.load_config_file(key) for key in self.config_files
        }

        site = context.get("site") or {}
        landing = site.get("LANDING") or {}
        pages = site.get("PAGES") or {}

        publications = context.get("publications") or {}
        talks_cfg = context.get("talks") or {}
        projects = context.get("projects") or {}

        pubs_all = list(publications.get("PUBLICATIONS") or [])
        talks_all = list(talks_cfg.get("TALKS") or [])
        projects_all = list(projects.get("PROJECTS") or [])
        blog_cfg = context.get("blog") or {}
        markdown_dir = blog_cfg.get("MARKDOWN_DIR", "posts")
        markdown_posts = self.discover_markdown_posts(markdown_dir if isinstance(markdown_dir, str) else "posts")
        configured_posts = list(blog_cfg.get("POSTS") or [])
        posts_all = sort_posts_by_date(markdown_posts + configured_posts)

        def landing_slice(all_items: List[Any], max_key: str) -> Tuple[List[Any], bool]:
            raw = landing.get(max_key)
            if raw is None:
                n = 3
            else:
                n = int(raw)
            if n <= 0:
                return all_items[:], False
            return all_items[:n], len(all_items) > n

        pubs_landing, pubs_more = landing_slice(pubs_all, "publications_max")
        talks_landing, talks_more = landing_slice(talks_all, "talks_max")
        projects_landing, projects_more = landing_slice(projects_all, "projects_max")
        posts_landing, posts_more = landing_slice(posts_all, "blog_max")

        page_urls = {
            "publications": pages.get("publications", "publications.html"),
            "talks": pages.get("talks", "talks.html"),
            "work": pages.get("work", "work.html"),
            "blog": pages.get("blog", "blog.html"),
        }

        show_portfolio = bool(site.get("SHOW_PORTFOLIO_ON_HOME", False))
        show_work_nav = bool(site.get("SHOW_WORK_NAV", True))

        show_blog_on_home = bool(site.get("SHOW_BLOG_ON_HOME", False))
        show_blog_nav = bool(site.get("SHOW_BLOG_NAV", True))

        context.update(
            {
                "pubs_landing": pubs_landing,
                "publications_has_more": pubs_more,
                "talks_landing": talks_landing,
                "talks_has_more": talks_more,
                "projects_landing": projects_landing,
                "projects_has_more": projects_more,
                "posts_landing": posts_landing,
                "posts_all": posts_all,
                "markdown_posts": markdown_posts,
                "blog_has_more": posts_more,
                "publication_categories": collect_categories(pubs_all),
                "talk_categories": collect_categories(talks_all),
                "project_categories": collect_categories(projects_all),
                "page_urls": page_urls,
                "show_portfolio_on_home": show_portfolio,
                "show_work_nav": show_work_nav,
                "show_blog_on_home": show_blog_on_home,
                "show_blog_nav": show_blog_nav,
                "is_subpage": False,
                "nav_current": None,
                "page_title": f"{context['profile'].get('USER', {}).get('name', 'Portfolio')} · Computational biology",
            }
        )
        return context


if __name__ == "__main__":
    portfolio = Portfolio()
    context = portfolio.build_context()

    portfolio.render_template("site/index.j2", "index.html", context)

    name = context["profile"].get("USER", {}).get("name", "Portfolio")

    pub_ctx = {**context, "is_subpage": True, "nav_current": "publications"}
    pub_ctx["page_title"] = (
        f"{context['publications'].get('HEADER', {}).get('label', 'Publications')} · {name}"
    )
    portfolio.render_template("site/publications_page.j2", "publications.html", pub_ctx)

    talks_ctx = {**context, "is_subpage": True, "nav_current": "talks"}
    talks_ctx["page_title"] = (
        f"{context['talks'].get('HEADER', {}).get('label', 'Talks')} · {name}"
    )
    portfolio.render_template("site/talks_page.j2", "talks.html", talks_ctx)

    work_ctx = {**context, "is_subpage": True, "nav_current": "work"}
    work_ctx["page_title"] = (
        f"{context['projects'].get('HEADER', {}).get('label', 'Work')} · {name}"
    )
    portfolio.render_template("site/work_page.j2", "work.html", work_ctx)

    blog_ctx = {**context, "is_subpage": True, "nav_current": "blog"}
    blog_ctx["page_title"] = f"Blog · {name}"

    portfolio.render_template("site/blog_page.j2", "blog.html", blog_ctx)

    for post in context.get("markdown_posts", []):
        post_ctx = {**context, "post": post}
        post_ctx["page_title"] = f"{post.get('title', 'Blog')} · {name}"
        portfolio.render_template("site/blog_post.j2", post["output_path"], post_ctx)
