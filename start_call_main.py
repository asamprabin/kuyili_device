import serial
import serial.tools.list_ports
import time
import sys

PHONE_NUMBER = "+919092089717"
BAUDRATES = [9600, 115200]

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
            except:
                ser = None
        if ser:
            break

    if not ser:
        print("❌ GSM module not responding on any USB port")
        sys.exit(1)

    send_cmd(ser, "ATE0")
    send_cmd(ser, "AT+CSQ")
    send_cmd(ser, "AT+CREG?")

    send_cmd(ser, f"ATD{PHONE_NUMBER};", delay=3)
    print("📞 CALLING...")

    try:
        while True:
            if ser.in_waiting:
                print(ser.readline().decode(errors="ignore").strip())
    except KeyboardInterrupt:
        send_cmd(ser, "ATH")
        ser.close()
        print("☎️ Call ended")

if __name__ == "__main__":
    main()
