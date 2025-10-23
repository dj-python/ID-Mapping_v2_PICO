from machine import Pin, SPI
import time
import W5500_EVB_PICO_UDP as W5500
from collections import OrderedDict

# 서버 메시지 수신 버퍼
tcp_receive_buffer = ""  # 네트워크 수신 버퍼
script_buffer = ""  # 스크립트 전체 누적 버퍼

FIRMWARE_VERSION = 0.2

SPI_SPEED = 12_000_000
SPI_BUF_SIZE = 32
DELAY_SPI_TX_RX = 0.000_01
SPI_TX_RETRY = 0

DEBUG_MODE = True

class Error:
    ERR_CURRENT     = 'ERR_CURRENT'
    ERR_SPI         = 'ERR_COM'
    ERR_SENSOR_ID   = 'ERR_SENSOR_ID'
    ERR_VARIFY      = 'ERR_VARIFY'


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
        self.is_script_sending = False  # 스크립트 수신 상태 플래그


        self.barcode_sendStates = {}
        self.barcode_info = {}
        self.isSumDelay_sensorId = None
        self.delay_sensorId = int()
        self.isRead_sensorId = False
        self.sensorId = {}
        self.udp_receive_buffer = b''
        self.script_buffer = b''

        self.gpioIn_ipSel1 = Pin(8, Pin.IN)
        self.gpioIn_ipSel2 = Pin(9, Pin.IN)
        self.gpioIn_ipSel3 = Pin(14, Pin.IN)
        self.gpioIn_ipSel4 = Pin(15, Pin.IN)

        self.ipAddress = ''
        self.portNumber = None
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

        self.try_init_udp()

        # self.sendScript(5)
        # barcode = 'C9051A569000H5'
        # self.sendBarcode(5, barcode)

    # region time function
    def func_1ms(self):
        pass

    def func_10ms(self):
        chunk = W5500.read_from_socket()
        if chunk:
            self.udp_receive_buffer += chunk
            print(f'[*] Received data: {chunk}')

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
    def try_init_udp(self):
        try:
            W5500.init(ipAddress=self.ipAddress,
                       portNumber=self.portNumber,
                       gateway=self.gateway,
                       server_ip=self.server_ip,
                       server_port=self.server_port)
        except Exception as e:
            print(f"[-] UDP Initialization Error: {str(e)}")
    # endregion


    @staticmethod
    def save_to_script_file(data):
        try:
            # 아래처럼 안전하게 출력!
            print("[REPL]", repr(data[:64]), "...")
            with open("script.txt", "wb") as f:
                f.write(data)
            print("[Debug] script.txt에 데이터 저장 완료")
        except Exception as e:
            print(f"[Error] script.txt 파일 저장 중 오류 발생: {e}")


    # @staticmethod
    # def save_to_script_file(data):
    #     """
    #     서버로부터 청크 데이터를 받아 script.txt 파일에 저장
    #     """
    #     print(f"[REPL] {data}")
    #     try:
    #         # 파일 저장 시 반드시 bytes로 변환
    #         with open("script.txt", "wb") as f:
    #             f.write(data.encode('utf-8'))
    #         print("[Debug] script.txt에 데이터 저장 완료")
    #     except Exception as e:
    #         print(f"[Error] script.txt 파일 저장 중 오류 발생: {e}")

    def handle_script_receive(self):
        # 반드시 bytes로 비교!
        if not self.is_script_sending and b"Script send" in self.udp_receive_buffer:
            idx = self.udp_receive_buffer.index(b"Script send")
            self.udp_receive_buffer = self.udp_receive_buffer[idx + len(b"Script send"):]
            self.is_script_sending = True
            self.script_buffer = b''
            print("[Debug] Script send 감지, 수신 시작")
            return

        if self.is_script_sending:
            if b"EOF" in self.udp_receive_buffer:
                idx = self.udp_receive_buffer.index(b"EOF")
                chunk_data = self.udp_receive_buffer[:idx]
                self.script_buffer += chunk_data
                print("[Debug] Script 수신 완료 - 파일로 저장")
                self.save_to_script_file(self.script_buffer)
                self.is_script_sending = False
                self.udp_receive_buffer = self.udp_receive_buffer[idx + len(b"EOF"):]
            else:
                self.script_buffer += self.udp_receive_buffer
                self.udp_receive_buffer = b''


    # def handle_script_receive(self):
    #     global tcp_receive_buffer, is_script_sending, mcu_script_status
    #
    #     # Script send 신호 감지 및 스크립트 수신 시작
    #     if not is_script_sending and "Script send" in tcp_receive_buffer:
    #         idx = tcp_receive_buffer.index("Script send")
    #         tcp_receive_buffer = tcp_receive_buffer[idx + len("Script send"):]
    #         is_script_sending = True
    #         return
    #
    #     # 스크립트 수신 종료(EOF) 감지 및 저장
    #     if is_script_sending and "EOF" in tcp_receive_buffer:
    #         idx = tcp_receive_buffer.index("EOF")
    #         script_buffer = tcp_receive_buffer[:idx]
    #         tcp_receive_buffer = tcp_receive_buffer[idx + len("EOF"):]
    #         print("[Debug] Script 수신 완료 - 파일로 저장")
    #         self.save_to_script_file(script_buffer)
    #         is_script_sending = False
    #
    #         start_time = time.ticks_ms()
    #         for i in range(8):
    #             ret = self.sendScript(i + 1)
    #             msg = f"Script save {ret}: MCU{i + 1}\n"
    #             W5500.sendMessage(msg)
    #         end_time = time.ticks_ms()
    #         print(f'Elapsed time: {time.ticks_diff(end_time, start_time) / 1000}ms')
    #     else:
    #         # EOF가 없으면 버퍼를 비우지 않고 계속 누적만 함
    #         return

    def handle_barcode_receive(self):
        """
        서버로부터 'barcode_info: { ... }' 형태의 딕셔너리 문자열을 수신해
        그대로 self.barcode_info에 저장한다. 'barcode_info:' 프리픽스는 무시한다.
        부분 수신을 고려해 중괄호 매칭으로 완전한 딕셔너리 본문이 모일 때까지 대기.
        """
        if not self.udp_receive_buffer:
            return

        prefix = b'barcode_info:'
        buf = self.udp_receive_buffer

        # 프리픽스가 없으면 처리하지 않음
        if prefix not in buf:
            return

        # 프리픽스 이후의 본문에서 딕셔너리 추출
        prefix_idx = buf.find(prefix)
        after = buf[prefix_idx + len(prefix):]

        # 바이트 스트림을 문자열로 디코드
        try:
            after_str = after.decode('utf-8', errors='replace')
        except Exception as e:
            print("[Error] barcode_info decode 실패:", e)
            return

        # 딕셔너리 시작 '{' 탐색
        lbrace_idx = after_str.find('{')
        if lbrace_idx == -1:
            # 아직 본문 시작이 오지 않음
            return

        # 중괄호 레벨 카운팅으로 끝 위치 탐색
        depth = 0
        end_rel_idx = -1
        for i, ch in enumerate(after_str[lbrace_idx:], start=lbrace_idx):
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

        dict_str = after_str[lbrace_idx:end_rel_idx + 1]

        # 파싱 시도: JSON 우선, 실패 시 literal_eval 폴백
        parsed = None
        try:
            try:
                import ujson as json
            except ImportError:
                import json
            json_str = dict_str.replace("'", '"')
            parsed = json.loads(json_str)
        except Exception as e:
            try:
                import ast
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
        consumed_end = prefix_idx + len(prefix) + len(after_str.encode('utf-8')[:end_rel_idx + 1])
        self.udp_receive_buffer = buf[consumed_end:]



    # def handle_barcode_receive(self):
    #     """
    #     서버로부터 'barcode_info: { ... }' 형태의 딕셔너리 문자열을 수신해
    #     그대로 self.barcode_info에 저장한다. 'barcode_info:' 프리픽스는 무시한다.
    #     부분 수신을 고려해 중괄호 매칭으로 완전한 딕셔너리 본문이 모일 때까지 대기.
    #     """
    #     if not self.udp_receive_buffer:
    #         return
    #
    #     prefix = 'barcode_info:'
    #     buf = self.udp_receive_buffer
    #
    #     # 프리픽스가 없으면 처리하지 않음
    #     if prefix not in buf:
    #         return
    #
    #     # 프리픽스 이후의 본문에서 딕셔너리 추출
    #     prefix_idx = buf.find(prefix)
    #     after = buf[prefix_idx + len(prefix):]
    #
    #     # 딕셔너리 시작 '{' 탐색
    #     lbrace_idx = after.find('{')
    #     if lbrace_idx == -1:
    #         # 아직 본문 시작이 오지 않음
    #         return
    #
    #     # 중괄호 레벨 카운팅으로 끝 위치 탐색
    #     depth = 0
    #     end_rel_idx = -1
    #     for i, ch in enumerate(after[lbrace_idx:], start=lbrace_idx):
    #         if ch == '{':
    #             depth += 1
    #         elif ch == '}':
    #             depth -= 1
    #             if depth == 0:
    #                 end_rel_idx = i
    #                 break
    #
    #     if end_rel_idx == -1:
    #         # 아직 전체 딕셔너리가 수신되지 않음
    #         return
    #
    #     dict_str = after[lbrace_idx:end_rel_idx + 1]
    #
    #     # 파싱 시도: JSON 우선, 실패 시 literal_eval 폴백
    #     parsed = None
    #     try:
    #         try:
    #             import ujson as json
    #         except:
    #             import json  # type: ignore
    #         json_str = dict_str.replace("'", '"')
    #         parsed = json.loads(json_str)
    #     except Exception as e:
    #         try:
    #             import ast  # type: ignore
    #             parsed = ast.literal_eval(dict_str)
    #         except Exception as e2:
    #             print("[Error] barcode_info 파싱 실패:", e, e2)
    #             return
    #
    #     if not isinstance(parsed, dict):
    #         print("[Error] barcode_info 형식 오류: dict 아님 ->", type(parsed))
    #         return
    #
    #     self.barcode_info = parsed
    #     print("[Debug] barcode_info dict 저장 완료:", self.barcode_info)
    #
    #     self.barcode_sendStates = dict()
    #     for key, value in self.barcode_info.items():
    #         ret = self.sendBarcode(int(key[-1]), value)
    #         self.barcode_sendStates[key] = ret
    #
    #     time.sleep((self.delay_sensorId + 100) / 1000)
    #     self.isRead_sensorId = True
    #
    #     # 소비한 데이터 제거 (+ 선택적으로 종료 토큰 제거)
    #     consumed_end = prefix_idx + len(prefix) + end_rel_idx + 1
    #     remainder = buf[consumed_end:]
    #     finish_token = 'barcode sending finished'
    #     if finish_token in remainder:
    #         remainder = remainder.replace(finish_token, '')
    #     tcp_receive_buffer = remainder
    #     # self.is_barcode_receiving = False
    # # endregion

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

            # UDP는 연결 개념이 약하므로, 소켓 준비 상태 기준으로 재초기화 시도
            # if not W5500.is_initialized:
            #     conn_state = "DISCONNECTED"
            #     if reconnect_timer <= 0:
            #         print("[*] Trying to (re)initialize UDP socket...")
            #         main.try_init_udp()
            #
            #         if W5500.is_initialized:
            #             print("[*] UDP socket ready")
            #             conn_state = 'CONNECTED'
            #             reconnect_timer = 0
            #         else:
            #             print("[*] UDP init failed")
            #             reconnect_timer = 3000
            #     else:
            #         reconnect_timer -= 1
            # else:
            #     conn_state = "CONNECTED"

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
