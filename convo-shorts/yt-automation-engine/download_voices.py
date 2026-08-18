import os
import urllib.request

def download_file(url, dest):
    print(f"Downloading {url} to {dest}...")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    try:
        urllib.request.urlretrieve(url, dest)
        print("Success.")
    except Exception as e:
        print(f"Failed to download: {e}")

if __name__ == "__main__":
    base_url = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US"
    
    voices = {
        "ryan/medium/en_US-ryan-medium.onnx": "models/voices/en_US-ryan-medium.onnx",
        "ryan/medium/en_US-ryan-medium.onnx.json": "models/voices/en_US-ryan-medium.onnx.json",
        "amy/medium/en_US-amy-medium.onnx": "models/voices/en_US-amy-medium.onnx",
        "amy/medium/en_US-amy-medium.onnx.json": "models/voices/en_US-amy-medium.onnx.json"
    }
    
    # Resolve relative to convo-shorts project root
    target_dir = Path(__file__).parent.parent / "models" / "voices"
    target_dir.mkdir(parents=True, exist_ok=True)
    
    for remote_path, local_name in voices.items():
        url = f"{base_url}/{remote_path}"
        filename = os.path.basename(local_name)
        dest_path = os.path.join(target_dir, filename)
        
        if os.path.exists(dest_path):
            print(f"{filename} already exists, skipping.")
        else:
            download_file(url, dest_path)
