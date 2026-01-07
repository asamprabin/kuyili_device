import requests

def download_audio(url, audio_file):
    print("⬇️ Downloading audio:", url)
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    with open(audio_file, "wb") as f:
        f.write(r.content)
    print("✅ Audio downloaded")