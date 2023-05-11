import ctypes
import time
from ctypes import windll

import pyautogui
import pygame
import pynput
import win32api
import win32con
import win32gui
from mss import mss, tools

from constants import fuchsia, WINDOW, green, blue, \
    NOT_TOPMOST, NO_MOVE, NO_SIZE, TOPMOST, red, screen_width_4k, screen_height_4k, \
    cyan, white, CT, T


class RECT(ctypes.Structure):
    _fields_ = [
        ('left', ctypes.c_long),
        ('top', ctypes.c_long),
        ('right', ctypes.c_long),
        ('bottom', ctypes.c_long),
    ]

    def width(self): return self.right - self.left

    def height(self): return self.bottom - self.top


class ScreenManipulator:
    def __init__(self):
        self.fpsClock = pygame.time.Clock()
        # fpsClock.tick(30)
        # Initialize PyGame window
        pygame.init()
        print("Initializing PyGame window...")
        self.screen_width = screen_width_4k
        self.screen_height = screen_height_4k
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        # self.screen = pygame.display.set_mode((0, 0), pygame.NOFRAME) # (0, 0) sets the size to the size of the screen
        # # self.screen = pygame.display.set_mode((1920, 1080), pygame.HWSURFACE)  # For borderless, use pygame.NOFRAME

        # Set the default back-ground color which is fuchsia to be interpreted as transparent
        hwnd = pygame.display.get_wm_info()[WINDOW]
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE,
                               win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) | win32con.WS_EX_LAYERED)
        win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(*fuchsia), 0, win32con.LWA_COLORKEY)
        self.SetWindowPos = windll.user32.SetWindowPos
        self.screen.fill(fuchsia)
        pygame.display.update()
        # Position the window to always be on top of the screen
        self.always_on_top(True)

        self.SendInput = ctypes.windll.user32.SendInput

        pyautogui.PAUSE = 0

        # Define the area on the screen to capture
        self.monitor = {"top": 0, "left": 0, "width": self.screen_width, "height": self.screen_height}
        # x = 0
        # y = 0
        # os.environ['SDL_VIDEO_WINDOW_POS'] = "%d,%d" % (x, y)

    @staticmethod
    def unpack_box(box):
        # Format of unpacking: x_top, y_left, width, height, confidence of prediction, _class predicted
        x, y, w, h, c, _class = int(box[0]), int(box[1]), int(box[2] - box[0]), int(box[3] - box[1]), box[4], box[5]
        return x, y, w, h, c, _class

    def always_on_top(self, yesOrNo):
        win32gui.SetWindowPos(pygame.display.get_wm_info()['window'], win32con.HWND_TOPMOST, 0, 0, 0, 0,
                              win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
        z_order = (NOT_TOPMOST, TOPMOST)[yesOrNo]  # choose a flag according to bool
        hwnd = pygame.display.get_wm_info()[WINDOW]  # handle to the window
        self.SetWindowPos(hwnd, z_order, 0, 0, 0, 0, NO_MOVE | NO_SIZE)

    def get_crosshair(self):
        cur_x, cur_y = pyautogui.position()
        return cur_x, cur_y

    def set_crosshair(self, x, y):
        x = 1 + int(x * 65536. / self.screen_width)
        y = 1 + int(y * 65536. / self.screen_height)
        extra = ctypes.c_ulong(0)
        ii_ = pynput._util.win32.INPUT_union()
        ii_.mi = pynput._util.win32.MOUSEINPUT(x, y, 0, (0x0001 | 0x8000), 0,
                                               ctypes.cast(ctypes.pointer(extra), ctypes.c_void_p))
        # create mouse movement event
        command = pynput._util.win32.INPUT(ctypes.c_ulong(0), ii_)
        self.SendInput(1, ctypes.pointer(command), ctypes.sizeof(command))

    def click_left_button(self):
        # create left mouse button down event
        extra = ctypes.c_ulong(0)
        ii_ = pynput._util.win32.INPUT_union()
        ii_.mi = pynput._util.win32.MOUSEINPUT(0, 0, 0, (0x0002 | 0x8000), 0,
                                               ctypes.cast(ctypes.pointer(extra), ctypes.c_void_p))
        command_down = pynput._util.win32.INPUT(ctypes.c_ulong(0), ii_)

        # create left mouse button up event
        extra = ctypes.c_ulong(0)
        ii_ = pynput._util.win32.INPUT_union()
        ii_.mi = pynput._util.win32.MOUSEINPUT(0, 0, 0, (0x0004 | 0x8000), 0,
                                               ctypes.cast(ctypes.pointer(extra), ctypes.c_void_p))
        command_up = pynput._util.win32.INPUT(ctypes.c_ulong(0), ii_)

        # send events to input queue
        self.SendInput(1, ctypes.pointer(command_down), ctypes.sizeof(command_down))
        time.sleep(0.5)
        self.SendInput(1, ctypes.pointer(command_up), ctypes.sizeof(command_up))
        # pyautogui.click()
        for event in pygame.event.get():
            print(event)
        print('SHOT FIRED')

    def set_crosshair_and_shoot(self, x, y):
        self.set_crosshair(x, y)
        self.click_left_button()

    def draw_text(self, text, x, y, background_color=green, text_color=blue, text_size=13):
        font = pygame.font.Font('freesansbold.ttf', text_size)
        fontText = font.render(text, True, text_color, background_color)
        textRect = fontText.get_rect()
        textRect.center = (x, y)
        self.screen.blit(fontText, textRect)

    def draw_boxes(self, bboxes, box_text='', box_color=green, text_color=white, draw_aiming_point=True, text_size=13):
        for box in bboxes:
            # bbox x_left, y_top, x_right, y_bottom
            x, y, w, h, c, _class = self.unpack_box(box)
            if box_text != '':
                self.draw_text(box_text, x, y - text_size // 2, background_color=box_color,
                               text_color=text_color, text_size=text_size)

            box_color_list = list(box_color)
            pygame.draw.rect(self.screen, box_color_list, [x, y, w, h], 1)
            if draw_aiming_point:
                if _class in [CT, T]:
                    pygame.draw.circle(self.screen, color=red, center=(x + w // 2, y + h // 4), radius=3)
                pygame.draw.circle(self.screen, color=red, center=(x + w // 2, y + h // 2), radius=3)
            pygame.display.update()

    def draw_line_to_box(self, box, color=cyan, width=5):
        x, y, w, h, c, _class = self.unpack_box(box)
        start = self.get_crosshair()
        end = x + w // 2, y + h // 2
        pygame.draw.line(self.screen, start_pos=start, end_pos=end, color=color, width=width)
        pygame.display.update()

    def clear_screen(self):
        self.screen.fill(fuchsia)
        pygame.display.update()

    def grab_frame(self):
        with mss() as sct:
            screenshot = sct.grab(self.monitor)
        return screenshot

    def test_screen_manipulation(self):
        pygame.display.update()
        self.draw_boxes([[929, 565, 962, 597, 81, 1], [907, 562, 1000, 735, 80, 0]])

        for i in range(200):
            self.draw_text("TEST" + str(i), 150, 25, background_color=fuchsia, text_color=green, text_size=32)
            self.draw_boxes([[(300 + 10 * i) % self.screen_width, (400 + 10 * i) % self.screen_height, 100, 50]])
            self.set_crosshair((10 * i) % self.screen_width, (40 * i) % self.screen_height)
            pygame.display.update()

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

    def test_draw_line(self):
        self.draw_boxes([[929, 565, 962, 597, 81, 1], [907, 562, 1000, 735, 80, 0]], "CT")
        self.draw_line_to_box([929, 565, 962, 597, 81, 1])
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    quit()

    def test_draw_bboxes(self):
        self.draw_boxes([[929, 565, 962, 597, 81, 1], [907, 562, 1000, 735, 80, 0]], "CT")
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    quit()

    def test_mouse_movement(self):
        self.set_crosshair(750, 100)
        cur_x, cur_y = self.get_crosshair()
        assert cur_x == 750 and cur_y == 100
        pygame.quit()
        quit()

    def test_mouse_recording(self):
        clicks = []

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    quit()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    print('click')
                    clicks.append(event.pos)

            self.screen.fill((255, 255, 255))
            # Does not work with fuchsia background because it does not register clicks on transparent background...
            # self.screen.fill(fuchsia)

            # Draw all recorded clicks as circles on the screen
            for click in clicks:
                pygame.draw.circle(self.screen, (255, 0, 0), click, 5)

            pygame.display.update()
            self.fpsClock.tick(60)
        # while True:
        #     for event in pygame.event.get():
        #         if event.type == pygame.QUIT:
        #             pygame.quit()
        #             quit()
        #         elif event.type == pygame.MOUSEBUTTONDOWN:
        #            print('click')
        # self.fpsClock.tick(60)
        # from pynput.mouse import Listener
        #
        # def on_click(x, y, button, pressed):
        #     if pressed:
        #         print(f"Clicked at ({x}, {y}) with {button}")
        #
        # with Listener(on_click=on_click) as listener:
        #     listener.join()
        #     self.fpsClock.tick(10)

    def test_mouse_click(self):
        time.sleep(2)
        for i in range(10):
            print(i)
            for event in pygame.event.get():
                print(event)
            time.sleep(0.5)
            x, y = self.get_crosshair()
            pyautogui.click()
            self.clear_screen()
            self.fpsClock.tick(10)
        pygame.quit()
        quit()

    def click(self, x, y):
        win32api.SetCursorPos((x, y))
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)

    def test_mouse_movement_and_shoot(self):
        time.sleep(5)
        for i in range(10):
            print(i)
            for event in pygame.event.get():
                print(event)
            x, y = self.get_crosshair()
            self.set_crosshair_and_shoot(x + 100, y)
            time.sleep(1)
            self.fpsClock.tick(10)

        pygame.quit()
        quit()


if __name__ == '__main__':
    service = ScreenManipulator()
    # service.test_draw_bboxes()
    # service.test_draw_line()
    # service.test_screen_manipulation()
    # service.test_screen_capture()
    # service.test_mouse_movement()
    service.test_mouse_movement_and_shoot()
    # service.test_mouse_click()
    # service.test_mouse_recording()
