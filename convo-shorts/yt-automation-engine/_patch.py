"""Patch assemble_video in media_engine.py with a Windows-safe FFmpeg call."""
content = open('media_engine.py', encoding='utf-8').read()

start_marker = 'def assemble_video('
end_marker   = '\ndef generate_thumbnail('

start = content.find(start_marker)
end   = content.find(end_marker)

if start == -1 or end == -1:
    raise RuntimeError(f"Markers not found. start={start} end={end}")

new_func = '''def assemble_video(video_bg_path, audio_path,
                   subtitle_data, final_output_path,
                   category="Weird Science"):
    """
    Compose the final 9:16 MP4 with burned-in word subtitles.
    Uses shell=True + forward-slash paths to avoid Windows ASS-filter escaping issues.
    """
    import shutil
    ass_path = str(Path(final_output_path).parent / "subs.ass")
    _write_ass(subtitle_data, ass_path, category)

    # Forward-slash paths for FFmpeg (works on Windows too)
    ass_fwd  = ass_path.replace("\\\\", "/").replace("\\", "/").replace(":", "\\\\:")
    bg_fwd   = video_bg_path.replace("\\\\", "/").replace("\\", "/")
    audio_fwd= audio_path.replace("\\\\", "/").replace("\\", "/")
    out_fwd  = final_output_path.replace("\\\\", "/").replace("\\", "/")

    vf = (
        f"scale={VW}:{VH}:force_original_aspect_ratio=decrease,"
        f"pad={VW}:{VH}:(ow-iw)/2:(oh-ih)/2,"
        f"boxblur=8:2,"
        f"ass=\\'{ass_fwd}\\'"
    )

    shell_cmd = (
        f\'ffmpeg -y -stream_loop -1 -i "{bg_fwd}" -i "{audio_fwd}" \'
        f\'-vf "{vf}" \'
        f\'-c:v libx264 -preset fast -crf 22 \'
        f\'-c:a aac -b:a 192k -shortest "{out_fwd}"\\'
    )

    print("[FFmpeg] Assembling video...")
    print(f"[FFmpeg] Command: {shell_cmd[:120]}...")
    result = subprocess.run(shell_cmd, shell=True, capture_output=True)

    stderr_txt = result.stderr.decode("utf-8", errors="ignore")
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed (code {result.returncode}):\\n{stderr_txt[-2000:]}")

    out_path = Path(final_output_path)
    if not out_path.exists() or out_path.stat().st_size < 10_000:
        raise RuntimeError(f"FFmpeg produced empty output.\\nstderr:\\n{stderr_txt[-2000:]}")

    print(f"[FFmpeg] Done: {out_path.name}  ({out_path.stat().st_size // 1024} KB)")
    return final_output_path

'''

new_content = content[:start] + new_func + content[end:]
open('media_engine.py', 'w', encoding='utf-8').write(new_content)
print("Patched successfully.")
