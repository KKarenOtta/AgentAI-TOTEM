from smbus2 import SMBus

ADDR=0x68
def bcd_to_int(b): return ((b>>4)*10) + (b & 0x0F)

with SMBus(1) as bus:
    data = bus.read_i2c_block_data(ADDR, 0x00, 7)
    sec=bcd_to_int(data[0]&0x7F)
    minute=bcd_to_int(data[1]&0x7F)
    hour=bcd_to_int(data[2]&0x3F)
    day=bcd_to_int(data[4]&0x3F)
    month=bcd_to_int(data[5]&0x1F)
    year=2000+bcd_to_int(data[6])
    print(f"{year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{sec:02d}")