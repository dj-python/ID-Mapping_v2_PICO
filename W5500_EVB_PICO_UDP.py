import _thread
from machine import Pin, SPI
import time
import network
try:
    import usocket as socket
except ImportError:
    import socket

udpSocket = None
is_initialized = False
_socket_lock = _thread.allocate_lock()
_remote_addr = None  # (server_ip, server_port)


def init(ipAddress: str, portNumber: int, gateway: str, server_ip: str, server_port: int) -> None:
    """
    UDP 초기화:
    - WIZNET5K 활성화
    - UDP 소켓 생성, 논블로킹
    - 서버 주소(_remote_addr) 설정
    """
    global udpSocket, is_initialized, _remote_addr

    try:
        if udpSocket:
            try:
                udpSocket.close()
            except:
                pass
            udpSocket = None
        is_initialized = False
        _remote_addr = (server_ip, server_port)

        # SPI 및 W5500 초기화 (기존과 동일)
        spi = SPI(0, 1_000_000, polarity=0, phase=0, mosi=Pin(19), miso=Pin(16), sck=Pin(18))
        eth = network.WIZNET5K(spi, Pin(17), Pin(20))  # spi, cs, reset pin
        eth.active(True)

        # 네트워크 설정 (원본 코드 순서 유지)
        eth.ifconfig((ipAddress, '255.255.255.0', '8.8.8.8', gateway))
        print("[*] Network Config:", eth.ifconfig())
        print(f"[*] UDP ready to send to... {server_ip}:{server_port}")

        # UDP 소켓 생성 및 논블로킹
        udpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udpSocket.setblocking(False)
        udpSocket.bind((ipAddress, portNumber))
        print(f"[*] UDP binded({ipAddress}, {portNumber})")

        # 선택: UDP connect (환경에 따라 실패 가능, 실패해도 sendto/recvfrom로 동작)
        try:
            udpSocket.connect(_remote_addr)
            print('Connected to server')
        except Exception as e:
            print(f"[Warn] UDP connect not applied: {e}")

        is_initialized = True
        print(f"[*] UDP socket initialized for server: {server_ip}:{server_port}")

    except Exception as e:
        print(f"[-] UDP Initialization Error: {str(e)}")
        is_initialized = False
        try:
            if udpSocket:
                udpSocket.close()
        except:
            pass
        udpSocket = None




def read_from_socket():
    """
    논블로킹 수신:
    - 수신 데이터 없으면 None
    - 수신 시 bytes 반환 (디코딩하지 않음)
    """
    global udpSocket, is_initialized, _remote_addr
    if udpSocket is None:
        is_initialized = False
        return None
    try:
        # connect가 되어 있으면 recv 사용 가능
        try:
            data = udpSocket.recv(2048)
            addr_ok = True
        except Exception:
            data, addr = udpSocket.recvfrom(2048)
            addr_ok = (_remote_addr is None) or (addr == _remote_addr)

        if not data:
            return None

        if not addr_ok:
            return None

        # **디코딩하지 않고 bytes 그대로 반환**
        return data

    except OSError as e:
        if hasattr(e, 'errno') and e.errno == 11:
            return None
        print(f"[Error] UDP recv failed: {e}")
        is_initialized = False
        try:
            udpSocket.close()
        except Exception:
            pass
        udpSocket = None
        return None
    except Exception as e:
        print(f"[Error] UDP recv failed: {e}")
        is_initialized = False
        try:
            udpSocket.close()
        except Exception:
            pass
        udpSocket = None
        return None



# def read_from_socket():
#     """
#     논블로킹 수신:
#     - 수신 데이터 없으면 None
#     - 수신 시 UTF-8 디코딩 문자열 반환
#     - 서버가 아닌 발신자는 무시
#     """
#     global udpSocket, is_initialized, _remote_addr
#     if udpSocket is None:
#         is_initialized = False
#         return None
#     try:
#         # connect가 되어 있으면 recv 사용 가능
#         try:
#             data = udpSocket.recv(2048)
#             addr_ok = True
#         except Exception:
#             data, addr = udpSocket.recvfrom(2048)
#             addr_ok = (_remote_addr is None) or (addr == _remote_addr)
#
#         if not data:
#             # UDP는 연결 종료 개념이 없음. 빈 데이터는 무시.
#             return None
#
#         if not addr_ok:
#             # 지정 서버가 아니면 무시
#             return None
#
#         try:
#             decoded_data = data.decode('utf-8')
#         except Exception as e:
#             print(f"[Error] UDP data decode failed: {e}. Raw data: {data}")
#             decoded_data = ""
#         return decoded_data
#
#     except OSError as e:
#         # 데이터 없음(논블로킹)
#         if hasattr(e, 'errno') and e.errno == 11:
#             return None
#         print(f"[Error] UDP recv failed: {e}")
#         is_initialized = False
#         try:
#             udpSocket.close()
#         except Exception:
#             pass
#         udpSocket = None
#         return None
#     except Exception as e:
#         print(f"[Error] UDP recv failed: {e}")
#         is_initialized = False
#         try:
#             udpSocket.close()
#         except Exception:
#             pass
#         udpSocket = None
#         return None


def sendMessage(msg: str) -> None:
    """
    서버로 메시지 전송 (UDP, 비신뢰성).
    """
    global udpSocket, is_initialized, _remote_addr
    try:
        if not is_initialized or udpSocket is None or _remote_addr is None:
            print("[클라이언트][UDP] sendMessage: Not initialized, message not sent.")
            return

        payload = msg.encode('utf-8')
        try:
            udpSocket.send(payload)  # connect() 성공 시
        except Exception:
            udpSocket.sendto(payload, _remote_addr)

        print(f"[*][UDP] Message sent: {msg}")
    except Exception as e:
        print(f"[-][UDP] send Error: {str(e)}")
        is_initialized = False
        if udpSocket:
            try:
                udpSocket.close()
            except:
                pass
            udpSocket = None


def close_connection():
    global udpSocket, is_initialized
    if udpSocket:
        try:
            udpSocket.close()
        except:
            pass
        udpSocket = None
    is_initialized = False
    print("[*] UDP 소켓 종료")
