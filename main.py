from datetime import datetime
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


def sort_posts_by_published(posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    def published_key(post: Dict[str, Any]) -> datetime:
        raw = post.get("published")
        if isinstance(raw, str):
            try:
                return datetime.strptime(raw, "%Y-%m-%d")
            except ValueError:
                pass
        return datetime.min

    return sorted(posts, key=published_key, reverse=True)


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
        with open(file_path, "w", encoding="utf-8") as file:
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
        posts_all = sort_posts_by_published(list(blog_cfg.get("POSTS") or []))

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
