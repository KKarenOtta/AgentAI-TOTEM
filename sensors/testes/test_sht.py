import time, board, adafruit_sht31d
i2c = board.I2C()
s = adafruit_sht31d.SHT31D(i2c)
while True:
    print("Temp:", s.temperature, "Hum:", s.relative_humidity)
    time.sleep(1)