
import serial
import time

def sniff(port, baudrate):
    print(f"Sniffing {port} at {baudrate}...")
    try:
        ser = serial.Serial(port, baudrate, timeout=2)
        # Try to trigger a response
        ser.write(b'\xa5\x20') # GET_INFO
        time.sleep(0.1)
        data = ser.read(100)
        if data:
            print(f"Received {len(data)} bytes: {data.hex(' ')}")
            if b'\xa5\x5a' in data:
                print(f"!!! FOUND SYNC BYTES A5 5A at baudrate {baudrate} !!!")
                return True
        else:
            print("No data received.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'ser' in locals():
            ser.close()
    return False

if __name__ == "__main__":
    port = "/dev/ttyS1"
    bauds = [9600, 19200, 38400, 57600, 115200, 230400, 256000, 460800, 500000, 921600, 1000000]
    for baud in bauds:
        if sniff(port, baud):
            break
