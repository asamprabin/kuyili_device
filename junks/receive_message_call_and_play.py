import serial
import serial.tools.list_ports
import time
import sys
import simpleaudio as sa
import requests
import json
import os

import paho.mqtt.client as mqtt

# ================= MQTT CONFIG =================

BROKER = "e0cce88517644183b5332d1aabbee868.s1.eu.hivemq.cloud"
PORT = 8883
USERNAME = "edge_admin"
PASSWORD = "Q2JNzkZh.K8@_ee"
TOPIC = "voice-tasks"

# ================= GSM CONFIG =================

BAUDRATES = [9600, 115200]
AUDIO_FILE = "../incoming.wav"

busy = False

# =================================================


def get_usb_serial_ports():
    ports = []
    for p in serial.tools.list_ports.comports():
        if (
            "USB" in p.device
            or "ACM" in p.device
            or "CP210" in p.description
            or "CH340" in p.description
            or p.device.startswith("/dev/ttyUSB")
            or p.device.startswith("/dev/ttyACM")
        ):
            ports.append(p.device)
    return ports


def send_cmd(ser, cmd, delay=1):
    print(f">> {cmd}")
    ser.write((cmd + "\r").encode())
    time.sleep(delay)
    while ser.in_waiting:
        print(ser.readline().decode(errors="ignore").strip())


def detect_gsm():
    ports = get_usb_serial_ports()
    if not ports:
        print("❌ No GSM device found")
        sys.exit(1)

    for port in ports:
        for baud in BAUDRATES:
            try:
                print(f"🔄 Trying {port} @ {baud}")
                ser = serial.Serial(port, baudrate=baud, timeout=1)
                time.sleep(2)
                ser.write(b"AT\r")
                time.sleep(1)

                if ser.in_waiting:
                    resp = ser.read(ser.in_waiting).decode(errors="ignore")
                    if "OK" in resp:
                        print(f"✅ GSM detected on {port} @ {baud}")
                        return ser
                ser.close()
            except Exception:
                pass

    print("❌ GSM not responding")
    sys.exit(1)


def download_audio(url):
    print("⬇️ Downloading audio:", url)
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    with open(AUDIO_FILE, "wb") as f:
        f.write(r.content)
    print("✅ Audio downloaded")


def play_audio():
    print("🔊 Playing audio...")
    wave = sa.WaveObject.from_wave_file(AUDIO_FILE)
    play = wave.play()
    play.wait_done()
    print("✅ Audio playback finished")


def make_call_and_play(mobile):
    ser = detect_gsm()

    send_cmd(ser, "ATE0")
    send_cmd(ser, "AT+CSQ")
    send_cmd(ser, "AT+CREG?")

    send_cmd(ser, f"ATD{mobile};", delay=3)
    print("📞 Calling:", mobile)

    call_connected = False
    last_check = 0

    while True:
        if time.time() - last_check > 1:
            last_check = time.time()
            ser.write(b"AT+CLCC\r")

        if ser.in_waiting:
            line = ser.readline().decode(errors="ignore").strip()
            if not line:
                continue

            print(line)

            if "+CLCC:" in line:
                parts = line.split(",")
                if len(parts) > 2 and parts[2].strip() == "0" and not call_connected:
                    call_connected = True
                    print("✅ Call answered")
                    play_audio()

            if "NO CARRIER" in line:
                print("☎️ Call ended")
                break

    ser.close()
    print("🔌 GSM disconnected")


# ================= MQTT CALLBACKS =================

def on_connect(client, userdata, flags, rc):
    print("🔗 Connected to HiveMQ with code:", rc)
    client.subscribe(TOPIC, qos=1)


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

        download_audio(audio_url)
        make_call_and_play(mobile)

        print("✅ Job completed successfully")

    except Exception as e:
        print("❌ Job failed:", e)

    busy = False
    # ACK is sent automatically AFTER this function returns (QoS 1)


# ================= MAIN =================

def main():
    client = mqtt.Client(
        client_id="device-001",
        clean_session=False
    )

    client.username_pw_set(USERNAME, PASSWORD)
    client.tls_set()

    client.on_connect = on_connect
    client.on_message = on_message

    print("🚀 Connecting to HiveMQ Cloud...")
    client.connect(BROKER, PORT, keepalive=60)
    client.loop_forever()


if __name__ == "__main__":
    main()
