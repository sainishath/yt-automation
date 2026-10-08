# -*- coding: utf-8 -*-
"""
horizontal_card_renderer.py
---------------------------
High-resolution 16:9 (1920x1080) Horizontal Split-Screen Code & Architecture Renderer.
Designed for 10-Minute Long-Form Tutorials on Channel B (Debate Protocol / Coding Masterclass).

Layout:
  - Canvas: 1920 x 1080 (Dark Studio Canvas)
  - Left Container (1080 x 920): Tokyo Night IDE Window with Syntax Highlighting & Line Numbers
  - Right Container (680 x 920): Concept Diagram Card, Bullet Takeaways & Terminal Output Preview
"""

import os
from pathlib import Path
from typing import List, Dict, Union, Any, Optional
from PIL import Image, ImageDraw, ImageFont

import pygments
from pygments.lexers import PythonLexer, get_lexer_by_name
from pygments.token import Token

TOKYO_NIGHT = {
    "canvas_bg": (15, 17, 26, 255),         # #0f111a Studio backdrop
    "card_bg": (26, 27, 38, 255),           # #1a1b26 Editor background
    "card_border": (65, 72, 104, 255),      # #414868 Window border
    "header_bg": (36, 40, 59, 255),         # #24283b Window titlebar
    "title_text": (192, 202, 245, 255),     # #c0caf5 Light periwinkle
    "line_num": (86, 95, 137, 255),         # #565f89 Muted line numbers
    "accent_blue": (59, 130, 246, 255),     # Badge blue
    "accent_cyan": (13, 185, 238, 255),     # Output cyan
    "accent_green": (158, 206, 106, 255),   # Success / tip green
    "accent_orange": (255, 158, 100, 255),  # Warning / gotcha orange
    "accent_purple": (187, 154, 247, 255),  # Theory purple
    "sidebar_bg": (22, 23, 34, 255),        # #161722 Right pane background
    
    # Mac window controls
    "btn_red": (247, 118, 142, 255),
    "btn_yellow": (224, 175, 104, 255),
    "btn_green": (158, 206, 106, 255),
    
    # Syntax tokens
    Token.Text: (192, 202, 245),
    Token.Keyword: (187, 154, 247),
    Token.Keyword.Constant: (255, 158, 100),
    Token.Name.Function: (122, 162, 247),
    Token.Name.Class: (13, 185, 238),
    Token.Name.Builtin: (122, 162, 247),
    Token.String: (158, 206, 106),
    Token.Number: (255, 158, 100),
    Token.Operator: (137, 221, 255),
    Token.Punctuation: (192, 202, 245),
    Token.Comment: (86, 95, 137),
}

def get_font(size: int = 24, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        "C:\\Windows\\Fonts\\consolab.ttf" if bold else "C:\\Windows\\Fonts\\consola.ttf",
        "C:\\Windows\\Fonts\\arialbd.ttf" if bold else "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\courbd.ttf" if bold else "C:\\Windows\\Fonts\\cour.ttf"
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()

def draw_rounded_rect(draw: ImageDraw.Draw, box: tuple, radius: int, fill: tuple, outline: tuple = None, width: int = 1):
    x1, y1, x2, y2 = box
    draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=fill, outline=outline, width=width)

def render_longform_horizontal_card(
    code_snippet: List[str],
    module_number: int,
    module_title: str,
    key_takeaways: List[str],
    output_preview: Optional[List[str]] = None,
    output_path: Optional[str] = None,
    language: str = "python"
) -> Image.Image:
    """
    Renders a native 1920x1080 horizontal split-screen card:
      - Left: Tokyo Night code editor with line numbers and syntax highlighting.
      - Right: Concept takeaways card and expected runtime output.
    """
    canvas_w, canvas_h = 1920, 1080
    img = Image.new("RGBA", (canvas_w, canvas_h), TOKYO_NIGHT["canvas_bg"])
    draw = ImageDraw.Draw(img)

    # ── Decorative Header Banner ───────────────────────────────────────────────
    font_brand = get_font(22, bold=True)
    draw.text((70, 42), f"PYTHON ZERO-TO-HERO MASTERCLASS", fill=TOKYO_NIGHT["accent_cyan"], font=font_brand)
    
    font_mod = get_font(22, bold=False)
    draw.text((600, 42), f"•  MODULE {module_number}: {module_title.upper()}", fill=TOKYO_NIGHT["title_text"], font=font_mod)

    # ── Left Container: Code Editor Window (1080 x 920) ─────────────────────────
    left_x1, left_y1 = 70, 90
    left_w, left_h = 1100, 920
    left_x2, left_y2 = left_x1 + left_w, left_y1 + left_h

    # Editor card background & border
    draw_rounded_rect(draw, (left_x1, left_y1, left_x2, left_y2), radius=16, fill=TOKYO_NIGHT["card_bg"], outline=TOKYO_NIGHT["card_border"], width=2)

    # Titlebar (Header)
    header_h = 56
    draw_rounded_rect(draw, (left_x1, left_y1, left_x2, left_y1 + header_h), radius=16, fill=TOKYO_NIGHT["header_bg"])
    draw.rectangle([left_x1, left_y1 + 20, left_x2, left_y1 + header_h], fill=TOKYO_NIGHT["header_bg"])
    draw.line([(left_x1, left_y1 + header_h), (left_x2, left_y1 + header_h)], fill=TOKYO_NIGHT["card_border"], width=1)

    # Mac window buttons
    btn_y = left_y1 + 28
    draw.ellipse([left_x1 + 24, btn_y - 7, left_x1 + 38, btn_y + 7], fill=TOKYO_NIGHT["btn_red"])
    draw.ellipse([left_x1 + 48, btn_y - 7, left_x1 + 62, btn_y + 7], fill=TOKYO_NIGHT["btn_yellow"])
    draw.ellipse([left_x1 + 72, btn_y - 7, left_x1 + 86, btn_y + 7], fill=TOKYO_NIGHT["btn_green"])

    # Filename title in header
    font_tab = get_font(20, bold=True)
    filename = f"module_{module_number:02d}_{language}.py"
    draw.text((left_x1 + 110, left_y1 + 17), filename, fill=TOKYO_NIGHT["title_text"], font=font_tab)

    # Language badge
    badge_w, badge_h = 100, 30
    bx1 = left_x2 - badge_w - 20
    by1 = left_y1 + 13
    draw_rounded_rect(draw, (bx1, by1, bx1 + badge_w, by1 + badge_h), radius=6, fill=TOKYO_NIGHT["accent_blue"])
    font_badge = get_font(16, bold=True)
    draw.text((bx1 + 18, by1 + 6), "PYTHON", fill=(255, 255, 255, 255), font=font_badge)

    # Code Rendering with Pygments
    code_text = "\n".join(code_snippet)
    lexer = PythonLexer()
    tokens = list(pygments.lex(code_text, lexer))

    font_code = get_font(26, bold=False)
    font_linenum = get_font(24, bold=False)
    line_h = 38
    gutter_w = 60
    code_start_x = left_x1 + 30
    code_start_y = left_y1 + header_h + 30

    lines = code_text.split("\n")
    # Draw line numbers
    for i in range(len(lines)):
        curr_y = code_start_y + i * line_h
        if curr_y + line_h > left_y2 - 20:
            break
        num_str = f"{i+1:2d}"
        draw.text((code_start_x, curr_y), num_str, fill=TOKYO_NIGHT["line_num"], font=font_linenum)

    # Vertical separator line
    sep_x = code_start_x + gutter_w + 10
    draw.line([(sep_x, code_start_y - 10), (sep_x, left_y2 - 30)], fill=(45, 50, 75, 255), width=1)

    # Draw syntax-highlighted tokens
    cursor_x = sep_x + 20
    curr_line_idx = 0
    curr_y = code_start_y

    for token_type, text in tokens:
        color = TOKYO_NIGHT.get(token_type, TOKYO_NIGHT[Token.Text])
        
        # Handle newlines
        if "\n" in text:
            parts = text.split("\n")
            for idx, part in enumerate(parts):
                if part:
                    draw.text((cursor_x, curr_y), part, fill=color, font=font_code)
                    cursor_x += draw.textlength(part, font=font_code)
                if idx < len(parts) - 1:
                    curr_line_idx += 1
                    curr_y = code_start_y + curr_line_idx * line_h
                    cursor_x = sep_x + 20
        else:
            if curr_y + line_h <= left_y2 - 20:
                draw.text((cursor_x, curr_y), text, fill=color, font=font_code)
                cursor_x += draw.textlength(text, font=font_code)

    # ── Right Container: Concept & Output Card (660 x 920) ───────────────────────
    right_x1 = left_x2 + 30
    right_y1 = left_y1
    right_w = 1920 - right_x1 - 70
    right_x2 = right_x1 + right_w
    right_y2 = right_y1 + left_h

    # Card background & border
    draw_rounded_rect(draw, (right_x1, right_y1, right_x2, right_y2), radius=16, fill=TOKYO_NIGHT["sidebar_bg"], outline=TOKYO_NIGHT["card_border"], width=2)

    # Right Card Header
    draw_rounded_rect(draw, (right_x1, right_y1, right_x2, right_y1 + header_h), radius=16, fill=TOKYO_NIGHT["header_bg"])
    draw.rectangle([right_x1, right_y1 + 20, right_x2, right_y1 + header_h], fill=TOKYO_NIGHT["header_bg"])
    draw.line([(right_x1, right_y1 + header_h), (right_x2, right_y1 + header_h)], fill=TOKYO_NIGHT["card_border"], width=1)

    font_aside_title = get_font(20, bold=True)
    draw.text((right_x1 + 30, right_y1 + 17), "CORE CONCEPTS & MENTAL MODELS", fill=TOKYO_NIGHT["accent_purple"], font=font_aside_title)

    # Key Takeaways / Concept Points
    content_y = right_y1 + header_h + 35
    font_point_title = get_font(22, bold=True)
    font_point_body = get_font(19, bold=False)

    for p_idx, pt in enumerate(key_takeaways[:4]):
        bullet_box = (right_x1 + 30, content_y + 4, right_x1 + 42, content_y + 16)
        draw.rectangle(bullet_box, fill=TOKYO_NIGHT["accent_cyan"])
        
        # Split point into title and detail if colon exists
        if ":" in pt:
            p_head, p_tail = pt.split(":", 1)
            draw.text((right_x1 + 55, content_y), p_head + ":", fill=TOKYO_NIGHT["title_text"], font=font_point_title)
            content_y += 32
            # Wrap tail text
            words = p_tail.strip().split()
            cur_line = ""
            for w in words:
                test_l = (cur_line + " " + w).strip()
                if draw.textlength(test_l, font=font_point_body) < (right_w - 90):
                    cur_line = test_l
                else:
                    draw.text((right_x1 + 55, content_y), cur_line, fill=(160, 170, 200, 255), font=font_point_body)
                    content_y += 28
                    cur_line = w
            if cur_line:
                draw.text((right_x1 + 55, content_y), cur_line, fill=(160, 170, 200, 255), font=font_point_body)
                content_y += 35
        else:
            draw.text((right_x1 + 55, content_y), pt, fill=TOKYO_NIGHT["title_text"], font=font_point_body)
            content_y += 45

    # ── Terminal Output Box (Lower Right) ──────────────────────────────────────
    term_h = 240
    term_y1 = right_y2 - term_h - 30
    term_y2 = right_y2 - 30
    term_x1 = right_x1 + 25
    term_x2 = right_x2 - 25

    draw_rounded_rect(draw, (term_x1, term_y1, term_x2, term_y2), radius=10, fill=(12, 14, 20, 255), outline=(40, 45, 65, 255), width=1)
    
    # Terminal header bar
    draw.rectangle([term_x1, term_y1, term_x2, term_y1 + 36], fill=(20, 24, 34, 255))
    draw.line([(term_x1, term_y1 + 36), (term_x2, term_y1 + 36)], fill=(40, 45, 65, 255), width=1)
    font_term_hdr = get_font(16, bold=True)
    draw.text((term_x1 + 18, term_y1 + 10), "TERMINAL EXECUTION OUTPUT", fill=(130, 140, 170, 255), font=font_term_hdr)

    # Terminal output lines
    font_term_text = get_font(18, bold=False)
    t_y = term_y1 + 50
    default_out = output_preview if output_preview else ["> python " + filename, "[Process finished with exit code 0]"]
    for out_line in default_out[:5]:
        line_color = TOKYO_NIGHT["accent_green"] if out_line.startswith(">") or "Success" in out_line else (200, 210, 235, 255)
        draw.text((term_x1 + 20, t_y), out_line, fill=line_color, font=font_term_text)
        t_y += 30

    if output_path:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(out_p), format="PNG")
        print(f"[HORIZONTAL CARD] Saved 1080p card to: {out_p}")

    return img
