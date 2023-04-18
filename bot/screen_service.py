import ctypes
import os
import time
from ctypes import windll

import pyautogui
import pygame
import pynput
import win32api
import win32con
import win32gui

from constants import fuchsia, NOT_TOPMOST, TOPMOST, WINDOW, screen_width, screen_height, green, blue, fov_width, \
    fov_height, NO_MOVE, NO_SIZE, CT, T_HEAD, T, CT_HEAD


class ScreenService:
    def __init__(self):
        x = 0
        y = 0
        os.environ['SDL_VIDEO_WINDOW_POS'] = "%d,%d" % (x, y)
        fpsClock = pygame.time.Clock()
        pygame.init()
        self.screen = pygame.display.set_mode((1920, 1080), pygame.HWSURFACE)  # For borderless, use pygame.NOFRAME
        self.screen.fill(fuchsia)
        done = False
        hwnd = pygame.display.get_wm_info()[WINDOW]
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE,
                               win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) | win32con.WS_EX_LAYERED)
        win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(*fuchsia), 0, win32con.LWA_COLORKEY)

        self.SetWindowPos = windll.user32.SetWindowPos
        self.always_on_top(True)
        self.SendInput = ctypes.windll.user32.SendInput

        pyautogui.PAUSE = 0

        self.classesNames = [CT, CT_HEAD, T, T_HEAD]

    def always_on_top(self, yesOrNo):
        z_order = (NOT_TOPMOST, TOPMOST)[yesOrNo]  # choose a flag according to bool
        hwnd = pygame.display.get_wm_info()[WINDOW]  # handle to the window
        self.SetWindowPos(hwnd, z_order, 0, 0, 0, 0, NO_MOVE | NO_SIZE)

    def set_crosshair(self, x, y):
        x = 1 + int(x * 65536. / screen_width)
        y = 1 + int(y * 65536. / screen_height)
        extra = ctypes.c_ulong(0)
        ii_ = pynput._util.win32.INPUT_union()
        ii_.mi = pynput._util.win32.MOUSEINPUT(x, y, 0, (0x0001 | 0x8000), 0,
                                               ctypes.cast(ctypes.pointer(extra), ctypes.c_void_p))
        command = pynput._util.win32.INPUT(ctypes.c_ulong(0), ii_)
        self.SendInput(1, ctypes.pointer(command), ctypes.sizeof(command))

    def draw_text(self, text, x, y, background_color=green, text_color=blue, text_size=13):
        font = pygame.font.Font('freesansbold.ttf', text_size)
        fontText = font.render(text, True, text_color, background_color)
        textRect = fontText.get_rect()
        textRect.center = (x, y)
        self.screen.blit(fontText, textRect)

    def draw_box(self, bboxes, box_text='', box_color=green, text_color=blue):
        box_color_list = list(box_color)
        for box in bboxes:
            x, y, w, h = int(box[0]), int(box[1]), int(box[2]), int(box[3])
            if box_text != '':
                self.draw_text(box_text, x + (screen_width / 2 - fov_width / 2),
                               y - 10 + (screen_height / 2 - fov_height / 2),
                               background_color=box_color, text_color=text_color)
            pygame.draw.rect(self.screen, box_color_list,
                             [x + (screen_width / 2 - fov_width / 2), y + (screen_height / 2 - fov_height / 2), w, h],
                             1)

    def draw_fov(self):
        pygame.draw.rect(self.screen, [0, 255, 0],
                         [screen_width / 2 - fov_width / 2, screen_height / 2 - fov_height / 2, fov_width, fov_height],
                         1)


if __name__ == '__main__':
    service = ScreenService()
    for i in range(1000):
        service.draw_text("TEST" + str(i), 150, 25, background_color=fuchsia, text_color=green, text_size=32)
        service.draw_box([[(300 + 10 * i) % screen_width, (400 + 10 * i) % screen_height, 100, 50]])
        service.set_crosshair((10 * i) % screen_width, (40 * i) % screen_height)
        pygame.display.update()
