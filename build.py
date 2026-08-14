"""Render docs/index.html from the payload.

Autoescape is ON - the page prints company names from a third-party source and must
never inject them as markup.
"""

import os

from jinja2 import Environment, FileSystemLoader, select_autoescape

HERE = os.path.dirname(os.path.abspath(__file__))


def env():
    return Environment(
        loader=FileSystemLoader(os.path.join(HERE, "templates")),
        autoescape=select_autoescape(["html"]),
    )


def render(payload):
    counts = {}
    for r in payload.get("names", []) + payload.get("excluded", []):
        counts[r["market"]] = counts.get(r["market"], 0) + 1
    return env().get_template("index.html.j2").render(counts=counts, **payload)


def write(payload, path=None):
    path = path or os.path.join(HERE, "docs", "index.html")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(render(payload))
