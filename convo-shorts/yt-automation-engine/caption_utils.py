# -*- coding: utf-8 -*-
"""
caption_utils.py
----------------
Standalone caption alignment and ASS file generation utilities for Pipeline 2 (convo-shorts).
Generates v4.00+ ASS subtitle files with native 1080x1920 styling and dual-speaker highlighting.
"""

import logging

def format_ass_timestamp(seconds: float) -> str:
    """Formats seconds into ASS timestamp format H:MM:SS.cs"""
    cs = int(round(seconds * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def map_color_to_ass(color_name: str) -> str:
    """Maps human readable colors or hex values to ASS ABGR formatting."""
    color_map = {
        "white": "&H00FFFFFF",
        "black": "&H00000000",
        "cyan": "&H00FFFF00",
        "magenta": "&H00FF00FF",
        "yellow": "&H0000FFFF",
    }
    color_name = color_name.lower().strip()
    if color_name in color_map:
        return color_map[color_name]
    if color_name.startswith("&h"):
        return color_name
    return "&H00FFFFFF"

def align_and_generate_ass(
    whisper_words: list, 
    original_text: str, 
    style_cfg: dict, 
    max_words: int = 3, 
    max_chars: int = 15,
    is_debate: bool = False,
    speaker_colors: dict = None
) -> str:
    """
    Aligns Whisper's word timestamps with exact script spelling,
    then generates a v4.00+ ASS subtitle file with native 1080x1920 styling.
    Supports dual-speaker highlighting if is_debate=True.
    """
    orig_words = original_text.split()
    aligned = []
    orig_idx = 0
    
    for w_word in whisper_words:
        speaker = w_word.get("speaker", "narrator")
        word = w_word["word"]
        
        if orig_idx < len(orig_words):
            word = orig_words[orig_idx]
            orig_idx += 1
            
        aligned.append({
            "word": word,
            "start": w_word["start"],
            "end": w_word["end"],
            "speaker": speaker
        })
            
    # Catch any remaining words in script
    while orig_idx < len(orig_words) and aligned:
        aligned.append({
            "word": orig_words[orig_idx],
            "start": aligned[-1]["end"],
            "end": aligned[-1]["end"] + 0.2,
            "speaker": aligned[-1].get("speaker", "narrator")
        })
        orig_idx += 1
        
    # Group words into natural linguistic phrases
    chunks = []
    chunk = []
    chunk_chars = 0
    
    NON_SPLIT_WORDS = {
        "a", "an", "the", "in", "on", "of", "to", "at", "by", "for", "with", "from",
        "like", "that", "this", "it's", "they're", "you're", "we're", "and", "or", "but"
    }
    
    for word_info in aligned:
        w_text = word_info["word"].strip()
        w_lower = w_text.lower().strip(".,!?\"'")
        
        if not chunk:
            chunk.append(word_info)
            chunk_chars = len(w_text)
        else:
            prev_word = chunk[-1]["word"].strip().lower().strip(".,!?\"'")
            is_prev_non_split = prev_word in NON_SPLIT_WORDS
            
            if len(chunk) >= 4 or (chunk_chars + len(w_text) + 1 > max_chars and not is_prev_non_split and len(chunk) >= 2):
                chunks.append(chunk)
                chunk = [word_info]
                chunk_chars = len(w_text)
            else:
                chunk.append(word_info)
                chunk_chars += len(w_text) + 1
            
    if chunk:
        chunks.append(chunk)
        
    # Build ASS style header
    font = style_cfg.get("font", "Impact")
    bold = "1" if "bold" in font.lower() else "0"
    if "bold" in font.lower():
        font = font.replace("Bold", "").replace("bold", "").strip()
        
    size = style_cfg.get("size", 90)
    color = map_color_to_ass(style_cfg.get("color", "white"))
    out_color = map_color_to_ass(style_cfg.get("outline_color", "black"))
    out_width = style_cfg.get("outline_width", 5)
    shadow = style_cfg.get("shadow", 3)
    margin_v = style_cfg.get("margin_v", 400 if is_debate else 350)
    margin_l = style_cfg.get("margin_l", 20)
    margin_r = style_cfg.get("margin_r", 20)
    alignment = 2
    
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{size},{color},&H000000FF,{out_color},&H00000000,{bold},0,0,0,100,100,0,0,1,{out_width},{shadow},{alignment},{margin_l},{margin_r},{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    default_speaker_colors = {
        "a": "&H00FFFF00&",
        "b": "&H00FF00FF&",
        "character_a": "&H00FFFF00&",
        "character_b": "&H00FF00FF&",
        "narrator": "&H00FFFFFF&"
    }
    if speaker_colors:
        for k, v in speaker_colors.items():
            ass_color = map_color_to_ass(v)
            default_speaker_colors[k.lower()] = ass_color if ass_color.endswith('&') else f"{ass_color}&"
        
    events = []
    for chunk in chunks:
        for target_idx, w_target in enumerate(chunk):
            w_start = w_target["start"]
            w_end = chunk[target_idx + 1]["start"] if target_idx < len(chunk) - 1 else w_target["end"] + 0.1
                
            word_start_str = format_ass_timestamp(w_start)
            word_end_str = format_ass_timestamp(w_end)
            
            text_parts = []
            for idx, word_info in enumerate(chunk):
                word_text = word_info["word"].upper()
                spk = word_info.get("speaker", "narrator").lower()
                spk_color = default_speaker_colors.get(spk, "&H00FFFFFF&")
                
                if idx == target_idx:
                    text_parts.append(f"{{\\c{spk_color}\\fscx115\\fscy115}}{word_text}{{\\fscx100\\fscy100}}")
                else:
                    text_parts.append(f"{{\\c&HFFFFFF&}}{word_text}")
                    
            event_text = " ".join(text_parts)
            events.append(f"Dialogue: 0,{word_start_str},{word_end_str},Default,,0,0,0,,{event_text}")
            
    return header + "\n".join(events) + "\n"
