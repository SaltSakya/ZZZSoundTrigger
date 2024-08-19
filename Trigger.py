import time
import random

import serial

import numpy as np

import librosa

import pydirectinput

import win32con
import win32api

import vgamepad

import ctypes
from ctypes import wintypes

from Listener import GameAudioListener

user32 = ctypes.WinDLL('user32', use_last_error=True)
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
INPUT_HARDWARE = 2
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MAPVK_VK_TO_VSC = 0


class MOUSEINPUT(ctypes.Structure):
    _fields_ = (("dx", wintypes.LONG),
                ("dy", wintypes.LONG),
                ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", wintypes.WPARAM))


class KEYBDINPUT(ctypes.Structure):
    _fields_ = (("wVk", wintypes.WORD),
                ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", wintypes.WPARAM))

    def __init__(self, *args, **kwds):
        super(KEYBDINPUT, self).__init__(*args, **kwds)
        if not self.dwFlags & KEYEVENTF_UNICODE:
            self.wScan = user32.MapVirtualKeyExW(self.wVk,
                                                 MAPVK_VK_TO_VSC, 0)


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = (("uMsg", wintypes.DWORD),
                ("wParamL", wintypes.WORD),
                ("wParamH", wintypes.WORD))


class INPUT(ctypes.Structure):
    class _INPUT(ctypes.Union):
        _fields_ = (("ki", KEYBDINPUT),
                    ("mi", MOUSEINPUT),
                    ("hi", HARDWAREINPUT))

    _anonymous_ = ("_input",)
    _fields_ = (("type", wintypes.DWORD),
                ("_input", _INPUT))


class SoftKbMouse:
    PRESS_TIME = 0.1
    SHORT_PRESS_TIME = 0.01

    def __init__(self):
        pass


class SoftKbMouseV3(SoftKbMouse):
    # 系统层实现: https://stackoverflow.com/questions/54624221/simulate-physical-keypress-in-python-without-raising
    # -lowlevelkeyhookinjected-0/54638435#54638435
    def __init__(self):
        super().__init__()

    def PressKey(self, hexKeyCode):
        x = INPUT(type=INPUT_KEYBOARD,
                  ki=KEYBDINPUT(wVk=hexKeyCode))
        user32.SendInput(1, ctypes.byref(x), ctypes.sizeof(x))

    def ReleaseKey(self, hexKeyCode):
        x = INPUT(type=INPUT_KEYBOARD,
                  ki=KEYBDINPUT(wVk=hexKeyCode,
                                dwFlags=KEYEVENTF_KEYUP))
        user32.SendInput(1, ctypes.byref(x), ctypes.sizeof(x))

    def Mouse(self, dx, dy, flags):
        x = INPUT(type=INPUT_MOUSE, mi=MOUSEINPUT(dx, dy, 0, flags, 0, 0))
        user32.SendInput(1, ctypes.byref(x), ctypes.sizeof(INPUT))

    def push_space(self):
        self.PressKey(0x20)
        time.sleep((random.random() + 1.0) * self.PRESS_TIME)  # human-like
        self.ReleaseKey(0x20)

    def dodge(self):
        self.Mouse(0, 0, MOUSEEVENTF_RIGHTDOWN)
        time.sleep((random.random() + 1.0) * self.PRESS_TIME)  # human-like
        self.Mouse(0, 0, MOUSEEVENTF_RIGHTUP)

    def double_dodge(self):
        self.Mouse(0, 0, MOUSEEVENTF_RIGHTDOWN)
        self.Mouse(0, 0, MOUSEEVENTF_RIGHTUP)
        time.sleep(self.SHORT_PRESS_TIME)
        self.Mouse(0, 0, MOUSEEVENTF_LEFTDOWN)
        self.Mouse(0, 0, MOUSEEVENTF_LEFTUP)
        time.sleep(self.SHORT_PRESS_TIME)
        self.PressKey(0x20)
        self.ReleaseKey(0x20)


class SoftKbMouseV2(SoftKbMouse):
    def __init__(self):
        super().__init__()
        self.press = pydirectinput.press
        self.leftClick = pydirectinput.leftClick
        self.rightClick = pydirectinput.rightClick

    def push_space(self):
        self.press('space', interval=(random.random() + 1.0) * self.PRESS_TIME)

    def dodge(self):
        self.rightClick(interval=(random.random() + 1.0) * self.PRESS_TIME)

    def double_dodge(self):
        self.rightClick(_pause=False)
        time.sleep(self.SHORT_PRESS_TIME)
        self.leftClick(_pause=False)
        time.sleep(self.SHORT_PRESS_TIME)
        self.press('space')


class SoftKbMouseV1(SoftKbMouse):
    def __init__(self):
        super().__init__()
        self.button = win32api.keybd_event
        self.mouse_button = win32api.mouse_event
        self.space_key = win32con.VK_SPACE
        self.relax = win32con.KEYEVENTF_KEYUP
        self.mouse_key = win32con.VK_SPACE

    def push_space(self):
        self.button(self.space_key, 0, 0, 0)
        time.sleep((random.random() + 1.0) * self.PRESS_TIME)  # human-like
        self.button(self.space_key, 0, self.relax, 0)


class HardKbMouse:
    ENTER_OPERATION = '\r\n'
    LINUX_ENTER_OPERATION = '\n'
    INFO = '[INFO] '
    ERROR = '[ERROR] '
    PROG = '[PROGRESS]'
    ENCODING = 'utf-8'
    SPACE_KEY = 44
    PAUSE = 0.005
    PRESS_TIME = 100  # ms

    # 完整发送应答
    def _UartSendCmdWaitforAsk(self, content: str, timeout=10):
        control_c = '\003'
        send = bytes(content + self.ENTER_OPERATION, self.ENCODING)
        return_content = ""
        self.session.write(send)
        time.sleep(self.PAUSE)
        while True:
            response = self.session.read(self.session.in_waiting).decode(self.ENCODING)
            if response:
                return_content += response
            if '>>>' in response:
                return True, return_content
            elif '...' in response:
                self.session.write(bytes(control_c, self.ENCODING))
                time.sleep(self.PAUSE)
                self.session.write(send)
                time.sleep(self.PAUSE)
            else:
                time.sleep(self.PAUSE)
                timeout -= 1
                if timeout <= 0:
                    return False, return_content

    def __init__(self, com_name: str):
        # 连接开发板
        self.session = serial.Serial(com_name, 115200)
        status, response = self._UartSendCmdWaitforAsk('km.version()', 100)
        if status:
            print(self.INFO, response.replace(self.ENTER_OPERATION, ''))
        else:
            raise serial.serialutil.SerialException(self.ERROR,
                                                    "could not open port {}: FileNotFoundError(2, '系统找不到指定的文件。', None, 2)".format(
                                                        com_name))

    def push_space(self):
        random_pressing = int((random.random() + 1.0) * self.PRESS_TIME)  # ms, human-like
        status, response = self._UartSendCmdWaitforAsk('km.press({},{})'.format(self.SPACE_KEY, random_pressing), 100)
        if status:
            print(self.PROG, "执行完毕".format(response))
        else:
            print(self.ERROR, "执行脚本出错, info: {}".format(response))

class GamePad:
    SHORT_PRESS_TIME = 0.1
    def __init__(self, gamepad_type="X360"):
        if gamepad_type == "DS4":
            self.gamepad = vgamepad.VDS4Gamepad()
        else:
            self.gamepad = vgamepad.VX360Gamepad()

    def downFuncPress(self):
        self.gamepad.press_button(button=vgamepad.XUSB_BUTTON.XUSB_GAMEPAD_A)
        self.gamepad.update()
        time.sleep(GamePad.SHORT_PRESS_TIME)
        self.gamepad.release_button(button=vgamepad.XUSB_BUTTON.XUSB_GAMEPAD_A)
        self.gamepad.update()

    def leftFuncPress(self):
        self.gamepad.press_button(button=vgamepad.XUSB_BUTTON.XUSB_GAMEPAD_X)
        self.gamepad.update()
        time.sleep(GamePad.SHORT_PRESS_TIME)
        self.gamepad.release_button(button=vgamepad.XUSB_BUTTON.XUSB_GAMEPAD_X)
        self.gamepad.update()

    def rightShoulder(self):
        self.gamepad.press_button(button=vgamepad.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER)
        self.gamepad.update()
        time.sleep(GamePad.SHORT_PRESS_TIME)
        self.gamepad.release_button(button=vgamepad.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER)
        self.gamepad.update()

    def dodge(self):
        self.downFuncPress()

    def double_dodge(self):
        self.downFuncPress()
        time.sleep(GamePad.SHORT_PRESS_TIME)
        self.leftFuncPress()
        time.sleep(GamePad.SHORT_PRESS_TIME)
        self.rightShoulder()

    def push_space(self):
        self.rightShoulder()

class DodgingTrigger(GameAudioListener):
    monitor_time = 5  # 秒

    def __init__(self, sample_path: str, action, threshold=0.1, ratio=1.0, is_allowed_succe_dodge=False, callback=None):
        self.action = action
        self.threshold = threshold
        self.is_allowed_succe_dodge = is_allowed_succe_dodge
        self.run = True
        super().__init__(sample_path, ratio)
        if callback is not None:
            callback(self)

    def setAction(self, action):
        self.action = action
    
    def setThreshold(self, threshold):
        self.threshold = threshold

    def setRatio(self, ratio):
        self.ratio = ratio

    def setSucTri(self, is_allowed_succe_dodge):
        self.is_allowed_succe_dodge = is_allowed_succe_dodge

    def stop(self):
        self.run = False


    def online_listening(self):
        print("开始监测")

        last_frames = np.empty(shape=(0,), dtype=np.float64)
        is_not_past_triggered = True

        with self.audio_instance as audio_recorder:
            while self.run:
                current_frame = np.empty(shape=(0,), dtype=np.float64)
                for index in range(int(self.used_sr / self.chunk_size * self.sample_len)):
                    stream_data = audio_recorder.record(numframes=self.chunk_size)
                    read_chunks = librosa.to_mono(stream_data.T)

                    current_frame = np.append(current_frame, read_chunks)

                # 积累完成,计算匹配分数
                combined_frames = np.append(last_frames, current_frame)
                max_score = self.matching(combined_frames)

                if max_score >= self.threshold:
                    if is_not_past_triggered or self.is_allowed_succe_dodge:  # 是否可以连续激发
                        self.action()  # 触发动作
                        trigger_text = "触发分数: {}".format(round(max_score, 5))
                        print(trigger_text)

                        is_not_past_triggered = False
                else:
                    is_not_past_triggered = True

                last_frames = current_frame
