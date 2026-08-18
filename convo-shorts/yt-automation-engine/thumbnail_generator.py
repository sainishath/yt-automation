# -*- coding: utf-8 -*-
"""
thumbnail_generator.py
----------------------
Generates custom Pillow-based title card thumbnails for convo-shorts.
Packs the debate question in bold wrapped text over a premium dark backdrop.
"""

import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def _get_font(names: list, size: int) -> ImageFont.ImageFont:
    """Safely loads the first available TrueType font from candidates or falls back to default."""
    for name in names:
        try:
            return ImageFont.truetype(name, size=size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


def generate_debate_thumbnail(question: str, output_path: str) -> str:
    """
    Generates a 1080x1920 portrait title card thumbnail with the debate question text.
    Uses Pillow with word wrapping and stylized borders.
    """
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    bg_color = (30, 30, 46)       # Deep dark blue/indigo (#1e1e2e)
    text_color = (255, 255, 255)   # White
    accent_color = (245, 194, 231) # Light accent (#f5c2e7)
    
    img = Image.new("RGB", (1080, 1920), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    font_candidates = ["Impact.ttf", "impact.ttf", "arialbd.ttf", "Arialbd.ttf", "msgothic.ttc"]
    font = _get_font(font_candidates, 80)
    tag_font = _get_font(font_candidates, 50)
        
    # Top and bottom horizontal accent lines
    draw.rectangle([50, 50, 1030, 60], fill=accent_color)
    draw.rectangle([50, 1860, 1030, 1870], fill=accent_color)
    
    # Top series tag
    draw.text((540, 180), "AI DEBATE SERIES", fill=accent_color, font=tag_font, anchor="mm")
    
    # Word wrap question text within 850px width limit
    words = question.upper().split()
    lines = []
    current_line = []
    for word in words:
        current_line.append(word)
        test_line = " ".join(current_line)
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if (bbox[2] - bbox[0]) > 850:
            current_line.pop()
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))
        
    # Center text vertically
    line_height = 100
    total_text_height = len(lines) * line_height
    start_y = 960 - (total_text_height // 2)
    
    for idx, line in enumerate(lines):
        y = start_y + (idx * line_height)
        # Drop shadow and main text
        draw.text((544, y + 4), line, fill=(0, 0, 0), font=font, anchor="mm")
        draw.text((540, y), line, fill=text_color, font=font, anchor="mm")
        
    img.save(out_path, "JPEG", quality=95)
    print(f"[Thumbnail] Generated Pillow title card: {out_path.name}")
    return str(out_path)
