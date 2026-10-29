# -*- coding: utf-8 -*-
"""
pipeline/visuals.py
-------------------
Visual Generator & QA Gate exports (alias module for pipeline/compositor.py).
"""

from pipeline.compositor import (
    FOOOCUS_NEGATIVE_PROMPT_LOCK,
    MOTION_TRAJECTORIES,
    SAFE_SHORTS_ASS_HEADER,
    SAFE_SHORTS_ASS_STYLE,
    build_fooocus_scene_prompt,
    detect_split_panel_collage,
    render_dynamic_short_scene,
)

__all__ = [
    "FOOOCUS_NEGATIVE_PROMPT_LOCK",
    "MOTION_TRAJECTORIES",
    "SAFE_SHORTS_ASS_HEADER",
    "SAFE_SHORTS_ASS_STYLE",
    "build_fooocus_scene_prompt",
    "detect_split_panel_collage",
    "render_dynamic_short_scene",
]
