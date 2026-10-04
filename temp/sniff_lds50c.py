import serial
import time

def sniff_lds50c(port, baudrate):
    print(f"Sniffing {port} at {baudrate} for LDS-50C (Header: CE FA)...")
    try:
        ser = serial.Serial(port, baudrate, timeout=2)
        # LDS-50C might need a start command, but usually these send data automatically
        # Let's just read and look for CE FA
        start_time = time.time()
        buffer = b""
        while time.time() - start_time < 5:
            data = ser.read(1024)
            if data:
                buffer += data
                if b'\xce\xfa' in buffer:
                    idx = buffer.find(b'\xce\xfa')
                    print(f"!!! FOUND HEADER CE FA at index {idx} !!!")
                    print(f"Hex snippet: {buffer[idx:idx+20].hex(' ')}")
                    # Try to parse N
                    if len(buffer) > idx + 4:
                        n_points = int.from_bytes(buffer[idx+2:idx+4], byteorder='little')
                        print(f"Potential N points: {n_points}")
                    return True
                if len(buffer) > 2048:
                    buffer = buffer[-2:] # Keep last 2 bytes for header split
            else:
                print("No data received.")
                break
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'ser' in locals():
            ser.close()
    return False

if __name__ == "__main__":
    sniff_lds50c("/dev/ttyS1", 500000)
