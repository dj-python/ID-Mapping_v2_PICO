from machine import Pin, SPI
import time
import network
import socket
# import traceback

tcpSocket = None
is_initialized = False                  # 초기화 상태를 추적

# W5x00 chip init
def init(ipAddress: str, portNumber, gateway : str, server_ip : str, server_port: int) -> None:
    global tcpSocket, is_initialized

    try:
        # SPI 및 W5500 초기화
        spi = SPI(0, 1_000_000, polarity=0, phase=0, mosi=Pin(19), miso=Pin(16), sck=Pin(18))
        eth = network.WIZNET5K(spi, Pin(17), Pin(20))  # spi,cs,reset pin
        eth.active(True)

        # 네트워크 설정
        eth.ifconfig((ipAddress, '255.255.255.0', '8.8.8.8', gateway))
        print("[*] Network Config:", eth.ifconfig())
        print(f"[*] Attempting connection to... {server_ip}:{server_port}")

        # 서버 접속 시도 (재시도 로직 포함)
        while True:
            try:
                tcpSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                tcpSocket.settimeout(10)
                tcpSocket.bind((ipAddress, portNumber))
                tcpSocket.connect((server_ip, server_port))
                is_initialized = True
                tcpSocket.setblocking(True)                                           # Non-blocking mode
                # tcpSocket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)     # Keep alive
                print(f"[*] Connected to TCP Server: {server_ip} : {server_port}")
                break

            except socket.timeout:
                print(f"[-] Connection to TCP Server: {server_ip} : {server_port}")
                if tcpSocket:
                    tcpSocket.close()
                time.sleep(3)
            except socket.error as e:
                print(f"[-] Socket error: {e}")
                if tcpSocket:
                    tcpSocket.close()
                time.sleep(3)
            except Exception as e:
                print(f"[-] Unexpected Error: {e}")
                if tcpSocket:
                    tcpSocket.close()
                time.sleep(3)


    except Exception as e:
        # print(traceback.format_exc())
        is_initialized = False
        print(f"[-] Initialization Error: {str(e)}")
        tcpSocket = None    # 소켓 초기화



# 서버로부터 메시지 수신
def readMessage():
    global tcpSocket, is_initialized
    if not is_initialized or tcpSocket is None:
        print("[-] Error: TCP socket is not initialized")
        return None, None
    try :
        data, addr = tcpSocket.recv(1024)
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
        try:
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
        tcpSocket.sendall(msg.encode('utf-8'))
        print(f"[*] Message sent: {msg}")
    except Exception as e:
        print(f"[-] send Error: {str(e)}")

# 소켓 종료
def closeSocket() -> None:
    global tcpSocket

    if tcpSocket:
        tcpSocket.close()
        print("[*] Disconnected from TCP Server")
