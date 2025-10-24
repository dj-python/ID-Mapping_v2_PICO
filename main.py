from machine import Pin, SPI
import time
import W5500_EVB_PICO_UDP as W5500
from collections import OrderedDict

# 서버 메시지 수신 버퍼
tcp_receive_buffer = ""  # 네트워크 수신 버퍼
script_buffer = ""  # 스크립트 전체 누적 버퍼
is_script_sending = False  # 스크립트 수신 상태 플래그

FIRMWARE_VERSION = 0.3

SPI_SPEED = 12_000_000
SPI_BUF_SIZE = 32
DELAY_SPI_TX_RX = 0.000_01
SPI_TX_RETRY = 0

DEBUG_MODE = False

class Error:
    ERR_CURRENT     = 'ERR_CURRENT'
    ERR_SPI         = 'ERR_COM'
    ERR_SENSOR_ID   = 'ERR_SENSOR_ID'
    ERR_VARIFY      = 'ERR_VARIFY'



# ===== 추가: 베이스64 디코더 및 라인 파서 유틸 =====
try:
    import ubinascii as _ubinascii  # MicroPython 우선
except Exception:
    _ubinascii = None

# 서버가 보내는 "SCRIPT_CHUNK <len> <b64>"의 <b64>를 디코딩
def _b64decode(s: str) -> bytes:
    try:
        if _ubinascii is not None:
            # ubinascii.a2b_base64는 bytes 입력 필요
            return _ubinascii.a2b_base64(s.encode('ascii'))
        else:
            import base64
            return base64.b64decode(s)
    except Exception as e:
        print("[Error] base64 decode failed:", e)
        return b""

# tcp_receive_buffer에서 개행 단위로 한 줄을 꺼냄.
# 개행이 아직 안 온 경우 None 반환.
tcp_receive_buffer = ""   # 문자열 버퍼(텍스트)
def _pop_line_from_buffer():
    global tcp_receive_buffer
    nl = tcp_receive_buffer.find('\n')
    if nl == -1:
        return None
    line = tcp_receive_buffer[:nl].rstrip('\r')
    tcp_receive_buffer = tcp_receive_buffer[nl+1:]
    return line
# ===== 유틸 끝 =====


class Main:
    def __init__(self, server_ip, server_port):
        self.sysLed_pico = Pin(25, Pin.OUT)

        # region SPI
        self.spi = SPI(1, baudrate=SPI_SPEED, polarity=0, phase=0, bits=8, sck=Pin(10), mosi=Pin(11), miso=Pin(12))
        self.spi_cs_M1 = Pin(0, mode=Pin.OUT, value=1)
        self.spi_cs_M2 = Pin(1, mode=Pin.OUT, value=1)
        self.spi_cs_M3 = Pin(2, mode=Pin.OUT, value=1)
        self.spi_cs_M4 = Pin(3, mode=Pin.OUT, value=1)
        self.spi_cs_M5 = Pin(4, mode=Pin.OUT, value=1)
        self.spi_cs_M6 = Pin(5, mode=Pin.OUT, value=1)
        self.spi_cs_M7 = Pin(6, mode=Pin.OUT, value=1)
        self.spi_cs_M8 = Pin(7, mode=Pin.OUT, value=1)

        self.writeCard_sel1 = Pin(8, Pin.IN)
        self.writeCard_sel2 = Pin(9, Pin.IN)
        self.writeCard_sel3 = Pin(14, Pin.IN)
        self.writeCard_sel4 = Pin(15, Pin.IN)
        # endregion

        # region UDP/IP
        self.is_script_sending = False  # 스크립트 저장 상태
        self.script_file_name = "script.txt"
        # self.ipAddress = '192.168.1.104'
        self.gateway = '192.168.1.1'
        self.server_ip = server_ip
        self.server_port = server_port

        self.barcode_sendStates = {}
        self.barcode_info = {}
        self.isSumDelay_sensorId = None
        self.delay_sensorId = int()
        self.isRead_sensorId = False
        self.sensorId = {}

        self.gpioIn_ipSel1 = Pin(8, Pin.IN)
        self.gpioIn_ipSel2 = Pin(9, Pin.IN)
        self.gpioIn_ipSel3 = Pin(14, Pin.IN)
        self.gpioIn_ipSel4 = Pin(15, Pin.IN)

        self.ipAddress = ''
        self.portNumber = ''
        if self.gpioIn_ipSel1.value() == 1 and self.gpioIn_ipSel2.value() == 1 and self.gpioIn_ipSel3.value() == 1:
            self.ipAddress = '192.168.1.101'
            self.portNumber = 8001
        elif self.gpioIn_ipSel1.value() == 1 and self.gpioIn_ipSel2.value() == 1 and self.gpioIn_ipSel3.value() == 0:
            self.ipAddress = '192.168.1.102'
            self.portNumber = 8002
        elif self.gpioIn_ipSel1.value() == 1 and self.gpioIn_ipSel2.value() == 0 and self.gpioIn_ipSel3.value() == 1:
            self.ipAddress = '192.168.1.103'
            self.portNumber = 8003
        elif self.gpioIn_ipSel1.value() == 0 and self.gpioIn_ipSel2.value() == 1 and self.gpioIn_ipSel3.value() == 1:
            self.ipAddress = '192.168.1.104'
            self.portNumber = 8004
        # endregion

        self.try_init_tcp()


        # self.sendScript(5)
        # barcode = 'C9051A569000H5'
        # self.sendBarcode(5, barcode)

    # region time function
    def func_1ms(self):
        pass

    def func_10ms(self):
        global tcp_receive_buffer, is_script_sending

        if W5500.is_initialized:
            drained = 0
            added = 0
            while True:
                chunk = W5500.read_from_socket()
                if chunk:
                    if not is_script_sending:
                        print(f"[RX] {chunk.rstrip()}")
                elif not chunk:
                    break
                tcp_receive_buffer += chunk
                added += len(chunk)
                drained += 1
                if drained > 64:
                    break
            if added:
                try:
                    print("[DBG] appended {} bytes to buffer (total now ~unknown due to Python string)".format(added))
                except Exception:
                    pass
            self.handle_ping()
            self.handle_script_receive()
            self.handle_barcode_receive()

    def func_20ms(self):
        pass

    def func_50ms(self):
        pass



    def func_100ms(self):
        if self.isRead_sensorId:
            self.sensorId = dict()

            for key, value in self.barcode_sendStates.items():
                if value == 'failed':
                    self.sensorId[key] = Error.ERR_SPI
                else:
                    ret = self.readSensorId(int(key[-1]))

                    if ret == 'failed':
                        self.sensorId[key] = Error.ERR_SENSOR_ID
                    elif ret == '0':
                        self.sensorId[key] = Error.ERR_SENSOR_ID
                    else:
                        self.sensorId[key] = ret

            W5500.sendMessage('sensor_ID: {}\n'.format(self.sensorId))
            W5500.sendMessage('barcode_info: {}\n'.format(self.barcode_info))
            self.isRead_sensorId = False

    def func_500ms(self):
        self.sysLed_pico(not self.sysLed_pico.value())
    # endregion

    # region About UDP/IP
    def try_init_tcp(self):
        # 함수명은 기존 유지 (호출부 변경 최소화). 내부는 UDP 모듈 사용.
        try:
            W5500.init(ipAddress=self.ipAddress,
                       portNumber=self.portNumber,
                       gateway=self.gateway,
                       server_ip=self.server_ip,
                       server_port=self.server_port)
        except Exception as e:
            print(f"[-] Initialization Error: {str(e)}")



    def handle_ping(self):
        """
        서버로부터 'ping' (개행 단위) 메시지를 받으면 'pong'으로 회신.
        - 다른 프로토콜 라인은 그대로 버퍼에 되돌려 후속 핸들러가 처리하도록 함.
        - 대소문자 무시, 공백 제거 후 비교.
        """
        global tcp_receive_buffer
        if not tcp_receive_buffer:
            return

        orig_buf = tcp_receive_buffer
        keep_lines = []
        responded = False

        while True:
            line = _pop_line_from_buffer()
            if line is None:
                break
            if line.strip().lower() == 'ping':
                try:
                    W5500.sendMessage('pong\n')
                    print('pong')
                except Exception as e:
                    print("[Error] failed to send pong:", e)
                responded = True
            else:
                keep_lines.append(line)

        # 남은 조각(개행 없는 마지막 부분)
        remainder = tcp_receive_buffer

        # ping을 하나라도 처리했다면, 남은 라인들을 원래 순서로 복원
        if responded:
            rebuilt = ''
            if keep_lines:
                rebuilt = '\n'.join(keep_lines)
                if remainder or orig_buf.endswith('\n'):
                    rebuilt += '\n'
            tcp_receive_buffer = rebuilt + remainder

    @staticmethod
    def save_to_script_file_bytes(data: bytes):
        try:
            with open("script.txt", "wb") as f:
                f.write(data)
            print("[Debug] script.txt 저장 완료 ({} bytes)".format(len(data)))
        except Exception as e:
            print(f"[Error] script.txt 저장 오류: {e}")


    def handle_script_receive(self):
        global tcp_receive_buffer, is_script_sending, script_bytes

        progressed = False
        while True:
            # 1) 스크립트 수신 전: 'Script send' 라인이 나올 때까지 잡음 라인 소비
            if not is_script_sending:
                line = _pop_line_from_buffer()
                if line is None:
                    break
                progressed = True

                # 'Script send' 포함 라인 만나면 수신 모드로 전환
                if "Script send" in line:
                    is_script_sending = True
                    script_bytes = bytearray()
                    print("[DEBUG] Script receive start")
                    # 서버가 ACK을 요구한다면 아래 한 줄을 서버 요구 문자열로 변경 후 주석 해제
                    # W5500.sendMessage("Script ready\n")
                    continue

                # 여기로 오면 UDPTest 같은 잡음 라인
                # 이전 코드처럼 버퍼에 되돌려놓지 말고 '소비'하고 계속 진행
                continue

            # 2) 스크립트 수신 중: 다음 라인을 처리
            line = _pop_line_from_buffer()
            if line is None:
                break
            progressed = True

            s = line.strip()
            if not s:
                continue

            # 종료 토큰
            if s == "EOF":
                print("[Debug] Script 수신 완료 - 파일 저장")
                self.save_to_script_file_bytes(bytes(script_bytes))
                is_script_sending = False
                script_bytes = bytearray()

                # 이후 MCU로 스크립트 전송
                start_time = time.ticks_ms()
                for i in range(8):
                    ret = self.sendScript(i + 1)
                    msg = f"Script save {ret}: MCU{i + 1}\n"
                    W5500.sendMessage(msg)
                end_time = time.ticks_ms()
                print(f'Elapsed time: {time.ticks_diff(end_time, start_time) / 1000}ms')
                break

            # 청크 라인: SCRIPT_CHUNK <len> <b64>
            if s.startswith("SCRIPT_CHUNK "):
                parts = s.split(" ", 2)
                if len(parts) < 3:
                    print("[Warn] malformed SCRIPT_CHUNK line:", s[:80])
                    continue
                _, raw_len_str, b64_payload = parts
                try:
                    expected_len = int(raw_len_str)
                except:
                    print("[Warn] invalid length in SCRIPT_CHUNK:", raw_len_str)
                    expected_len = -1

                decoded = _b64decode(b64_payload)
                if expected_len >= 0 and len(decoded) != expected_len:
                    print(f"[Warn] length mismatch: expected {expected_len}, got {len(decoded)}")

                script_bytes.extend(decoded)
                continue

            # 스크립트 수신 중 예기치 않은 라인: 되돌리지 말고 무시
            # (되돌리면 다시 이 지점에서 막힐 수 있음)
            continue

        if not progressed:
            return



    def handle_barcode_receive(self):
        """
        서버로부터 'barcode_info: { ... }' 형태의 딕셔너리 문자열을 수신해
        그대로 self.barcode_info에 저장한다. 'barcode_info:' 프리픽스는 무시한다.
        부분 수신을 고려해 중괄호 매칭으로 완전한 딕셔너리 본문이 모일 때까지 대기.
        """
        global tcp_receive_buffer

        if not tcp_receive_buffer:
            return

        prefix = 'barcode_info:'
        buf = tcp_receive_buffer

        # 프리픽스가 없으면 처리하지 않음
        if prefix not in buf:
            return

        # 프리픽스 이후의 본문에서 딕셔너리 추출
        prefix_idx = buf.find(prefix)
        after = buf[prefix_idx + len(prefix):]

        # 딕셔너리 시작 '{' 탐색
        lbrace_idx = after.find('{')
        if lbrace_idx == -1:
            # 아직 본문 시작이 오지 않음
            return

        # 중괄호 레벨 카운팅으로 끝 위치 탐색
        depth = 0
        end_rel_idx = -1
        for i, ch in enumerate(after[lbrace_idx:], start=lbrace_idx):
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    end_rel_idx = i
                    break

        if end_rel_idx == -1:
            # 아직 전체 딕셔너리가 수신되지 않음
            return

        dict_str = after[lbrace_idx:end_rel_idx + 1]

        # 파싱 시도: JSON 우선, 실패 시 literal_eval 폴백
        parsed = None
        try:
            try:
                import ujson as json
            except:
                import json  # type: ignore
            json_str = dict_str.replace("'", '"')
            parsed = json.loads(json_str)
        except Exception as e:
            try:
                import ast  # type: ignore
                parsed = ast.literal_eval(dict_str)
            except Exception as e2:
                print("[Error] barcode_info 파싱 실패:", e, e2)
                return

        if not isinstance(parsed, dict):
            print("[Error] barcode_info 형식 오류: dict 아님 ->", type(parsed))
            return

        self.barcode_info = parsed
        print("[Debug] barcode_info dict 저장 완료:", self.barcode_info)

        self.barcode_sendStates = dict()
        for key, value in self.barcode_info.items():
            ret = self.sendBarcode(int(key[-1]), value)
            self.barcode_sendStates[key] = ret

        time.sleep((self.delay_sensorId + 100) / 1000)
        self.isRead_sensorId = True

        # 소비한 데이터 제거 (+ 선택적으로 종료 토큰 제거)
        consumed_end = prefix_idx + len(prefix) + end_rel_idx + 1
        remainder = buf[consumed_end:]
        finish_token = 'barcode sending finished'
        if finish_token in remainder:
            remainder = remainder.replace(finish_token, '')
        tcp_receive_buffer = remainder
        # self.is_barcode_receiving = False
    # endregion

    # region About MCU
    def sendScript(self, target) -> str:
        with open('script.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines:
                msg = line.strip().replace(' ', '').upper()

                if line[0] != ';' and line[0:2] != '\r\n' and line[0] != '\n':
                    sendBytes = b'\x01\x00' + int.to_bytes(len(msg), 2, 'big')
                    sub_msg = self.convert_hex_as_int(msg)
                    sendBytes += bytearray(sub_msg, 'utf-8')

                    while len(sendBytes) < (SPI_BUF_SIZE - 2):
                        sendBytes += b'\xFF'

                    checksum = self.getChecksum(sendBytes)
                    sendBytes += int.to_bytes(checksum, 2, 'big')

                    fail_cnt = 0
                    while True:
                        self.sendDataBySpi(sendBytes, target)
                        time.sleep(DELAY_SPI_TX_RX)
                        if b'#SCRIPT_START' in sendBytes:
                            self.delay_sensorId = 0
                            time.sleep(0.05)

                        if b'#POWER_SETTING' in sendBytes or b'#READ_SENSOR_ID' in sendBytes:
                            if b'#POWER_SETTING' in sendBytes:
                                self.isSumDelay_sensorId = 'POWER_SETTING'
                            else:
                                self.isSumDelay_sensorId = 'READ_SENSOR_ID'
                        elif (b'#MODEL_INFO' in sendBytes or b'#SLAVE_ADDRESS' in sendBytes or
                              b'#MEMORY_PROTECTION_DISABLE' in sendBytes or b'#WRITE_BARCODE' in sendBytes or
                              b'#MEMORY_PROTECTION_ENABLE' in sendBytes or b':END' in sendBytes):
                            self.isSumDelay_sensorId = None

                        if self.isSumDelay_sensorId == 'POWER_SETTING':
                            if b'#POWER_SETTING' not in sendBytes:
                                self.delay_sensorId += int(msg.split(',')[2])
                        elif self.isSumDelay_sensorId == 'READ_SENSOR_ID':
                            if b'#READ_SENSOR_ID' not in sendBytes:
                                self.delay_sensorId += int(msg.split(',')[6])

                        rxVal = self.receiveDataBySpi(SPI_BUF_SIZE, target)
                        if checksum == int.from_bytes(rxVal[SPI_BUF_SIZE - 2:], 'big'):
                            break
                        else:
                            fail_cnt += 1
                            if fail_cnt > SPI_TX_RETRY:
                                print(f'Error: Failed update script')
                                return 'failed'
                            else:
                                print(f'Warning: Failed checksum, TX Retry{fail_cnt}')
        return 'finished'

    def sendBarcode(self, target, barcode) -> str:
        sendBytes = b'\x02\x00' + int.to_bytes(len(barcode), 2, 'big')
        sendBytes += bytearray(barcode, 'utf-8')

        while len(sendBytes) < (SPI_BUF_SIZE - 2):
            sendBytes += b'\xFF'

        checksum = self.getChecksum(sendBytes)
        sendBytes += int.to_bytes(checksum, 2, 'big')

        fail_cnt = 0
        while True:
            self.sendDataBySpi(sendBytes, target)
            time.sleep(DELAY_SPI_TX_RX)

            rxVal = self.receiveDataBySpi(SPI_BUF_SIZE, target)
            if checksum == int.from_bytes(rxVal[SPI_BUF_SIZE - 2:], 'big'):
                break
            else:
                fail_cnt += 1
                if fail_cnt > SPI_TX_RETRY:
                    print(f'MCU_{target} >> Error: Failed send barcode')
                    return 'failed'
                else:
                    print(f'MCU_{target} >> Warning: Failed checksum, TX Retry{fail_cnt}')
        return 'finished'

    def readSensorId(self, target) -> any:
        sendBytes = b'\x03\x00\x00\x00'

        while len(sendBytes) < (SPI_BUF_SIZE - 2):
            sendBytes += b'\xFF'

        checksum = self.getChecksum(sendBytes)
        sendBytes += int.to_bytes(checksum, 2, 'big')

        fail_cnt = 0
        while True:
            self.sendDataBySpi(sendBytes, target)
            time.sleep(DELAY_SPI_TX_RX)

            rxVal = self.receiveDataBySpi(SPI_BUF_SIZE, target)

            if (self.getChecksum(rxVal[:-2]) == int.from_bytes(rxVal[SPI_BUF_SIZE - 2:], 'big') and
                    rxVal[1] == 0x00):
                sensorId_len = int.from_bytes(rxVal[2:4])
                sensorId = rxVal[4:4+sensorId_len]
                # print(f'Read sensor ID: {sensorId}')
                break
            else:
                fail_cnt += 1
                if fail_cnt > SPI_TX_RETRY:
                    print(f'MCU_{target} >> Error: Failed read sensor ID')
                    return 'failed'
                else:
                    print(f'MCU_{target} >> Warning: Failed checksum, TX Retry{fail_cnt}')

        if int.from_bytes(sensorId, 'big') == 0:
            return '0'
        else:
            return sensorId.hex().upper()

    def spi_chip_select(self, target, high_low):
        if target == 1:
            self.spi_cs_M1.value(high_low)
        elif target == 2:
            self.spi_cs_M2.value(high_low)
        elif target == 3:
            self.spi_cs_M3.value(high_low)
        elif target == 4:
            self.spi_cs_M4.value(high_low)
        elif target == 5:
            self.spi_cs_M5.value(high_low)
        elif target == 6:
            self.spi_cs_M6.value(high_low)
        elif target == 7:
            self.spi_cs_M7.value(high_low)
        elif target == 8:
            self.spi_cs_M8.value(high_low)

    def sendDataBySpi(self, data, target):
        if DEBUG_MODE:
            print(f'TX_{target} >> {len(data)}, {data}')

        self.spi_chip_select(target, 0)
        self.spi.write(data)
        self.spi_chip_select(target, 1)

    def receiveDataBySpi(self, length, target) -> bytes:
        self.spi_chip_select(target, 0)
        data = self.spi.read(length)
        self.spi_chip_select(target, 1)

        if DEBUG_MODE:
            print(f'RX_{target} >> {len(data)}, {data}')
        return data

    @staticmethod
    def getChecksum(data):
        checksum = 0
        for byte in data:
            checksum += byte

        return checksum & 0xFFFF
    # endregion

    @staticmethod
    def convert_hex_as_int(s):
        result = ''
        i = 0
        while i < len(s):
            if s[i:i + 2].upper() == '0X':
                j = i + 2
                hex_str = ''
                while j < len(s) and s[j].upper() in '0123456789ABCDEF':
                    hex_str += s[j]
                    j += 1
                dec = str(int(hex_str, 16))
                result += dec
                i = j
            else:
                result += s[i]
                i += 1
        return result


if __name__ == "__main__":
    cnt_ms = 0

    server_ip = '192.168.1.2'
    server_port = 8000
    main = Main(server_ip, server_port)

    # 상태머신 구조
    # 상태 : "DISCONNECTED", "CONNECTED"
    conn_state = "CONNECTED" if W5500.is_initialized else "DISCONNECTED"
    reconnect_timer = 0

    while True:
        cnt_ms += 1

        try:
            main.func_1ms()

            if not cnt_ms % 10:
                main.func_10ms()

            if not cnt_ms % 20:
                main.func_20ms()

            if not cnt_ms % 50:
                main.func_50ms()

            if not cnt_ms % 100:
                main.func_100ms()

            if not cnt_ms % 500:
                main.func_500ms()

            time.sleep_ms(1)
        except KeyboardInterrupt:
            print("KeyboardInterrupt: cleaning up UDP...")
            W5500.close_connection()
            break
        except Exception as e:
            print("Exception in main loop", e)
            import sys

            sys.print_exception(e)
