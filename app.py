from Objects.queue_subscribe import QueueSubscribe
import json
from utils.audio import download_audio
from utils.gsm import make_call_and_play

topic = "voice-tasks"
audio_file = "../incoming.wav"
busy = False

def on_connect(client, userdata, flags, rc):
    print("🔗 Connected to HiveMQ with code:", rc)
    client.subscribe(topic, qos=1)

def on_message(client, userdata, msg):
    global busy
    if busy:
        print("⚠️ Device busy, ignoring message")
        return

    busy = True
    payload = msg.payload.decode()
    print("📩 Received job:", payload)

    try:
        data = json.loads(payload)
        mobile = data["mobile"]
        audio_url = data["audio_url"]

        download_audio(audio_url, audio_file)
        make_call_and_play(mobile, audio_file)

        print("✅ Job completed successfully")

    except Exception as e:
        print("❌ Job failed:", e)

    busy = False
    # ACK is sent automatically AFTER this function returns (QoS 1)


def main():
    queue = QueueSubscribe("sam_laptop")
    queue.connect(on_connect, on_message)

if __name__ == "__main__":
    main()