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

    @staticmethod
    def mss_to_cv2(screen):
        # Extract the BGRA color array from the mss Screenshot
        img = np.array(screen)
        # Convert BGRA to BGR format used by OpenCV
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        return img

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
        frame = self.screen_service.grab_frame()
        frame = self.mss_to_cv2(frame)
        bboxes = self.object_detector.detect_in_frame(frame)
        print(bboxes)

        self.screen_service.draw_box(bboxes)
        if len(bboxes):
            self.screen_service.set_crosshair(bboxes[0][0], bboxes[0][1])
        end = time.time()
        print(end - start)
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    quit()


if __name__ == '__main__':
    master = GameMaster()
    master.test_integration_from_frame()

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
