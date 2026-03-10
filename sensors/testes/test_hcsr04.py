import time
import RPi.GPIO as GPIO

TRIG=23
ECHO=24
GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)
GPIO.output(TRIG, False)
time.sleep(0.5)

def distance_m():
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)

    start=time.time()
    while GPIO.input(ECHO)==0:
        if time.time()-start>0.03: return None
    t0=time.time()

    while GPIO.input(ECHO)==1:
        if time.time()-t0>0.03: return None
    t1=time.time()

    return ((t1-t0)*343)/2

try:
    while True:
        d=distance_m()
        print("dist(m):", None if d is None else round(d, 2))
        time.sleep(0.2)
finally:
    GPIO.cleanup()