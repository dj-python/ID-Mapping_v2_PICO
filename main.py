from machine import Pin, I2C
import time

FIRMWARE_VERSION = 0.1

class Main:
    def __init__(self):
        self.sysLed_picoBrd = Pin(25, Pin.OUT)

        self.i2c = I2C(0, scl=Pin(13), sda=Pin(12), freq=400000)

        # devices = self.i2c.scan()
        # for device in devices:
        #     print(hex(device))

        self.readSensorId()

    def func_1msec(self):
        pass

    def func_10msec(self):
        pass

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
        print("Start readSensorId")
        self.i2c.writeto(0x10, b'\x01\x3E\x00\xC8')
        self.i2c.writeto(0x10, b'\x03\x04\x00\x03')
        self.i2c.writeto(0x10, b'\x03\x06\x01\x13')
        self.i2c.writeto(0x10, b'\x03\x0C\x00\x00')
        self.i2c.writeto(0x10, b'\x03\x0E\x00\x03')
        self.i2c.writeto(0x10, b'\x03\x10\x01\x7C')
        self.i2c.writeto(0x10, b'\x03\x12\x00\x00')
        self.i2c.writeto(0x10, b'\x01\x00\x01\x00')  # streaming On
        time.sleep_ms(20)
        self.i2c.writeto(0x10, b'\x0A\x02\x00\x00')
        self.i2c.writeto(0x10, b'\x0A\x00\x01\x00')
        time.sleep_ms(10)

        self.i2c.writeto(0x10, b'\x0A\x24')
        optValue = self.i2c.readfrom(0x10, 6)
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

        self.i2c.writeto(0x10, b'\x00\x19')
        flag2 = self.i2c.readfrom(0x10, 1)
        print(f'Flag2: {flag2}')

        self.i2c.writeto(0x10, b'\x00\x02')
        revisionId1 = self.i2c.readfrom(0x10, 1)
        print(f'Revision_ID1: {revisionId1}')

        self.i2c.writeto(0x10, b'\x00\x03')
        revisionId2 = self.i2c.readfrom(0x10, 1)
        print(f'Revision_ID2: {revisionId2}')

        self.i2c.writeto(0x10, b'\x00\x0D')
        featureId1 = self.i2c.readfrom(0x10, 1)
        print(f'Feature_ID1: {featureId1}')

        self.i2c.writeto(0x10, b'\x00\x0E')
        featureId2 = self.i2c.readfrom(0x10, 1)
        print(f'Feature_ID2: {featureId2}')

        self.i2c.writeto(0x10, b'\x00\x00')
        modelId1 = self.i2c.readfrom(0x10, 1)
        print(f'Model_ID1: {modelId1}')

        self.i2c.writeto(0x10, b'\x00\x01')
        modelId2 = self.i2c.readfrom(0x10, 1)
        print(f'Model_ID2: {modelId2}')

        self.i2c.writeto(0x10, b'\x00\x16')
        flag0 = self.i2c.readfrom(0x10, 1)
        print(f'Flag0: {flag0}')

        self.i2c.writeto(0x10, b'\x00\x18')
        flag1 = self.i2c.readfrom(0x10, 1)
        print(f'Flag1: {flag1}')

        self.i2c.writeto(0x10, b'\x0A\x00\x00\x00')
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
    main = Main()

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
