import sys
import serial
import serial.tools.list_ports
import time
import simpleaudio as sa

BAUDRATES = [9600, 115200]

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
            "USB" in p.device
            or "ACM" in p.device
            or "CP210" in p.description
            or "CH340" in p.description
            or p.device.startswith("/dev/ttyUSB")
            or p.device.startswith("/dev/ttyACM")
        ):
            ports.append(p.device)
    return ports

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

def play_audio(audio_file):
    print("🔊 Playing audio...")
    wave = sa.WaveObject.from_wave_file(audio_file)
    play = wave.play()
    play.wait_done()
    print("✅ Audio playback finished")

def make_call_and_play(mobile, audio_file):
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
                    play_audio(audio_file)

            if "NO CARRIER" in line:
                print("☎️ Call ended")
                break

    ser.close()
    print("🔌 GSM disconnected")