import serial
import serial.tools.list_ports
import time
import sys
import threading
import simpleaudio as sa

# ================= CONFIG =================

PHONE_NUMBER = "+919092089717"
BAUDRATES = [9600, 115200]
AUDIO_FILE = "voice.wav"   # WAV file to play after call is answered

# =========================================


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


def play_audio():
    try:
        print("🔊 Playing audio on PC...")
        wave_obj = sa.WaveObject.from_wave_file(AUDIO_FILE)
        play_obj = wave_obj.play()
        play_obj.wait_done()
        print("✅ Audio playback completed")
    except Exception as e:
        print("❌ Audio error:", e)


def main():
    ports = get_usb_serial_ports()

    if not ports:
        print("❌ No USB GSM serial device found")
        sys.exit(1)

    print("🔍 Found ports:", ports)

    ser = None
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
                    print("📡 Response:", resp.strip())
                    if "OK" in resp:
                        print(f"✅ GSM detected on {port} @ {baud}")
                        break

                ser.close()
                ser = None
            except Exception:
                ser = None

        if ser:
            break

    if not ser:
        print("❌ GSM module not responding")
        sys.exit(1)

    # Basic GSM setup
    send_cmd(ser, "ATE0")
    send_cmd(ser, "AT+CSQ")
    send_cmd(ser, "AT+CREG?")

    # Dial call
    send_cmd(ser, f"ATD{PHONE_NUMBER};", delay=3)
    print("📞 CALLING... Waiting for answer")

    call_connected = False
    last_clcc_check = 0

    try:
        while True:
            # Poll call status every 1 second
            if time.time() - last_clcc_check > 1:
                last_clcc_check = time.time()
                ser.write(b"AT+CLCC\r")

            if ser.in_waiting:
                line = ser.readline().decode(errors="ignore").strip()
                if not line:
                    continue

                print(line)

                # +CLCC format:
                # +CLCC: <idx>,<dir>,<stat>,<mode>,<mpty>,<number>,<type>

                if "+CLCC:" in line:
                    parts = line.split(",")

                    if len(parts) > 2:
                        call_state = parts[2].strip()

                        # stat = 0 → ACTIVE (answered)
                        if call_state == "0" and not call_connected:
                            call_connected = True
                            print("✅ Call answered (ACTIVE)")

                            threading.Thread(
                                target=play_audio,
                                daemon=True
                            ).start()

                # Call ended
                if "NO CARRIER" in line:
                    print("☎️ Call ended")
                    break

    except KeyboardInterrupt:
        print("🛑 Interrupted by user")
        send_cmd(ser, "ATH")

    ser.close()
    print("🔌 GSM disconnected")


if __name__ == "__main__":
    main()
