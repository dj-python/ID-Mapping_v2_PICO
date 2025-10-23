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
            # s.bind(("0.0.0.0", 0))

            # 논블로킹
            s.setblocking(False)
            s.bind((ipAddress, portNumber))

            tcpSocket = s
            _server_addr = (server_ip, server_port)
            is_initialized = True

            print(f"[*] Ready for UDP peer: {server_ip} : {server_port}")



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




def read_from_socket():
    """
    논블로킹 수신.
    - 같은 서버 IP에서 오는 패킷은 소스 포트가 달라도 수용합니다.
    - 'Script send'를 수신하면 해당 (IP, 포트)로 피어 주소를 갱신합니다.
    - 디코딩 오류 시 데이터 유실을 막기 위해 errors='replace'를 위치 인자로 사용.
    - 단일 패킷으로 온 대용량 스크립트를 수신할 수 있도록 RECV_BUFSIZE(65507) 사용.
    """
    global tcpSocket, is_initialized, _server_addr
    if tcpSocket is None:
        is_initialized = False
        return None
    try:
        data, addr = tcpSocket.recvfrom(RECV_BUFSIZE)
        if not data:
            return None

        # peer 학습/검증: IP 기준으로만 제한 (포트 변화 허용)
        if _server_addr is None:
            _server_addr = addr  # 최초 수신자로 설정
        else:
            # IP가 다른 경우에만 무시
            if addr[0] != _server_addr[0]:
                # print(f"[*] Ignored packet from unexpected peer {addr}")
                return None

        # 안전 디코딩: MicroPython은 키워드 인자 미지원일 수 있으므로 위치 인자 사용
        decoded_data = data.decode('utf-8', 'replace')

        # 'Script send' 수신 시 포트까지 업데이트(서버가 이후 같은 소켓을 사용할 때 추적)
        if "Script send" in decoded_data and addr[0] == _server_addr[0]:
            _server_addr = addr

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



# def read_from_socket():
#     """
#     논블로킹 수신.
#     - 같은 서버 IP에서 오는 패킷은 소스 포트가 달라도 수용합니다.
#     - 'Script send'를 수신하면 해당 (IP, 포트)로 피어 주소를 갱신합니다.
#     - 디코딩 오류 시 데이터 유실을 막기 위해 errors='replace'를 위치 인자로 사용.
#     """
#     global tcpSocket, is_initialized, _server_addr
#     if tcpSocket is None:
#         is_initialized = False
#         return None
#     try:
#         data, addr = tcpSocket.recvfrom(2048)
#         if not data:
#             return None
#
#         # peer 학습/검증: IP 기준으로만 제한 (포트 변화 허용)
#         if _server_addr is None:
#             _server_addr = addr  # 최초 수신자로 설정
#         else:
#             # IP가 다른 경우에만 무시
#             if addr[0] != _server_addr[0]:
#                 # 디버깅 필요 시 활성화
#                 # print(f"[*] Ignored packet from unexpected peer {addr}")
#                 return None
#
#         # 안전 디코딩: MicroPython은 키워드 인자 미지원일 수 있으므로 위치 인자 사용
#         decoded_data = data.decode('utf-8', 'replace')
#
#         # 'Script send' 수신 시 포트까지 업데이트(서버가 이후 같은 소켓을 사용할 때 추적)
#         if "Script send" in decoded_data and addr[0] == _server_addr[0]:
#             _server_addr = addr
#
#         return decoded_data
#     except OSError as e:
#         # 데이터 없음(논블로킹)일 때 연결 유지
#         if hasattr(e, 'errno') and e.errno == 11:
#             return None
#         print(f"[Error] socket recv failed: {e}")
#         is_initialized = False
#         try:
#             tcpSocket.close()
#         except Exception:
#             pass
#         tcpSocket = None
#         return None
#     except Exception as e:
#         print(f"[Error] socket recv failed: {e}")
#         is_initialized = False
#         try:
#             tcpSocket.close()
#         except Exception:
#             pass
#         tcpSocket = None
#         return None





#
# def read_from_socket():
#     global tcpSocket, is_initialized, _server_addr
#     if tcpSocket is None:
#         is_initialized = False
#         return None
#     try:
#         # UDP는 송신자 주소도 함께 수신
#         data, addr = tcpSocket.recvfrom(1024)
#         if not data:
#             # UDP에서 0바이트는 연결 종료 신호가 아님 -> 무시
#             return None
#
#         # 예상 외 피어의 패킷은 무시 (필요 시 주석 처리 가능)
#         if _server_addr and addr != _server_addr:
#             # print(f"[*] Ignored packet from unexpected peer {addr}")
#             return None
#
#         try:
#             decoded_data = data.decode('utf-8')
#         except Exception as e:
#             print(f"[Error] Data decode failed: {e}. Raw data: {data}")
#             decoded_data = ""
#         return decoded_data
#     except OSError as e:
#         # 데이터 없음(논블로킹)일 때 연결 유지
#         if hasattr(e, 'errno') and e.errno == 11:
#             return None
#         print(f"[Error] socket recv failed: {e}")
#         is_initialized = False
#         try:
#             tcpSocket.close()
#         except Exception:
#             pass
#         tcpSocket = None
#         return None
#     except Exception as e:
#         print(f"[Error] socket recv failed: {e}")
#         is_initialized = False
#         try:
#             tcpSocket.close()
#         except Exception:
#             pass
#         tcpSocket = None
#         return None


# 서버로 메시지 전송
def sendMessage(msg: str) -> None:
    global tcpSocket, is_initialized, _server_addr
    try:
        if not is_initialized or tcpSocket is None or _server_addr is None:
            print("[클라이언트] sendMessage: Not initialized, message not sent.")
            return
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

