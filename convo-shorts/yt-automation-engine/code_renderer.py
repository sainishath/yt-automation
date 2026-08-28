import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

DEV_THEME = {
    'bg': (18, 20, 28, 255),
    'card_bg': (24, 26, 36, 250),
    'card_border': (60, 70, 95, 255),
    'header_bg': (32, 35, 48, 255),
    'btn_red': (255, 95, 86),
    'btn_yellow': (254, 189, 46),
    'btn_green': (39, 201, 63),
    'title_text': (220, 230, 245),
    'comment_text': (130, 140, 160),
    'junior_bad': (255, 110, 110),
    'senior_good': (100, 255, 150),
    'default_code': (235, 240, 255),
    'keyword': (255, 120, 180),
    'line_no': (90, 100, 125)
}

def render_code_snippet_card(code_lines: list, title: str = 'SENIOR DEV PATTERN', output_path: str = 'code_card.png') -> str:
    w, h = 896, 896
    img = Image.new('RGBA', (w, h), DEV_THEME['bg'])
    draw = ImageDraw.Draw(img)
    card_rect = [48, 48, 848, 848]
    draw.rounded_rectangle(card_rect, radius=24, fill=DEV_THEME['card_bg'], outline=DEV_THEME['card_border'], width=3)
    draw.rounded_rectangle([48, 48, 848, 120], radius=24, fill=DEV_THEME['header_bg'])
    draw.rectangle([48, 72, 848, 120], fill=DEV_THEME['header_bg'])
    draw.ellipse([80-8, 84-8, 80+8, 84+8], fill=DEV_THEME['btn_red'])
    draw.ellipse([108-8, 84-8, 108+8, 84+8], fill=DEV_THEME['btn_yellow'])
    draw.ellipse([136-8, 84-8, 136+8, 84+8], fill=DEV_THEME['btn_green'])
    font_def = ImageFont.load_default()
    draw.text((170, 76), title.upper(), fill=DEV_THEME['title_text'], font=font_def)
    y = 150
    line_h = 42
    for i, line in enumerate(code_lines):
        if y > 800:
            break
        txt = line.strip()
        if txt.startswith('#') or txt.startswith('//'):
            col = DEV_THEME['senior_good'] if 'SENIOR' in txt or 'FIX' in txt else (DEV_THEME['junior_bad'] if 'JUNIOR' in txt or 'BUG' in txt else DEV_THEME['comment_text'])
        elif any(txt.startswith(kw) for kw in ['def ', 'return ', 'if ', 'else:', 'class ', 'import ', 'from ', 'for ', 'async ', 'await ']):
            col = DEV_THEME['keyword']
        else:
            col = DEV_THEME['default_code']
        draw.text((80, y), f'{i+1:2d}  {line}', fill=col, font=font_def)
        y += line_h
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, 'PNG')
    return str(out)
