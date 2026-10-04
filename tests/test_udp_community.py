"""UDP 社区通信监听工具（手动脚本，非自动化测试）。

用于监听 RDK 端发来的 UDP 广播/单播消息并打印。

运行方式：
    python3 tests/test_udp_community.py
"""

import socket

PORT = 11811


def main() -> None:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(('0.0.0.0', PORT))
    print(f"正在等待 RDK 的消息 (UDP/{PORT})...")
    try:
        while True:
            data, addr = s.recvfrom(1024)
            try:
                print(f"来自 {addr} 的消息: {data.decode('utf-8')}")
            except UnicodeDecodeError:
                print(f"来自 {addr} 的消息 (非 UTF-8): {data.decode('gbk', errors='ignore')}")
    except KeyboardInterrupt:
        print("\n已停止监听。")
    finally:
        s.close()


if __name__ == '__main__':
    main()
