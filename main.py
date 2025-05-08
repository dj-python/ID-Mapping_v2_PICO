# 4/15 코드 교육 내용 추가됨

from machine import Pin, I2C
import time
import W5500_EVB_PICO as W5500
import network
import socket

FIRMWARE_VERSION = 0.0

class Main:
    def __init__(self, server_ip, server_port):
        print('PICO Start')
        print(dir(network))
        print(dir(network.WIZNET5K))
        # print(socket.__file__)
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

        ipAddress = '192.168.1.100'
        gateway = '192.168.1.1'
        # ipAddress = '166.79.26.100'
        # gateway = '166.79.26.1'

        try:
            W5500.init(ipAddress=ipAddress, gateway=gateway, server_ip=server_ip, server_port=server_port)
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
        try:
            # 청크 데이터를 수신
            data = W5500.receiveChunks()
            if data:
                with open(self.script_file_name, "a") as file:
                    file.write(data+ "\n")                   # 데이터를 파일에 저장
                    print(f"[*] Data saved to {self.script_file_name}")
            else:
                print("[!] No data received to save")
        except Exception as e:
            print(f"[!] Error saving to file: {e}")

    def func_1msec(self):
        pass

    def func_10msec(self):
        if not W5500.is_initialized:
            print("[-] TCP socket is not initialized, skipping readMessage.")
            return

        message, address = W5500.readMessage()
        if message is not None:
            print(message, address)

            if message == "Script send":
                print("Starting script saving...")
                self.is_script_sending = True

            # 데이터 저장 중이면 파일에 저장
            elif self.is_script_sending:
                if message == "Script sending finished":
                    print("Script saving finished")
                    self.is_script_sending = False
                else:
                    self.save_to_script_file(message)


            elif message == "Read_Sensor":
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
