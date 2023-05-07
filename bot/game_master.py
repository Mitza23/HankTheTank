import time

import cv2
import numpy as np
import pygame
from mss import tools

from bot.object_detector import ObjectDetector
from bot.screen_service import ScreenService


class GameMaster:
    def __init__(self):
        self.object_detector = ObjectDetector()
        self.screen_service = ScreenService()
        self.clicks = 0

    @staticmethod
    def mss_to_cv2(screen):
        # Extract the BGRA color array from the mss Screenshot
        img = np.array(screen)
        # Convert BGRA to BGR format used by OpenCV
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        return img

    @staticmethod
    def box_is_valid(box):
        if box is None or len(box) != 6:
            return False
        return box[4] > 50

    def detect_in_frame(self, draw_bboxes=False, shoot=True):
        frame = self.screen_service.grab_frame()
        frame = self.mss_to_cv2(frame)
        bboxes = self.object_detector.detect_in_frame(frame)
        # print(bboxes)
        if draw_bboxes:
            self.screen_service.draw_box(bboxes)

        chosen_box = None
        # TODO add box choosing strategy
        if len(bboxes):
            bboxes.sort(key=lambda b: b[4])
            chosen_box = bboxes[0]

        print(chosen_box)

        if self.box_is_valid(chosen_box):
            self.screen_service.set_crosshair_on_box(chosen_box, shoot=shoot)

    def detect_continuous(self, draw_bboxes=False, shoot=True):
        while True:
            self.detect_in_frame(draw_bboxes=draw_bboxes, shoot=shoot)
            time.sleep(0.3)
            self.screen_service.clear_screen()
            for event in pygame.event.get():
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.clicks += 1
                if event.type == pygame.QUIT:
                    print(f"Clicks made: {self.clicks}")
                    pygame.quit()
                    quit()

    def test_detection_speed_frame(self):
        frame = self.screen_service.grab_frame()
        frame = self.mss_to_cv2(frame)
        start = time.time()
        self.object_detector.detect_in_frame(frame)
        end = time.time()
        print(end - start)

    def test_integration_from_source(self):
        start = time.time()
        frame = self.screen_service.grab_frame()
        frame = self.mss_to_cv2(frame)
        output = 'test.png'
        frame = tools.to_png(frame.rgb, frame.size, output=output)
        bboxes = self.object_detector.detect_from_source(output)
        print(bboxes)

        self.screen_service.draw_box(bboxes)
        self.screen_service.set_crosshair(bboxes[0][0], bboxes[0][1])
        end = time.time()
        print(end - start)
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    quit()

    def test_integration_from_frame(self):
        start = time.time()
        self.detect_in_frame()
        end = time.time()
        print(end - start)
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    quit()

    def test_detect_continuous(self):
        self.detect_continuous(draw_bboxes=True, shoot=True)

    def demo(self):
        while True:
            self.detect_in_frame(draw_bboxes=True, shoot=True)
            time.sleep(0.5)
            self.screen_service.clear_screen()
            for event in pygame.event.get():
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.clicks += 1
                if event.type == pygame.QUIT:
                    print(f"Clicks made: {self.clicks}")
                    pygame.quit()
                    quit()


if __name__ == '__main__':
    master = GameMaster()
    # master.test_detect_continuous()
    master.test_detection_speed_frame()

# import mss
# import cv2
#
#
# # The model takes as input images in BGR encoding as outputted by cv2.imread(), while the screen captures from
# # mss().grab() are done in BGRA encoding
# def mss_to_cv2(screen):
#     # Extract the BGRA color array from the mss Screenshot
#     img = np.array(screen)
#     # Convert BGRA to BGR format used by OpenCV
#     img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
#     return img
#
#
# with mss.mss() as sct:
#     # Capture a screenshot
#     screenshot = sct.grab(sct.monitors[0])
#
#     # Convert the screenshot to a NumPy array in BGR format
#     img = mss_to_cv2(screenshot)
#
#     # Display the image using OpenCV
#     cv2.imshow("Screenshot", img)
#     cv2.waitKey(0)
#     cv2.destroyAllWindows()
