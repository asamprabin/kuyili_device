#!/usr/bin/env python3
import sys
import time
import json
import queue
import threading
import serial
import serial.tools.list_ports
import subprocess
import requests

# ================= CONFIG =================

BAUDRATES = [9600, 115200]
ALSA_DEVICE = "plughw:1,0"
DOWNLOAD_FILE = "voice.wav"

# =========================================

job_queue = queue.Queue()
gsm_lock = threading.Lock()

# ---------- GSM HELPERS ----------

def send_cmd(ser, cmd, delay=1):
    print(f">> {cmd}")
    ser.write((cmd + "\r").encode())
    time.sleep(delay)
    while ser.in_waiting:
        print(ser.readline().decode(errors="ignore").strip())


def get_usb_serial_ports():
    ports = []
    for p in serial.tools.list_ports.comports():
        if (
            p.device.startswith("/dev/ttyUSB")
            or p.device.startswith("/dev/ttyACM")
            or "CP210" in p.description
            or "CH340" in p.description
        ):
            ports.append(p.device)
    return ports


def detect_gsm():
    for port in get_usb_serial_ports():
        for baud in BAUDRATES:
            try:
                print(f"🔄 Trying {port} @ {baud}")
                ser = serial.Serial(port, baudrate=baud, timeout=1)
                time.sleep(2)
                ser.write(b"AT\r")
                time.sleep(1)
                if ser.in_waiting and b"OK" in ser.read(ser.in_waiting):
                    print(f"✅ GSM detected on {port} @ {baud}")
                    return ser
                ser.close()
            except:
                pass

    raise RuntimeError("GSM modem not detected")


def play_audio(audio_file):
    print("🔊 Playing audio...")
    subprocess.run(
        ["aplay", "-D", ALSA_DEVICE, audio_file],
        check=True
    )


def make_call_and_play(mobile, audio_file):
    with gsm_lock:  # 🔒 ENSURES ONE CALL AT A TIME
        print(f"📞 Starting call job for {mobile}")

        ser = detect_gsm()

        send_cmd(ser, "ATE0")
        send_cmd(ser, "AT+CSQ")
        send_cmd(ser, "AT+CREG?")

        send_cmd(ser, f"ATD{mobile};", delay=3)

        call_connected = False
        last_check = 0

        while True:
            if time.time() - last_check > 1:
                last_check = time.time()
                ser.write(b"AT+CLCC\r")

            if ser.in_waiting:
                line = ser.readline().decode(errors="ignore").strip()
                print(line)

                if "+CLCC:" in line:
                    parts = line.split(",")
                    if len(parts) > 2 and parts[2].strip() == "0":
                        if not call_connected:
                            call_connected = True
                            print("✅ Call answered")
                            play_audio(audio_file)
                            send_cmd(ser, "ATH", delay=2)
                            break

                if "NO CARRIER" in line:
                    print("☎️ Call ended")
                    break

            time.sleep(0.1)

        ser.close()
        print("🔌 GSM released")

# ---------- QUEUE WORKER ----------

def worker():
    while True:
        job = job_queue.get()
        try:
            make_call_and_play(job["mobile"], job["audio"])
            print("✅ Job completed")
        except Exception as e:
            print("❌ Job failed:", e)
        finally:
            job_queue.task_done()


# ---------- MQTT CALLBACK ----------

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        print("📩 Job received:", payload)

        audio_url = payload["audio_url"]
        mobile = payload["mobile"]

        print("⬇️ Downloading audio...")
        r = requests.get(audio_url, timeout=10)
        r.raise_for_status()

        with open(DOWNLOAD_FILE, "wb") as f:
            f.write(r.content)

        job_queue.put({
            "mobile": mobile,
            "audio": DOWNLOAD_FILE
        })

        print("📥 Job queued")

    except Exception as e:
        print("❌ Invalid job:", e)

# ---------- START ----------

if __name__ == "__main__":
    threading.Thread(target=worker, daemon=True).start()
    print("🚀 GSM Worker started (ONE JOB AT A TIME)")
