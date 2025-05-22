# 4/15 코드 교육 내용 추가됨

from machine import Pin, I2C
import time
import W5500_EVB_PICO as W5500
import network
import socket

from W5500_EVB_PICO import tcpSocket, is_initialized


# 서버 메시지 수신 버퍼
tcp_receive_buffer = b""    # 네트워크 수신 버퍼
script_buffer = ""          # 스크립트 전체 누적 버퍼
is_script_sending = False   # 스크립트 수신 상태 플래그

FIRMWARE_VERSION = 0.0

class Main:
    def __init__(self, server_ip, server_port):
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

        ipAddress = '192.168.1.300'
        portNumber = 8003
        gateway = '192.168.1.1'
        # ipAddress = '166.79.26.100'
        # gateway = '166.79.26.1'

        try:
            W5500.init(ipAddress=ipAddress, portNumber=portNumber, gateway=gateway, server_ip=server_ip, server_port=server_port)
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

        if not W5500.is_initialized:
            print("[-] TCP socket is not initialized, skipping readMessage.")
            return

        # 1. 소켓에서 데이터 chunk 받아오기
        chunk = W5500.read_from_socket()
        if chunk:
            tcp_receive_buffer += chunk

        # 2. 버퍼에서 메시지 파싱
        #   'Script send' 신호 수신 -> 스크립트 수신 시작
        #   'EOF' 수신 전까지 모두 누적 (decode 하지 않음) -> 'EOF' 도착 시 한번에 decode 하여 script.txt로 저장
        while True:
            # Script send 신호 감지 및 스크립트 수신 시작
            if not is_script_sending and b"Script send" in tcp_receive_buffer:
                idx = tcp_receive_buffer.index(b"Script send")
                tcp_receive_buffer = tcp_receive_buffer[idx + len(b"Script send"):]
                is_script_sending = True
                continue

            # 스크립트 수신 종료(EOF) 감지 및 저장
            if is_script_sending:
                if b"EOF" in tcp_receive_buffer:
                    idx = tcp_receive_buffer.index(b"EOF")
                    # 오직 여기서만 decode!
                    script_buffer = tcp_receive_buffer[:idx].decode('utf-8')
                    tcp_receive_buffer = tcp_receive_buffer[idx + len(b"EOF"):]
                    print("[Debug] Script 수신 완료 - 파일로 저장")
                    self.save_to_script_file(script_buffer)
                    is_script_sending = False
                else:
                    # EOF가 없으면 버퍼를 decode/비우지 않고 계속 누적만 함
                    break

            break



        if b"Read_Sensor" in tcp_receive_buffer:
            idx = tcp_receive_buffer.index(b"Read Sensor")
            tcp_receive_buffer = tcp_receive_buffer[:idx] + tcp_receive_buffer[idx+len(b"Read Sensor"):]
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
    server_ip = '192.168.1.2'
    server_port = 8000
    main = Main(server_ip, server_port)


    while True:
        cnt_msec += 1
        main.func_1msec()

        if not cnt_msec % 10:
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


"""
        message = W5500.readMessage()
        print(f"[Debug] Message received in func_10msec: \n{message}")        # 디버깅 메시지
        if message is not None:
            print(message)

            if message == "Script send":
                print("Starting script saving...")
                self.is_script_sending = True

            elif message != "Script send" and self.is_script_sending and message != "EOF":
                print(f"[Debug] save_to_script_file 함수 실행, message: {message}")
                # 메시지 수신 및 처리
                self.save_to_script_file(message)
"""
