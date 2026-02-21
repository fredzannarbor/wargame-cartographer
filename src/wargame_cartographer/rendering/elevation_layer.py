"""Elevation layer: hillshade overlay for topographic depth."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

from wargame_cartographer.rendering.renderer import RenderContext


def render_elevation_layer(
    ax: plt.Axes,
    context: RenderContext,
    x_min: float,
    x_max: float,
    y_min: float,
    y_max: float,
):
    """Render hillshade as a semi-transparent overlay.

    The hillshade provides subtle topographic shading that gives
    the map depth without obscuring terrain colors.
    """
    if context.hillshade is None:
        return

    ax.imshow(
        context.hillshade,
        cmap="gray",
        alpha=context.style.hillshade_alpha,
        extent=(x_min, x_max, y_min, y_max),
        zorder=2,
        interpolation="bilinear",
    )
