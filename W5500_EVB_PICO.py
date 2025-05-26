import _thread
from machine import Pin, SPI
import time
import network
import socket

tcpSocket = None
is_initialized = False                  # 초기화 상태를 추적
_ping_thread_running = False            # ping 송신 스레드 상태 플래그

# W5x00 chip init
def init(ipAddress: str, portNumber: int, gateway : str, server_ip : str, server_port: int) -> None:
    global tcpSocket, is_initialized, _ping_thread_running

    try:
        # 기존 소켓이 열려 있으면 닫고 초기화
        if tcpSocket:
            try: tcpSocket.close()
            except: pass
            tcpSocket = None

        # SPI 및 W5500 초기화
        spi = SPI(0, 1_000_000, polarity=0, phase=0, mosi=Pin(19), miso=Pin(16), sck=Pin(18))
        eth = network.WIZNET5K(spi, Pin(17), Pin(20))  # spi,cs,reset pin
        eth.active(True)

        # 네트워크 설정
        eth.ifconfig((ipAddress, '255.255.255.0', '8.8.8.8', gateway))
        print("[*] Network Config:", eth.ifconfig())
        print(f"[*] Attempting connection to... {server_ip}:{server_port}")

        # 서버 접속 시도 (재시도 로직 포함)
        try:
            tcpSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # tcpSocket.settimeout(10)
            tcpSocket.bind((ipAddress, portNumber))
            tcpSocket.connect((server_ip, server_port))
            is_initialized = True
            tcpSocket.setblocking(True)                                           # Non-blocking mode
            # tcpSocket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)     # Keep alive
            print(f"[*] Connected to TCP Server: {server_ip} : {server_port}")

            # ping 송신 스레드 시작 (이미 실행 중이 아니면)
            if not _ping_thread_running:
                _thread.start_new_thread(_ping_sender, ())
                _ping_thread_running = True


        #except socket.timeout:
        #    print(f"[-] Connection to TCP Server: {server_ip} : {server_port}")
        #    if tcpSocket:
        #        tcpSocket.close()
        #    time.sleep(3)
        # except socket.error as e:
        #     print(f"[-] Socket error: {e}")
        #     if tcpSocket:
        #         tcpSocket.close()
        #     time.sleep(3)
        except Exception as e:
            print(f"[-] Unexpected Error: {e}")
            is_initialized = False
            if tcpSocket:
                try: tcpSocket.close()
                except: pass
                tcpSocket = None

    except Exception as e:
        # print(traceback.format_exc())
        print(f"[-] Initialization Error: {str(e)}")
        is_initialized = False
        try: tcpSocket.close()
        except: pass
        tcpSocket = None    # 소켓 초기화

def _ping_sender():
    """3초마다 ping 메시지 전송"""
    global tcpSocket, is_initialized, _ping_thread_running

    try:
        while is_initialized and tcpSocket:
            try:
                tcpSocket.sendall(b"ping\n")
                print("[*] Ping sent")
            except Exception as e:
                print(f"[Error] ping send failed: {e}")
                is_initialized = False
                # ping 실패 시 연결 문제이므로 스레드 종료
                break
            time.sleep(3)
    except Exception as e:
        print(f"[Error] ping sender thread error: {e}")
        is_initialized = False
    finally:
        _ping_thread_running = False            # 스레드 종료 시 플래그 리셋

def read_from_socket():
    global tcpSocket, is_initialized
    if tcpSocket is None:
        return b""
    try:
        return tcpSocket.recv(1024)
    except Exception as e:
        print(f"[Error] socket recv failed: {e}")
        is_initialized = False
        return b""

# 서버로부터 메시지 수신
def readMessage():
    global tcpSocket, is_initialized
    buffer = b""
    if not is_initialized or tcpSocket is None:
        print("[-] Error: TCP socket is not initialized")
        return None

    try:
        while True:
            chunk = tcpSocket.recv(1024)
            if not chunk:
                print(f"[Debug] No data received, breaking loop.")
                break
            buffer += chunk

            # 종료 시그널 "EOF" 확인
            if b"EOF" in buffer:
                buffer = buffer.replace(b"EOF", b"")
                print("[Debug] EOF 수신 완료")
                break
            # 줄바꿈(\n) 단위 메시지 처리
            if b'\n' in buffer:
                print("[Debug] 줄바꿈 수신 완료")
                break

        message = buffer.decode('utf-8').strip()
        # print(f"[Debug] 읽은 메시지: {message}")
        return message
    except Exception as e:
        print(f"[Error] 데이터 수신 중 오류 발생: {e}")
        is_initialized = False
        return None

# 서버로부터 청크 데이터 수신 (스크립트 파일)
def receiveChunks() -> bytes:
    global tcpSocket, is_initialized

    buffer = b""                                                # 바이트 단위 누적할 버퍼
    try:
        while True:
            chunk = tcpSocket.recv(1024)
            if not chunk:                                       # 더이상 읽을 데이터가 없으면 종료
                break
            buffer += chunk

            # 청크 데이터를 출력
            print(chunk.decode('utf-8', errors='replace'))      # 디코딩 및 출력

            # 종료 시그널 확인
            if b'EOF' in buffer:
                buffer = buffer.replace(b'EOF', b'')     # 종료 시그널 제거
                break

        try:
            return buffer.decode('utf-8')                   # 모든 청크를 누적한 데이터를 디코딩하여 반환
        except UnicodeDecodeError as e:
            print(f"[-] Decoding error: {e}")
            return None
    except Exception as e:
        print(f"[-] Error while receiving chunk: {str(e)}")
        is_initialized = False
        return None

# 서버로 메시지 전송
def sendMessage(msg: str) -> None:
    global tcpSocket, is_initialized

    try :
        # 메시지 전송
        tcpSocket.sendall(msg.encode('utf-8'))
        print(f"[*] Message sent: {msg}")
    except Exception as e:
        print(f"[-] send Error: {str(e)}")
        is_initialized = False

# 소켓 종료
def closeSocket() -> None:
    global tcpSocket

    if tcpSocket:
        tcpSocket.close()
        tcpSocket = None
        print("[*] Disconnected from TCP Server")
