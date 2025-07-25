# 4/15 코드 교육 내용 추가됨
from machine import Pin, I2C
import time
import W5500_EVB_PICO as W5500

# 서버 메시지 수신 버퍼
tcp_receive_buffer = b""    # 네트워크 수신 버퍼
script_buffer = ""          # 스크립트 전체 누적 버퍼
is_script_sending = False   # 스크립트 수신 상태 플래그

FIRMWARE_VERSION = 0.0

class Main:
    def __init__(self, server_ip, server_port):
        global ipAddress, portNumber
        print('PICO Start')
        self.is_script_sending = False                              # 스크립트 저장 상태
        self.script_file_name = "script.txt"

        self.sysLed_picoBrd = Pin(25, Pin.OUT)

        self.i2c_0 = I2C(0, scl=Pin(13), sda=Pin(12), freq=400000)
        self.i2c_1 = I2C(1, scl=Pin(11), sda=Pin(10), freq=400000)

        self.resetA = Pin(2, Pin.OUT)
        self.resetB = Pin(3, Pin.OUT)
        self.resetC = Pin(4, Pin.OUT)
        self.resetD = Pin(5, Pin.OUT)

        self.io1v8 = Pin(6, Pin.OUT)

        self.resetA.off()
        self.resetB.off()
        self.resetC.off()
        self.resetD.off()
        self.io1v8.on()
        time.sleep_ms(10)

        self.ipAddress = '192.168.1.101'
        self.gateway = '192.168.1.1'
        self.server_ip = server_ip
        self.server_port = server_port
        # ipAddress = '166.79.26.100'
        # gateway = '166.79.26.1'
        self.barcode_info = {}
        self.is_barcode_receiving = False
        self.sensor_ID = {'Module1':'FAKEID1',
                          'Module2':'FAKEID2',
                          'Module3':'FAKEID3',
                          'Module4':'FAKEID4',
                          'Module5':'FAKEID5'}

    def try_init_tcp(self):
        try:
            W5500.init(ipAddress=self.ipAddress,
                       gateway=self.gateway,
                       server_ip=self.server_ip,
                       server_port=self.server_port)
        except Exception as e:
            print(f"[-] Initialization Error: {str(e)}")

        # print('I2C_0 slave address:')
        # devices = self.i2c_0.scan()
        # for device in devices:
        #     print(hex(device))
        #
        # print('I2C_1 slave address:')
        # devices = self.i2c_1.scan()
        # for device in devices:
        #     print(hex(device))

    def save_to_script_file(self, data):
        """
        서버로부터 청크 데이터를 받아 script.txt 파일에 저장
        """

        print(f"[REPL] {data}")

        # script.txt 파일에 저장
        try:
            with open("script.txt", "wb") as f:
                f.write(data)
            print("[Debug] script.txt에 데이터 저장 완료")
        except Exception as e:
            print(f"[Error] script.txt 파일 저장 중 오류 발생")

    def func_1msec(self):
        pass


    def func_10msec(self):
        global tcp_receive_buffer, is_script_sending

        try:
            chunk = W5500.read_from_socket()
            if chunk:
                tcp_receive_buffer += chunk
        except Exception as e:
            pass

        self.handle_script_receive()
        self.handle_read_sensor_request()
        self.handle_barcode_receive()




    def func_20msec(self):
        pass

    def func_50msec(self):
        pass




    def func_100msec(self):
        pass

    def func_500msec(self):
        self.sysLed_picoBrd(not self.sysLed_picoBrd.value())
        pass

    @staticmethod
    def decoding(value):
        if value < 10:
            result = value + 0x30
        else:
            result = value + 0x37
        return result


    def handle_script_receive(self):
        global tcp_receive_buffer, is_script_sending, mcu_script_status

        # Script send 신호 감지 및 스크립트 수신 시작
        if not is_script_sending and b"Script send" in tcp_receive_buffer:
            idx = tcp_receive_buffer.index(b"Script send")
            tcp_receive_buffer = tcp_receive_buffer[idx + len(b"Script send"):]
            is_script_sending = True
            return

        # 스크립트 수신 종료(EOF) 감지 및 저장
        if is_script_sending and b"EOF" in tcp_receive_buffer:
            idx = tcp_receive_buffer.index(b"EOF")
            script_buffer = tcp_receive_buffer[:idx].decode('utf-8')
            tcp_receive_buffer = tcp_receive_buffer[idx + len(b"EOF"):]
            print("[Debug] Script 수신 완료 - 파일로 저장")
            self.save_to_script_file(script_buffer)
            is_script_sending = False
            for mcu in range(1, 8):
                msg = f"Script save finished: MCU{mcu}\n"
                W5500.sendMessage(msg)

        else:
        # EOF가 없으면 버퍼를 decode/비우지 않고 계속 누적만 함
            return

    def handle_read_sensor_request(self):
        global tcp_receive_buffer
        if b"Read_Sensor" in tcp_receive_buffer:
            idx = tcp_receive_buffer.index(b"Read_Sensor")
            tcp_receive_buffer = tcp_receive_buffer[:idx] + tcp_receive_buffer[idx + len(b"Read_Sensor")]
            self.readSensorId()

            # Write protect: Disable
            self.i2c_0.writeto(0x50, b'\xA0\x00\x06')
            time.sleep_ms(10)  # Write cycle time: 5ms
            # self.i2c_0.writeto(0x50, b'\xA0\x00')
            # temp = self.i2c_0.readfrom(0x50, 1)
            # print(f'E2P write protect: {temp}')

            # Write data
            self.i2c_0.writeto(0x50, b'\x7D\xE3\xAB\xAB\xCC')
            time.sleep_ms(10)

            # Read data
            # self.i2c_0.writeto(0x50, b'\x7D\xE3')
            # temp = self.i2c_0.readfrom(0x50, 15)
            # print('temp:', temp)

            # Write protect: Enable
            self.i2c_0.writeto(0x50, b'\xA0\x00\x0E')
            time.sleep_ms(10)  # Write cycle time: 5ms
            # self.i2c_0.writeto(0x50, b'\xA0\x00')
            # temp = self.i2c_0.readfrom(0x50, 1)
            # print(f'E2P write protect: {temp}')

            # Power Off
            data = bytearray([0x00])

            self.i2c_1.writeto_mem(0x20, 0x09, data)

    def handle_barcode_receive(self):
        """
        서버로부터 'barcode'로 시작하는 데이터를 받아서 barcode_info에 저장.
        'barcode sending finished'가 오면 저장 종료 후 sensor_ID와 barcode_info를 서버로 송신.
        """
        global tcp_receive_buffer

        # 바코드 데이터 수신 시작
        while True:
            # 바코드 시작 플래그가 없고, 'barcode'로 시작하는 데이터가 있으면 수신 시작
            if not self.is_barcode_receiving and b'barcode' in tcp_receive_buffer:
                self.is_barcode_receiving = True

            # 바코드 수신 상태일 때만 처리
            if self.is_barcode_receiving:
                # 바코드 한 줄씩 추출
                lines = tcp_receive_buffer.split(b'\n')
                new_buffer = b''
                for line in lines:
                    # barcode로 시작하는 형식에 매칭되는지 확인
                    if line.startswith(b'barcode'):
                        try:
                            text = line.decode('utf-8').strip()
                            if ':' in text:
                                key, value = text.split(':', 1)
                                self.barcode_info[key.strip()] = value.strip()
                        except Exception as e:
                            print(f"[Error] 바코드 데이터 디코딩/저장 오류: {e}")
                    elif b'barcode sending finished' in line:
                        # 바코드 데이터 수신 종료
                        self.is_barcode_receiving = False
                        print("[Debug] barcode 데이터 저장 완료:", self.barcode_info)
                        # 0.5초 대기 후 sensor_ID, barcode_info 전송
                        time.sleep_ms(500)
                        try:
                            # sensor_ID 송신
                            W5500.sendMessage(f"sensor_ID: {self.sensor_ID}\n")
                            # barcode_info 송신
                            W5500.sendMessage(f"barcode_info: {self.barcode_info}\n")
                            print("[Debug] sensor_ID, barcode_info 서버로 송신 완료")
                        except Exception as e:
                            print(f"[Error] sensor_ID/barcode_info 송신 실패: {e}")
                        # barcode sending finished 이후 남은 데이터는 버퍼에 남김
                        idx = line.index(b'barcode sending finished')
                        new_buffer += line[idx + len(b'barcode sending finished'):]
                        print(self.barcode_info)
                    else:
                        # barcode, barcode sending finished와 무관한 데이터는 남겨두기
                        new_buffer += line + b'\n'
                tcp_receive_buffer = new_buffer
                break
            else:
                break

    def readSensorId(self):

        # IODIR
        data = bytearray([0x00])
        self.i2c_1.writeto_mem(0x20, 0x00, data)
        # temp = self.i2c_1.readfrom_mem(0x20, 0x00, 1)
        # print(f'IODIR: {temp}')

        data = bytearray([0x00])
        self.i2c_1.writeto_mem(0x21, 0x00, data)

        data = bytearray([0x00])
        self.i2c_1.writeto_mem(0x22, 0x00, data)

        data = bytearray([0x00])
        self.i2c_1.writeto_mem(0x23, 0x00, data)

        # Set GPIO
        data = bytearray([0xff])
        self.i2c_1.writeto_mem(0x20, 0x09, data)
        # temp = self.i2c_1.readfrom_mem(0x20, 0x09, 1)
        # print(f'GPIO: {temp}')

        data = bytearray([0x00])
        self.i2c_1.writeto_mem(0x21, 0x09, data)

        data = bytearray([0x00])
        self.i2c_1.writeto_mem(0x22, 0x09, data)

        data = bytearray([0x00])
        self.i2c_1.writeto_mem(0x23, 0x09, data)

        time.sleep_ms(10)
        self.resetA.on()
        time.sleep_ms(10)

        # I2C Selector
        self.i2c_0.writeto(0x71, b'\x01')
        # temp = self.i2c_0.readfrom(0x71, 1)
        # print(temp)

        print('I2C_0 slave address:')
        devices = self.i2c_0.scan()
        for device in devices:
            print(hex(device))

        time.sleep_ms(10)
        print("Start readSensorId")
        self.i2c_0.writeto(0x10, b'\x01\x36\x13\x00')
        self.i2c_0.writeto(0x10, b'\x01\x3E\x00\xC8')
        self.i2c_0.writeto(0x10, b'\x03\x04\x00\x03')
        self.i2c_0.writeto(0x10, b'\x03\x06\x01\x13')
        self.i2c_0.writeto(0x10, b'\x03\x0C\x00\x00')
        self.i2c_0.writeto(0x10, b'\x03\x0E\x00\x03')
        self.i2c_0.writeto(0x10, b'\x03\x10\x01\x7C')
        self.i2c_0.writeto(0x10, b'\x03\x12\x00\x00')
        self.i2c_0.writeto(0x10, b'\x01\x00\x01\x00')  # streaming On
        time.sleep_ms(20)
        self.i2c_0.writeto(0x10, b'\x0A\x02\x00\x00')
        self.i2c_0.writeto(0x10, b'\x0A\x00\x01\x00')
        time.sleep_ms(10)
        self.i2c_0.writeto(0x10, b'\x0A\x24')
        optValue = self.i2c_0.readfrom(0x10, 6)
        print(f'0x0A24~0x0A29: {optValue}')

        optValue = int.from_bytes(optValue, 'big')
        str_optValue = f'{optValue:048b}'
        print(len(str_optValue), str_optValue)

        lot_id1 = self.decoding(int(str_optValue[0:6], 2))
        lot_id2 = self.decoding(int(str_optValue[6:12], 2))
        lot_id3 = self.decoding(int(str_optValue[12:18], 2))
        lot_id4 = self.decoding(int(str_optValue[18:24], 2))
        wf_no = int(str_optValue[24:29], 2)
        x_coordinate = int(str_optValue[29:37], 2)
        y_coordinate = int(str_optValue[37:45], 2)
        print(lot_id1, lot_id2, lot_id3, lot_id4, wf_no, x_coordinate, y_coordinate)

        self.i2c_0.writeto(0x10, b'\x00\x19')
        flag2 = self.i2c_0.readfrom(0x10, 1)
        print(f'Flag2: {flag2}')

        self.i2c_0.writeto(0x10, b'\x00\x02')
        revisionId1 = self.i2c_0.readfrom(0x10, 1)
        print(f'Revision_ID1: {revisionId1}')

        self.i2c_0.writeto(0x10, b'\x00\x03')
        revisionId2 = self.i2c_0.readfrom(0x10, 1)
        print(f'Revision_ID2: {revisionId2}')

        self.i2c_0.writeto(0x10, b'\x00\x0D')
        featureId1 = self.i2c_0.readfrom(0x10, 1)
        print(f'Feature_ID1: {featureId1}')

        self.i2c_0.writeto(0x10, b'\x00\x0E')
        featureId2 = self.i2c_0.readfrom(0x10, 1)
        print(f'Feature_ID2: {featureId2}')

        self.i2c_0.writeto(0x10, b'\x00\x00')
        modelId1 = self.i2c_0.readfrom(0x10, 1)
        print(f'Model_ID1: {modelId1}')

        self.i2c_0.writeto(0x10, b'\x00\x01')
        modelId2 = self.i2c_0.readfrom(0x10, 1)
        print(f'Model_ID2: {modelId2}')

        self.i2c_0.writeto(0x10, b'\x00\x16')
        flag0 = self.i2c_0.readfrom(0x10, 1)
        print(f'Flag0: {flag0}')

        self.i2c_0.writeto(0x10, b'\x00\x18')
        flag1 = self.i2c_0.readfrom(0x10, 1)
        print(f'Flag1: {flag1}')

        self.i2c_0.writeto(0x10, b'\x0A\x00\x00\x00')
        print('End readSensorId')

        sensorId = bytes()
        sensorId += lot_id1.to_bytes(1, 'big')
        sensorId += lot_id2.to_bytes(1, 'big')
        sensorId += lot_id3.to_bytes(1, 'big')
        sensorId += lot_id4.to_bytes(1, 'big')
        sensorId += flag2
        sensorId += wf_no.to_bytes(1, 'big')
        sensorId += x_coordinate.to_bytes(1, 'big')
        sensorId += y_coordinate.to_bytes(1, 'big')
        sensorId += revisionId1
        sensorId += revisionId2
        sensorId += featureId1
        sensorId += featureId2
        sensorId += modelId1
        sensorId += modelId2
        sensorId += flag0
        sensorId += flag1

        print(f'Final sensor ID: {sensorId}')


if __name__ == "__main__":
    cnt_msec = 0

    ipAddress = '192.168.1.101'
    gateway = '192.168.1.1'
    server_ip = '192.168.1.2'
    server_port = 8000

    main = Main(server_ip, server_port)

    # 상태머신 구조
    # 상태 : "DISCONNECTED", "CONNECTED"
    conn_state = "CONNECTED" if W5500.is_initialized else "DISCONNECTED"
    reconnect_timer = 0

    while True:
        try:
            cnt_msec += 1

            # 연결이 끊어진 경우에만 재접속 시도
            if not W5500.is_initialized:
                conn_state = "DISCONNECTED"
                if reconnect_timer <= 0:
                    print("[*] Trying to reconnect to server...")
                    main.try_init_tcp()
                    if W5500.is_initialized:
                        print("[*] Reconnected to server")
                        conn_state = 'CONNECTED'
                        reconnect_timer = 0
                    else:
                        print("[*] Reconnect failed")
                        reconnect_timer = 3000
                else:
                    reconnect_timer -= 1
            else:
                conn_state = "CONNECTED"

            if not cnt_msec % 10:
                if W5500.is_initialized :
                    main.func_10msec()

            if not cnt_msec % 20:
                main.func_20msec()

            if not cnt_msec % 50:
                main.func_50msec()

            if not cnt_msec % 100:
                main.func_100msec()

            if not cnt_msec % 500:
                main.func_500msec()

            time.sleep_ms(1)
        except KeyboardInterrupt:
            print("KeyboardInterrupt: cleaning up TCP...")
            W5500.close_connection()
            break
        except Exception as e:
            print("Exception in main loop", e)
            import sys
            sys.print_exception(e)



    # IO 보드는 안정적인 재접속을 위해 루프 함수를 아래와 같이 변경함. (7/7)
    # Writecard 도 향후 변경 검토 필요.

    # while True:
    #     try:
    #         cnt_msec += 1
    #
    #         # 항상 TCPClient 상태 확인, 끊어진 경우 즉시 재접속 시도
    #         if not TCPClient.is_initialized:
    #             conn_state = "DISCONNECTED"
    #             if reconnect_timer <= 0:
    #                 print("[*] Trying to reconnect to server...")
    #                 main.try_init_tcp()
    #                 if TCPClient.is_initialized:
    #                     print("[*] Reconnected to server")
    #                     conn_state = 'CONNECTED'
    #                     reconnect_timer = 0
    #                 else:
    #                     print("[*] Reconnect failed")
    #                     reconnect_timer = 3000
    #             else:
    #                 reconnect_timer -= 1
    #         else:
    #             conn_state = 'CONNECTED'
    #
    #         if not cnt_msec % 10:
    #             if TCPClient.is_initialized :
    #                 main.func_10msec()
    #
    #         if not cnt_msec % 25:
    #             main.func_25msec()
    #
    #         if not cnt_msec % 100:
    #             main.func_100msec()
    #
    #         if not cnt_msec % 500:
    #             main.func_500msec()
    #
    #         time.sleep_ms(1)
    #     except KeyboardInterrupt:
    #         print("KeyboardInterrupt: cleaning up TCP...")
    #         TCPClient.close_connection()
    #         break
    #     except Exception as e:
    #         print("Exception in main loop", e)
    #         import sys
    #         sys.print_exception(e)
