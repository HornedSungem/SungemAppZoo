#! /usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright(c) 2018 Senscape Corporation.
# License: Apache 2.0

import os
os.chdir(os.path.dirname(os.path.realpath(__file__)))
import sys
sys.path.append('../SungemSDK-Python')
import hsapi as hs # pylint: disable=E0401
import cv2
import numpy
import time
import RPi.GPIO as GPIO
from enum import Enum, unique
import threading


class Car:
    gpio_mode = GPIO.BCM
    gpio_l = (18, 22, 27) # PWM, IN1, IN2
    gpio_r = (23, 25, 24) # PWM, IN1, IN2

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        GPIO.setwarnings(False)
        GPIO.setmode(self.gpio_mode)
        for gpio in self.gpio_l+self.gpio_r:
            GPIO.setup(gpio, GPIO.OUT)
        self.motor_l = GPIO.PWM(self.gpio_l[0], 100)
        self.motor_r = GPIO.PWM(self.gpio_r[0], 100)

    def shutdown(self):
        GPIO.cleanup()

    def _run(self, speed, outputs, t_time):
        self.motor_l.ChangeDutyCycle(speed)
        GPIO.output(self.gpio_l[1], outputs[0])
        GPIO.output(self.gpio_l[2], outputs[1])
        self.motor_r.ChangeDutyCycle(speed)
        GPIO.output(self.gpio_r[1], outputs[2])
        GPIO.output(self.gpio_r[2], outputs[3])
        time.sleep(t_time)

    def start(self):
        self.motor_l.start(0)
        self.motor_r.start(0)

    def stop(self, t_time):
        self._run(0, (False, False, False, False), t_time)

    def up(self, speed, t_time):
        self._run(speed, (True, False, True, False), t_time)

    def down(self, speed, t_time):
        self._run(speed, (False, True, False, True), t_time)

    def left(self, speed, t_time):
        self._run(speed, (False, True, True, False), t_time)

    def right(self, speed, t_time):
        self._run(speed, (True, False, False, True), t_time)


@unique
class Direction(Enum):
    stop = 0
    up = 1
    down = 2
    left = 3
    right = 4


class Driver:
    direction = Direction.stop

    def __init__(self, car):
        self.car = car
        self.__flag = threading.Event()
        self.__flag.clear()
        self.__thread = threading.Thread(target=self._run)
        self.__thread.daemon = True
        self.__thread.start()

    def active(self):
        self.__flag.set()

    def inactive(self):
        self.__flag.clear()

    def _run(self):
        try:
            self.car.start()
            while True:
                self.__flag.wait()
                if self.direction is Direction.up:
                    self.car.up(25, 0.2)
                elif self.direction is Direction.down:
                    self.car.down(25, 0.2)
                elif self.direction is Direction.left:
                    self.car.left(12, 0.1)
                elif self.direction is Direction.right:
                    self.car.left(12, 0.1)
                else:
                    self.car.stop(0.2)
        finally:
            self.car.shutdown()

    def track(self, result, tag=1):
        objs = [x for x in result[1] if x[0] in {tag}]
        if len(objs) > 0:  # 当检测到目标物体时
            obj = objs[0]
            x_mid = (obj[2] + obj[4]) / 2 / result[0].shape[1]
            if x_mid < 0.4:  # 目标在左前方
                self.direction = Direction.left
            elif x_mid > 0.6:  # 目标在右前方
                self.direction = Direction.right
            else:  # 目标在正前方
                self.direction = Direction.up
        else:
            self.direction = Direction.stop


def main():
    time.sleep(5)
    net = hs.ObjectDetector(zoom=True, thresh=0.2, graphPath="./graph_object_SSD")
    driver = Driver(Car())
    driver.active()
    try:
        while True:
            result = net.run()
            driver.track(result)
    finally:
        net.quit()


if __name__ == "__main__":
    sys.exit(main())
