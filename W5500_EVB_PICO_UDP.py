import _thread
from machine import Pin, SPI
import time
import network
# import socket
try:
    import usocket as socket
except ImportError:
    import socket

tcpSocket = None
is_initialized = False                  # 초기화 상태를 추적
_ping_thread_running = False            # ping 송신 스레드 상태 플래그
_ping_thread = None
_socket_lock = _thread.allocate_lock()

# UDP에서는 원격 서버 주소를 명시적으로 관리
_server_addr = None  # tuple[str, int] 형태로 (server_ip, server_port) 저장


# W5x00 chip init
def init(ipAddress: str, portNumber: int, gateway: str, server_ip: str, server_port: int) -> None:
    global tcpSocket, is_initialized, _ping_thread_running, _server_addr

    try:
        # 기존 소켓이 열려 있으면 닫고 초기화
        if tcpSocket:
            try: tcpSocket.close()
            except: pass
            tcpSocket = None
        is_initialized = False
        _ping_thread_running = False
        _server_addr = None

        # SPI 및 W5500 초기화
        spi = SPI(0, 1_000_000, polarity=0, phase=0, mosi=Pin(19), miso=Pin(16), sck=Pin(18))
        eth = network.WIZNET5K(spi, Pin(17), Pin(20))  # spi,cs,reset pin
        eth.active(True)

        # 네트워크 설정 (원본 코드 순서 유지)
        eth.ifconfig((ipAddress, '255.255.255.0', '8.8.8.8', gateway))
        print("[*] Network Config:", eth.ifconfig())
        print(f"[*] Preparing UDP to... {server_ip}:{server_port}")

        try:
            # UDP 소켓 생성 및 바인드 (임의 포트)
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                # 재사용 가능 옵션은 가능 시 설정 (플랫폼에 따라 미지원일 수 있음)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            except Exception:
                pass

            # 로컬 임의 포트에 바인드 (수신 위해 바인드 권장)
            # IP는 0.0.0.0으로 바인드하여 NIC의 IP로 송수신
            s.bind(("0.0.0.0", 0))

            # 논블로킹
            s.setblocking(False)
            s.bind((ipAddress, portNumber))

            tcpSocket = s
            _server_addr = (server_ip, server_port)
            is_initialized = True

            print(f"[*] Ready for UDP peer: {server_ip} : {server_port}")

            # ping 송신 스레드 시작 (이미 실행 중이 아니면)
            if not _ping_thread_running:
                _thread.start_new_thread(_ping_sender, ())
                _ping_thread_running = True

        except Exception as e:
            print(f"[-] Unexpected Error: {e}")
            is_initialized = False
            if tcpSocket:
                try: tcpSocket.close()
                except: pass
                tcpSocket = None

    except Exception as e:
        print(f"[-] Initialization Error: {str(e)}")
        is_initialized = False
        try:
            if tcpSocket: tcpSocket.close()
        except: pass
        tcpSocket = None    # 소켓 초기화


def start_ping_sender():
    global _ping_thread, _ping_thread_running
    if _ping_thread_running:
        return
    _ping_thread_running = True
    try:
        # MicroPython은 daemon 개념이 없고, 함수가 끝나면 스레드가 종료됩니다.
        _ping_thread = _thread.start_new_thread(_ping_sender, ())
    except Exception:
        # 스레드 시작 실패 시 플래그 롤백
        _ping_thread_running = False
        raise


def _ping_sender():
    global tcpSocket, is_initialized, _ping_thread_running, _server_addr

    try:
        while _ping_thread_running and is_initialized and tcpSocket:
            try:
                with _socket_lock:
                    sock = tcpSocket
                    peer = _server_addr
                if not sock or not peer:
                    break
                # UDP는 연결이 없으므로 명시적으로 대상 지정
                sock.sendto(b"ping\n", peer)
            except Exception as e:
                print(f"[Error] ping send failed: {e}")
                is_initialized = False
                try:
                    tcpSocket.close()
                except: pass
                tcpSocket = None
                break
            time.sleep(1)
    except Exception as e:
        print(f"[Error] ping sender thread error: {e}")
        is_initialized = False
    finally:
        _ping_thread_running = False
        print("[*] ping sender thread terminated")


def read_from_socket():
    global tcpSocket, is_initialized, _server_addr
    if tcpSocket is None:
        is_initialized = False
        return None
    try:
        # UDP는 송신자 주소도 함께 수신
        data, addr = tcpSocket.recvfrom(1024)
        if not data:
            # UDP에서 0바이트는 연결 종료 신호가 아님 -> 무시
            return None

        # 예상 외 피어의 패킷은 무시 (필요 시 주석 처리 가능)
        if _server_addr and addr != _server_addr:
            # print(f"[*] Ignored packet from unexpected peer {addr}")
            return None

        try:
            decoded_data = data.decode('utf-8')
        except Exception as e:
            print(f"[Error] Data decode failed: {e}. Raw data: {data}")
            decoded_data = ""
        return decoded_data
    except OSError as e:
        # 데이터 없음(논블로킹)일 때 연결 유지
        if hasattr(e, 'errno') and e.errno == 11:
            return None
        print(f"[Error] socket recv failed: {e}")
        is_initialized = False
        try:
            tcpSocket.close()
        except Exception:
            pass
        tcpSocket = None
        return None
    except Exception as e:
        print(f"[Error] socket recv failed: {e}")
        is_initialized = False
        try:
            tcpSocket.close()
        except Exception:
            pass
        tcpSocket = None
        return None


# 서버로 메시지 전송
def sendMessage(msg: str) -> None:
    global tcpSocket, is_initialized, _server_addr
    try:
        if not is_initialized or tcpSocket is None or _server_addr is None:
            print("[클라이언트] sendMessage: Not initialized, message not sent.")
            return
        # UDP는 대상 주소 지정 필요
        tcpSocket.sendto(msg.encode('utf-8'), _server_addr)
        print(f"[*] Message sent: {msg}")
    except Exception as e:
        print(f"[-] send Error: {str(e)}")
        is_initialized = False
        if tcpSocket:
            try:
                tcpSocket.close()
            except:
                pass
            tcpSocket = None

def close_connection():
    global tcpSocket, is_initialized, _ping_thread_running, _server_addr
    if tcpSocket:
        try:
            tcpSocket.close()
        except:
            pass
        tcpSocket = None
    is_initialized = False
    _ping_thread_running = False
    _server_addr = None
    print("[*] 서버 연결 종료")


"""
        # 서버로부터 청크 데이터 수신 (스크립트 파일)
        def receiveChunks() -> bytes:
            global tcpSocket, is_initialized

            buffer = b""  # 바이트 단위 누적할 버퍼
            try:
                while True:
                    chunk = tcpSocket.recv(1024)
                    if not chunk:  # 더이상 읽을 데이터가 없으면 종료
                        break
                    buffer += chunk

                    # 청크 데이터를 출력
                    print(chunk.decode('utf-8', errors='replace'))  # 디코딩 및 출력

                    # 종료 시그널 확인
                    if b'EOF' in buffer:
                        buffer = buffer.replace(b'EOF', b'')  # 종료 시그널 제거
                        break

                try:
                    return buffer.decode('utf-8')  # 모든 청크를 누적한 데이터를 디코딩하여 반환
                except UnicodeDecodeError as e:
                    print(f"[-] Decoding error: {e}")
                    return None
            except Exception as e:
                print(f"[-] Error while receiving chunk: {str(e)}")
                is_initialized = False
                return None
"""


"""
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
"""
