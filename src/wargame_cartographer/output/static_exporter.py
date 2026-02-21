"""Static output: PNG and PDF export via matplotlib."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt


def export_png(fig: plt.Figure, path: Path, dpi: int = 300) -> Path:
    """Export map as PNG."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(path), dpi=dpi, bbox_inches="tight", facecolor="white")
    return path


def export_pdf(fig: plt.Figure, path: Path) -> Path:
    """Export map as PDF (vector)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(path), bbox_inches="tight", facecolor="white")
    return path
