import os
import urllib.request
import subprocess

def download_file(url, dest):
    print(f"Downloading {url} to {dest}...")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    try:
        urllib.request.urlretrieve(url, dest)
        print("Success.")
    except Exception as e:
        print(f"Failed to download: {e}")

if __name__ == "__main__":
    voices = {
        "kristin": {
            "onnx": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/kristin/medium/en_US-kristin-medium.onnx",
            "json": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/kristin/medium/en_US-kristin-medium.onnx.json",
            "text": "Hi, this is the Kristin voice. Do you think my tone fits the debate expert role?"
        },
        "ljspeech": {
            "onnx": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ljspeech/medium/en_US-ljspeech-medium.onnx",
            "json": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ljspeech/medium/en_US-ljspeech-medium.onnx.json",
            "text": "Hello, this is the L J Speech voice. I am a widely used female voice trained on audiobook data. How do I sound?"
        },
        "lessac": {
            "onnx": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx",
            "json": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json",
            "text": "Hey, this is the Lessac voice speaking. I am a clear, neutral female narrator model. Do you like my cadence?"
        }
    }
    
    ROOT_DIR = str(Path(__file__).parent.parent.resolve())
    temp_model_dir = os.path.join(ROOT_DIR, "models", "temp_samples")
    sample_out_dir = os.path.join(ROOT_DIR, "yt-automation-engine", "data", "assets", "samples")
    
    os.makedirs(temp_model_dir, exist_ok=True)
    os.makedirs(sample_out_dir, exist_ok=True)
    
    piper_exe = os.path.join(ROOT_DIR, "piper.exe")
    
    for name, info in voices.items():
        onnx_dest = os.path.join(temp_model_dir, f"{name}.onnx")
        json_dest = os.path.join(temp_model_dir, f"{name}.onnx.json")
        
        # Download files
        if not os.path.exists(onnx_dest):
            download_file(info["onnx"], onnx_dest)
        if not os.path.exists(json_dest):
            download_file(info["json"], json_dest)
            
        # Render sample WAV
        wav_path = os.path.join(sample_out_dir, f"sample_{name}.wav")
        print(f"Rendering sample for {name} to {wav_path}...")
        
        cmd = f'echo "{info["text"]}" | "{piper_exe}" -m "{onnx_dest}" -f "{wav_path}"'
        try:
            os.system(cmd)
            print(f"Sample generated successfully at: {wav_path}")
        except Exception as e:
            print(f"Failed to generate wav for {name}: {e}")
