"""Simple HTML report assembly."""

from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Template


TEMPLATE = Template(
    """<!doctype html>
<html><head><meta charset="utf-8"><title>Diurnalize Report</title>
<style>body{font-family:system-ui,sans-serif;max-width:980px;margin:32px auto;line-height:1.45}code{background:#f4f4f4;padding:2px 4px}img{max-width:100%;border:1px solid #ddd}</style>
</head><body>
<h1>Diurnalize Report</h1>
<h2>Run Summary</h2>
<pre>{{ manifest }}</pre>
<h2>Preprocessing</h2>
<pre>{{ preprocessing }}</pre>
<h2>Diagnostics</h2>
<pre>{{ diagnostics }}</pre>
<h2>Validation Plots</h2>
{% for plot in plots %}<figure><img src="{{ plot }}"><figcaption>{{ plot }}</figcaption></figure>{% endfor %}
</body></html>"""
)


def write_report(run_dir: str | Path, output: str | Path) -> None:
    run = Path(run_dir)
    output = Path(output)
    val = run / "validation"
    plots = []
    if val.exists():
        plots = [str(p.relative_to(output.parent)) if p.is_relative_to(output.parent) else str(p) for p in sorted(val.glob("*.png"))]
    def read_json(path: Path):
        return json.dumps(json.load(path.open()), indent=2) if path.exists() else "{}"
    html = TEMPLATE.render(
        manifest=read_json(run / "manifest.json"),
        preprocessing=read_json(run / "preprocessing_summary.json"),
        diagnostics=read_json(run / "diagnostics_summary.json"),
        plots=plots,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html)
