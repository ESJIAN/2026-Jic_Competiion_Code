
import smbus2

def scan_i2c_bus(bus_num):
    print(f"Scanning I2C bus {bus_num}...")
    try:
        bus = smbus2.SMBus(bus_num)
    except Exception as e:
        print(f"Error opening bus {bus_num}: {e}")
        return

    found_devices = []
    for addr in range(0x03, 0x78):
        try:
            # Try reading a byte
            bus.read_byte(addr)
            found_devices.append(addr)
        except OSError:
            pass
    
    bus.close()

    if found_devices:
        print(f"Bus {bus_num}: Found devices at addresses:")
        for addr in found_devices:
            print(f"0x{addr:02X}")
    else:
        print(f"Bus {bus_num}: No devices found.")

if __name__ == "__main__":
    scan_i2c_bus(5)
