import ctypes
from ctypes import windll

import pyautogui
import pygame
import pynput
import win32api
import win32con
import win32gui
from mss import mss, tools

from constants import fuchsia, WINDOW, screen_width, screen_height, green, blue, fov_width, \
    fov_height, CT, T_HEAD, T, CT_HEAD, screen_width_4k, screen_height_4k


class RECT(ctypes.Structure):
    _fields_ = [
        ('left', ctypes.c_long),
        ('top', ctypes.c_long),
        ('right', ctypes.c_long),
        ('bottom', ctypes.c_long),
    ]

    def width(self):  return self.right - self.left

    def height(self): return self.bottom - self.top


class ScreenService:
    def __init__(self):
        fpsClock = pygame.time.Clock()
        pygame.init()

        # self.screen = pygame.display.set_mode((screen_width, screen_height))
        self.screen = pygame.display.set_mode((0, 0), pygame.NOFRAME)  # (0, 0) sets the size o the size
        # of the screen
        # # self.screen = pygame.display.set_mode((1920, 1080), pygame.HWSURFACE)  # For borderless, use pygame.NOFRAME

        hwnd = pygame.display.get_wm_info()[WINDOW]
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE,
                               win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) | win32con.WS_EX_LAYERED)
        win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(*fuchsia), 0, win32con.LWA_COLORKEY)

        self.SetWindowPos = windll.user32.SetWindowPos
        self.screen.fill(fuchsia)
        self.always_on_top(True)

        self.SendInput = ctypes.windll.user32.SendInput

        pyautogui.PAUSE = 0

        self.classesNames = [CT, CT_HEAD, T, T_HEAD]

        self.monitor = {"top": 0, "left": 0, "width": screen_width_4k, "height": screen_height_4k}
        # x = 0
        # y = 0
        # os.environ['SDL_VIDEO_WINDOW_POS'] = "%d,%d" % (x, y)

    @staticmethod
    def onTop(window):
        SetWindowPos = windll.user32.SetWindowPos
        GetWindowRect = windll.user32.GetWindowRect
        rc = RECT()
        GetWindowRect(window, ctypes.byref(rc))
        SetWindowPos(window, -1, rc.left, rc.top, 0, 0, 0x0001)

    def always_on_top(self, yesOrNo):
        # win32gui.SetWindowPos(pygame.display.get_wm_info()['window'], win32con.HWND_TOPMOST, 0, 0, 0, 0,
        #                       win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
        # z_order = (NOT_TOPMOST, TOPMOST)[yesOrNo]  # choose a flag according to bool
        # hwnd = pygame.display.get_wm_info()[WINDOW]  # handle to the window
        # self.SetWindowPos(hwnd, z_order, 0, 0, 0, 0, NO_MOVE | NO_SIZE)
        self.onTop(pygame.display.get_wm_info()['window'])

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

    def grab_frame(self):
        with mss() as sct:
            screenshot = sct.grab(self.monitor)
        return screenshot

    def test_screen_manipulation(self):
        for i in range(200):
            self.draw_text("TEST" + str(i), 150, 25, background_color=fuchsia, text_color=green, text_size=32)
            self.draw_box([[(300 + 10 * i) % screen_width, (400 + 10 * i) % screen_height, 100, 50]])
            # self.set_crosshair((10 * i) % screen_width, (40 * i) % screen_height)
            pygame.display.update()

    # def test_screen_capture(self):
    #     # Create an mss screenshot object
    #     with mss() as sct:
    #         # Capture a screenshot of the entire screen
    #         screenshot = sct.grab(self.monitor)
    #
    #         # Convert the screenshot to a Pygame surface
    #         pygame_screenshot = pygame.image.frombuffer(screenshot.rgb, screenshot.size, "RGB")
    #
    #         # Blit the Pygame surface onto the screen
    #         self.screen.blit(pygame_screenshot, (0, 0))
    #
    #     # Update the display
    #     pygame.display.update()
    #
    #     # Wait for the user to close the window
    #     while True:
    #         for event in pygame.event.get():
    #             if event.type == pygame.QUIT:
    #                 pygame.quit()
    #                 quit()

    def test_screen_capture(self):
        # Main while loop for the program
        done = 0
        count = 0
        while not done:
            # Accessing the event if any occurred
            for event in pygame.event.get():
                # Checking if quit button is pressed or not
                if event.type == pygame.QUIT:
                    #  If quit then store true
                    done = 1
                    # Checking if the escape button is pressed or not
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        with mss() as sct:
                            # Capture a screenshot of the entire screen
                            screenshot = sct.grab(self.monitor)
                            output = f'sct-{count}.png'
                            tools.to_png(screenshot.rgb, screenshot.size, output=output)
                            print(output)
                            count += 1
                    # If the escape button  is pressed then store true in the variable
                    if event.key == pygame.K_ESCAPE:
                        done = 1
            # Transparent background
            self.screen.fill(fuchsia)
            #  Calling the show_text function
            #  Checking for the update in the display
            pygame.display.update()

if __name__ == '__main__':
    service = ScreenService()
    # service.test_screen_manipulation()
    service.test_screen_capture()
#
# # Initialize Pygame
# pygame.init()
#
# # Set the screen size
# screen_size = (800, 600)
#
# # Create the Pygame screen
# screen = pygame.display.set_mode(screen_size)
#
# # Create an mss screenshot object
# with mss() as sct:
#     # Capture a screenshot of the entire screen
#     monitor = {"top": 0, "left": 0, "width": screen_size[0], "height": screen_size[1]}
#     screenshot = sct.grab(monitor)
#
#     # Convert the screenshot to a Pygame surface
#     pygame_screenshot = pygame.image.frombuffer(screenshot.rgb, screenshot.size, "RGB")
#
#     # Blit the Pygame surface onto the screen
#     screen.blit(pygame_screenshot, (0, 0))
#
# # Update the display
# pygame.display.update()
#
# # Wait for the user to close the window
# while True:
#     for event in pygame.event.get():
#         if event.type == pygame.QUIT:
#             pygame.quit()
#             quit()
