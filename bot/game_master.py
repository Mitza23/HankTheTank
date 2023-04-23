import time

import pygame
from mss import tools

from bot.constants import fuchsia
from bot.object_detector import ObjectDetector
from bot.screen_service import ScreenService


class GameMaster:
    def __init__(self):
        self.object_detector = ObjectDetector()
        self.screen_service = ScreenService()

    def test_integration(self):
        self.screen_service.screen.fill(fuchsia)
        pygame.display.update()
        start = time.time()
        frame = self.screen_service.grab_frame()
        output = 'test.png'
        frame = tools.to_png(frame.rgb, frame.size, output=output)
        bboxes = self.object_detector.detect_from_source(output)
        print(bboxes)

        self.screen_service.draw_box(bboxes)
        self.screen_service.set_crosshair(bboxes[0][0], bboxes[0][1])
        end = time.time()
        print(end - start)
        time.sleep(5)
        pygame.quit()
        quit()


if __name__ == '__main__':
    master = GameMaster()
    master.test_integration()
