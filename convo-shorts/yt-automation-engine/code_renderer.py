# -*- coding: utf-8 -*-
"""
code_renderer.py
----------------
High-quality Tokyo Night syntax-highlighted code card renderer for Pipeline 2.
Utilizes Pygments for tokenization and Pillow with TrueType fonts (Consolas) for
crisp, legible dark-mode code cards tailored to vertical 9:16 mobile screens.

Supports:
1. Multi-Language Comparison Cards (Python vs JavaScript vs Java vs C++).
2. Stacked syntax blocks with distinct language badges.
3. Clean single-snippet cards with line numbering.
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Union, Any
from PIL import Image, ImageDraw, ImageFont

import pygments
from pygments.lexers import (
    PythonLexer,
    JavascriptLexer,
    JavaLexer,
    CppLexer,
    get_lexer_by_name
)
from pygments.token import Token

# ── Tokyo Night Color Palette ────────────────────────────────────────────────
TOKYO_NIGHT = {
    "canvas_bg": (0, 0, 0, 0),             # Transparent outer padding
    "card_bg": (26, 27, 38, 252),          # #1a1b26 Tokyo Night deep background
    "card_border": (65, 72, 104, 255),     # #414868 Subtle neon border
    "header_bg": (36, 40, 59, 255),        # #24283b Window titlebar
    "title_text": (192, 202, 245),         # #c0caf5 Light periwinkle
    "line_num": (86, 95, 137),             # #565f89 Muted line numbers
    
    # Mac window buttons
    "btn_red": (247, 118, 142),            # #f7768e
    "btn_yellow": (224, 175, 104),         # #e0af68
    "btn_green": (158, 206, 106),          # #9ece6a
    
    # Language Badges
    "badge_python": (59, 130, 246),        # Blue
    "badge_js": (234, 179, 8),             # Yellow
    "badge_java": (239, 68, 68),           # Red
    "badge_cpp": (168, 85, 247),           # Purple
    "badge_default": (99, 102, 241),       # Indigo
    
    # Syntax Tokens
    Token.Text: (192, 202, 245),           # #c0caf5 Default text
    Token.Keyword: (187, 154, 247),        # #bb9af7 Purple keyword
    Token.Keyword.Constant: (255, 158, 100), # #ff9e64 Orange constant
    Token.Name.Function: (122, 162, 247),  # #7aa2f7 Blue function name
    Token.Name.Class: (13, 185, 238),      # #0db9d7 Cyan class name
    Token.Name.Builtin: (122, 162, 247),   # #7aa2f7 Builtin name
    Token.String: (158, 206, 106),         # #9ece6a Green string
    Token.Number: (255, 158, 100),         # #ff9e64 Orange numbers
    Token.Operator: (137, 221, 255),       # #89ddff Cyan operators
    Token.Punctuation: (192, 202, 245),    # #c0caf5 Punctuation
    Token.Comment: (86, 95, 137),          # #565f89 Muted comment
    
    # Semantic Highlights
    "junior_bad": (247, 118, 142),
    "senior_good": (158, 206, 106),
    "shadow": (0, 0, 0, 140)               # Drop shadow
}

LANGUAGE_BADGE_COLORS = {
    "python": TOKYO_NIGHT["badge_python"],
    "py": TOKYO_NIGHT["badge_python"],
    "javascript": TOKYO_NIGHT["badge_js"],
    "js": TOKYO_NIGHT["badge_js"],
    "typescript": TOKYO_NIGHT["badge_js"],
    "ts": TOKYO_NIGHT["badge_js"],
    "java": TOKYO_NIGHT["badge_java"],
    "c++": TOKYO_NIGHT["badge_cpp"],
    "cpp": TOKYO_NIGHT["badge_cpp"],
    "c": TOKYO_NIGHT["badge_cpp"],
}


def get_best_font(font_size: int = 30, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Attempts to load a crisp TrueType monospace font from the system."""
    font_candidates = [
        "C:\\Windows\\Fonts\\consolab.ttf" if bold else "C:\\Windows\\Fonts\\consola.ttf",
        "C:\\Windows\\Fonts\\courbd.ttf" if bold else "C:\\Windows\\Fonts\\cour.ttf",
        "C:\\Windows\\Fonts\\arialbd.ttf" if bold else "C:\\Windows\\Fonts\\arial.ttf"
    ]
    for font_path in font_candidates:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, font_size)
            except Exception:
                pass
    return ImageFont.load_default()


def get_lexer_for_lang(lang_name: str):
    """Safely retrieves pygments lexer for given language string."""
    lang_lower = lang_name.lower().strip()
    if lang_lower in ["py", "python"]:
        return PythonLexer()
    elif lang_lower in ["js", "javascript", "node"]:
        return JavascriptLexer()
    elif lang_lower in ["java"]:
        return JavaLexer()
    elif lang_lower in ["cpp", "c++", "c"]:
        return CppLexer()
    try:
        return get_lexer_by_name(lang_lower)
    except Exception:
        return PythonLexer()


def render_code_snippet_card(
    code_input: Union[List[str], Dict[str, str], str],
    title: str = "CODE COMPARISON",
    language: str = "python",
    width: int = 960,
    height: int = 720,
    output_path: str = "code_card.png"
) -> str:
    """
    Renders a 960x720 floating Tokyo Night dark-mode code card.
    Supports single code snippets as well as multi-language comparison blocks.
    """
    # 1. Normalize code input into list of sections
    sections = []
    if isinstance(code_input, dict):
        for lang_k, code_v in code_input.items():
            lines = [code_v] if isinstance(code_v, str) else list(code_v)
            sections.append({"lang": lang_k, "lines": lines})
    elif isinstance(code_input, list):
        current_lang = language
        current_lines = []
        for item in code_input:
            line_str = str(item)
            # Detect language header like "# Python", "// JavaScript", "### Java"
            header_match = re.match(r'^(?:#|//|/\*|###)\s*([a-zA-Z\+\#]+)(?:\s*:|\s*\*/)?$', line_str.strip(), re.IGNORECASE)
            if header_match:
                if current_lines:
                    sections.append({"lang": current_lang, "lines": current_lines})
                    current_lines = []
                current_lang = header_match.group(1).lower()
            else:
                current_lines.append(line_str)
        if current_lines:
            sections.append({"lang": current_lang, "lines": current_lines})
    elif isinstance(code_input, str):
        sections.append({"lang": language, "lines": code_input.splitlines()})

    if not sections:
        sections = [{"lang": language, "lines": ["// Code snippet unavailable", "let result = true;"]}]

    # 2. Create canvas with RGBA transparency for clean compositing
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 3. Draw Soft Drop Shadow
    shadow_margin = 12
    card_rect = [shadow_margin, shadow_margin, width - shadow_margin, height - shadow_margin]
    draw.rounded_rectangle(
        [card_rect[0] + 6, card_rect[1] + 8, card_rect[2] + 6, card_rect[3] + 8],
        radius=20,
        fill=TOKYO_NIGHT["shadow"]
    )

    # 4. Draw Card Body & Border
    draw.rounded_rectangle(
        card_rect,
        radius=20,
        fill=TOKYO_NIGHT["card_bg"],
        outline=TOKYO_NIGHT["card_border"],
        width=3
    )

    # 5. Draw Header Window Bar (y: 12 to 84)
    header_h = 72
    header_rect = [card_rect[0], card_rect[1], card_rect[2], card_rect[1] + header_h]
    draw.rounded_rectangle(header_rect, radius=20, fill=TOKYO_NIGHT["header_bg"])
    draw.rectangle([card_rect[0], card_rect[1] + 35, card_rect[2], card_rect[1] + header_h], fill=TOKYO_NIGHT["header_bg"])

    # Divider line under header
    draw.line(
        [(card_rect[0], card_rect[1] + header_h), (card_rect[2], card_rect[1] + header_h)],
        fill=TOKYO_NIGHT["card_border"],
        width=2
    )

    # 6. Mac OS Window Buttons
    btn_y = card_rect[1] + header_h // 2
    btn_r = 9
    btn_start_x = card_rect[0] + 36
    draw.ellipse([btn_start_x - btn_r, btn_y - btn_r, btn_start_x + btn_r, btn_y + btn_r], fill=TOKYO_NIGHT["btn_red"])
    draw.ellipse([btn_start_x + 28 - btn_r, btn_y - btn_r, btn_start_x + 28 + btn_r, btn_y + btn_r], fill=TOKYO_NIGHT["btn_yellow"])
    draw.ellipse([btn_start_x + 56 - btn_r, btn_y - btn_r, btn_start_x + 56 + btn_r, btn_y + btn_r], fill=TOKYO_NIGHT["btn_green"])

    # 7. Window Title (Bold & Crisp)
    title_font = get_best_font(26, bold=True)
    clean_title = title.upper().strip()
    draw.text((btn_start_x + 105, card_rect[1] + 20), clean_title, fill=TOKYO_NIGHT["title_text"], font=title_font)

    # 8. Multi-Language / Section Layout Calculation (SUPERSIZED FOR MOBILE)
    num_sections = len(sections)
    avail_h = (card_rect[3] - 25) - (card_rect[1] + header_h + 25)
    
    # Calculate font size & line heights based on content density (48pt to 60pt for 1-4 lines)
    total_code_lines = sum(len(s["lines"]) for s in sections)
    if total_code_lines <= 3:
        font_size = 56
        line_height = 82
        badge_font_size = 26
    elif total_code_lines <= 5:
        font_size = 50
        line_height = 72
        badge_font_size = 24
    elif total_code_lines <= 7:
        font_size = 42
        line_height = 60
        badge_font_size = 20
    else:
        font_size = 36
        line_height = 48
        badge_font_size = 18

    font_code = get_best_font(font_size, bold=True)
    font_num = get_best_font(max(20, font_size - 10), bold=False)
    font_badge = get_best_font(badge_font_size, bold=True)

    # Calculate vertical start with balanced padding
    needed_content_h = (total_code_lines * line_height) + (num_sections * (badge_font_size + 16))
    vertical_offset = max(20, (avail_h - needed_content_h) // 2) if needed_content_h < avail_h else 20
    
    curr_y = card_rect[1] + header_h + vertical_offset
    start_x = card_rect[0] + 40

    for s_idx, sec in enumerate(sections):
        sec_lang = sec["lang"].lower().strip()
        sec_lines = sec["lines"]
        badge_color = LANGUAGE_BADGE_COLORS.get(sec_lang, TOKYO_NIGHT["badge_default"])
        badge_label = sec_lang.upper()

        # Draw Language Badge
        if num_sections > 1 or sec_lang not in ["python", "code"]:
            badge_w = int(draw.textlength(badge_label, font=font_badge)) + 24
            badge_h = badge_font_size + 14
            badge_box = [start_x, curr_y, start_x + badge_w, curr_y + badge_h]
            draw.rounded_rectangle(badge_box, radius=8, fill=badge_color)
            draw.text((start_x + 12, curr_y + 5), badge_label, fill=(255, 255, 255), font=font_badge)
            curr_y += badge_h + 12

        # Tokenize code with Pygments
        lexer = get_lexer_for_lang(sec_lang)
        code_text = "\n".join(sec_lines)
        tokens = list(pygments.lex(code_text, lexer))

        line_no = 1
        num_col_w = 60 if font_size >= 48 else 45
        curr_x = start_x + num_col_w
        draw.text((start_x, curr_y + 4), f"{line_no:2d}", fill=TOKYO_NIGHT["line_num"], font=font_num)

        for tok_type, val in tokens:
            if "\n" in val:
                lines = val.split("\n")
                for l_idx, sub_val in enumerate(lines):
                    if sub_val:
                        col = TOKYO_NIGHT.get(tok_type, TOKYO_NIGHT[Token.Text])
                        if not isinstance(col, tuple):
                            col = TOKYO_NIGHT.get(tok_type.parent, TOKYO_NIGHT[Token.Text])
                        draw.text((curr_x, curr_y), sub_val, fill=col, font=font_code)
                        curr_x += int(draw.textlength(sub_val, font=font_code))

                    if l_idx < len(lines) - 1:
                        curr_y += line_height
                        if curr_y > card_rect[3] - 25:
                            break
                        line_no += 1
                        curr_x = start_x + num_col_w
                        # Draw next line number
                        draw.text((start_x, curr_y + 4), f"{line_no:2d}", fill=TOKYO_NIGHT["line_num"], font=font_num)
            else:
                col = TOKYO_NIGHT.get(tok_type, TOKYO_NIGHT[Token.Text])
                if not isinstance(col, tuple):
                    col = TOKYO_NIGHT.get(tok_type.parent, TOKYO_NIGHT[Token.Text])
                draw.text((curr_x, curr_y), val, fill=col, font=font_code)
                curr_x += int(draw.textlength(val, font=font_code))

        curr_y += line_height + 10
        if curr_y > card_rect[3] - 30:
            break

    # 9. Save Output PNG
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_file, "PNG")
    return str(out_file)
