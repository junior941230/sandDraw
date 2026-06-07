import serial
from serial.tools.list_ports import comports
import time


class ESP32Serial:
    def __init__(self):
        self.serialHandler = None
        self.baud_rate = 115200

    def find_esp32(self):
        ports = comports()

        esp_keywords = ['CP210', 'CH340', 'CH341']

        for port in ports:
            for keyword in esp_keywords:
                if keyword.lower() in port.description.lower():
                    print(f"找到 ESP32：{port.device} ({port.description})")
                    return True, port.device

        print("找不到 ESP32，目前可用的 Port：")
        for port in ports:
            print(f"   {port.device} - {port.description}")
        return False, None

    def isConnected(self):
        return self.serialHandler is not None and self.serialHandler.is_open

    def connect(self):
        try:
            find, port = self.find_esp32()
            if not find:
                print("無法連接到 ESP32，請檢查連接並重試。")
                return False
            self.serialHandler = serial.Serial(port, self.baud_rate, timeout=1)
            time.sleep(1)  # 等待 ESP32 重置
            print(f"成功連接到 ESP32：{port}")
            self.serialHandler.flush()  # 清除緩衝區
            return True
        except serial.SerialException as e:
            print(f"連接失敗：{e}")
            return False

    def disconnect(self):
        if self.serialHandler and self.serialHandler.is_open:
            self.serialHandler.flush()
            self.serialHandler.close()
            print("已斷開與 ESP32 的連接。")

    def send(self, data: str) -> bool:
        if self.serialHandler and self.serialHandler.is_open:
            try:
                self.serialHandler.write(data.encode())
                print(f"已發送數據：{data}")
                return True
            except serial.SerialException as e:
                print(f"發送失敗：{e}")
                return False
        else:
            print("無法發送數據，請先連接到 ESP32。")
            return False
        
    def hasData(self) -> bool:
        """檢查是否有資料可讀，不阻塞"""
        if self.serialHandler and self.serialHandler.is_open:
            return self.serialHandler.in_waiting > 0
        return False

    def receive(self) -> str:
        if self.serialHandler and self.serialHandler.is_open:
            try:
                # readline() 只在確定有資料時呼叫，避免無謂等待
                data = self.serialHandler.readline().decode("utf-8", errors="replace").strip()
                if data:
                    print(f"收到數據：{data}")
                return data
            except serial.SerialException as e:
                print(f"接收失敗：{e}")
                return ""
        return ""


if __name__ == "__main__":
    esp32_serial = ESP32Serial()
