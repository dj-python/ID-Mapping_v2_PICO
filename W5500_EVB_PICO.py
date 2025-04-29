from cmath import phase

from machine import Pin, SPI
import time
import network
import socket

tcpSocket = None

# W5x00 chip init
def init(ipAddress: str, gateway : str, server_ip : str, server_port: int) -> None:
    global tcpSocket

    try:
        # SPI 및 W5500 초기화
        spi = SPI(0, 2_000_000, polarity=0, phase=0, mosi=Pin(19), miso=Pin(16), sck=Pin(18))
        eth = network.WIZNET5K(spi, Pin(17), Pin(20))  # spi,cs,reset pin
        eth.active(True)

        # 네트워크 설정
        eth.ifconfig((ipAddress, '255.255.255.0', gateway, '8,8,8,8'))

        # TCP 클라이언트 소켓 생성 및 서버 연결
        tcpSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # 서버 접속 시도 (재시도 로직 포함)
        max_retries = 5
        retries = 0
        while retries < max_retries:
            try:
                tcpSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                tcpSocket.settimeout(10)
                tcpSocket.connect((server_ip, server_port))
                tcpSocket.setblocking(False)                                    # Non-blocking mode
                tcpSocket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)     # Keep alive
                print(f"[*] Connected to TCP Server: {server_ip} : {server_port}")
                break

            except socket.timeout:
                retries += 1
                print(f"[-] Connection to TCP Server: {server_ip} : {server_port}")
                if tcpSocket:
                    tcpSocket.close()
                time.sleep(3)
            except socket.error as e:
                retries += 1
                print(f"[-] Socket error: {e} (Attempt {retries}/{max_retries})")
                if tcpSocket:
                    tcpSocket.close()
                time.sleep(3)
            except Exception as e:
                retries += 1
                print(f"[-] Unexpected Error: {e} (Attempt {retries}/{max_retries}")
                if tcpSocket:
                    tcpSocket.close()
                time.sleep(3)
        else:
            print("[-] Failed to connect to server after maximum retries")
            tcpSocket = None        # 소켓 초기화
    except Exception as e:
        print(f"[-] Initialization Error: {str(e)}")
        tcpSocket = None    # 소켓 초기화



# 서버로부터 메시지 수신
def readMessage():
    global tcpSocket
    if tcpSocket is None:
        print("[-] Error: TCP socket is not initialized")
        return None, None
    try :
        data = tcpSocket.recv(1024)
        if data :
            return data.decode(), None
    except Exception as e:
        print(f"[-] Receive Error: {str(e)}")
    return None, None

# 서버로부터 청크 데이터 수신 (스크립트 파일)
def receiveChunks() -> bytes:
    global tcpSocket

    buffer = b""                                                # 바이트 단위 누적할 버퍼
    try:
        while True:
            chunk = tcpSocket.recv(1024)
            if not chunk:                                       # 더이상 읽을 데이터가 없으면 종료
                break
            buffer += chunk
        return buffer.decode()                   # 모든 청크를 누적한 데이터를 디코딩하여 반환
    except UnicodeDecodeError as e:
        print(f"[-] Decoding error: {e}")
        return None
    except Exception as e:
        print(f"[-] Error while receiving chunk: {str(e)}")
        return None

# 서버로 메시지 전송
def sendMessage(msg: str) -> None:
    global tcpSocket

    try :
        # 메시지 전송
        tcpSocket.sendall(msg.encode())
        print(f"[*] Message sent: {msg}")
    except Exception as e:
        print(f"[-] send Error: {str(e)}")

# 소켓 종료
def closeSocket() -> None:
    global tcpSocket

    if tcpSocket:
        tcpSocket.close()
        print("[*] Disconnected from TCP Server")
