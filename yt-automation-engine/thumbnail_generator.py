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

def generate_debate_thumbnail(question: str, output_path: str):
    """
    Generates a 1080x1920 portrait title card thumbnail with the debate question text.
    Uses Pillow with word wrapping and stylized borders.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Premium background color: deep dark blue/indigo (#11111b or #1e1e2e)
    bg_color = (30, 30, 46)  # RGB
    text_color = (255, 255, 255) # White
    accent_color = (245, 194, 231) # Light pink/purple accent (#f5c2e7)
    
    # Create image
    img = Image.new("RGB", (1080, 1920), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # Load font - try to find a bold font, fallback to default
    font_names = ["Impact.ttf", "impact.ttf", "arialbd.ttf", "Arialbd.ttf", "msgothic.ttc"]
    font = None
    for name in font_names:
        try:
            font = ImageFont.truetype(name, size=80)
            break
        except IOError:
            continue
            
    if font is None:
        font = ImageFont.load_default()
        
    # Draw accent borders
    # Top and bottom horizontal accent lines
    draw.rectangle([50, 50, 1030, 60], fill=accent_color)
    draw.rectangle([50, 1860, 1030, 1870], fill=accent_color)
    
    # Draw "DEBATE" tag at top
    tag_font = None
    for name in font_names:
        try:
            tag_font = ImageFont.truetype(name, size=50)
            break
        except IOError:
            continue
    if tag_font is None:
        tag_font = ImageFont.load_default()
        
    draw.text((540, 180), "AI DEBATE SERIES", fill=accent_color, font=tag_font, anchor="mm")
    
    # Wrap text
    words = question.upper().split()
    lines = []
    current_line = []
    for word in words:
        current_line.append(word)
        test_line = " ".join(current_line)
        # Check text width
        bbox = draw.textbbox((0, 0), test_line, font=font)
        w = bbox[2] - bbox[0]
        if w > 850:
            current_line.pop()
            lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))
        
    # Render question text centered vertically
    line_height = 100
    total_text_height = len(lines) * line_height
    start_y = 960 - (total_text_height // 2)
    
    for idx, line in enumerate(lines):
        y = start_y + (idx * line_height)
        # Draw a subtle drop shadow
        draw.text((544, y + 4), line, fill=(0, 0, 0), font=font, anchor="mm")
        # Draw main text
        draw.text((540, y), line, fill=text_color, font=font, anchor="mm")
        
    # Save image
    img.save(output_path, "JPEG", quality=95)
    print(f"[Thumbnail] Generated Pillow title card: {output_path.name}")
    return str(output_path)
