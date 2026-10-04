import socket
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(('0.0.0.0', 11811))
print("正在等待 RDK 的消息...")
while True:
    data, addr = s.recvfrom(1024)
    try:
        print(f"来自 {addr} 的消息: {data.decode('utf-8')}")
    except UnicodeDecodeError:
        print(f"来自 {addr} 的消息 (非 UTF-8): {data.decode('gbk', errors='ignore')}")


