from mss import tools

from bot.object_detector import ObjectDetector
from bot.screen_service import ScreenService


class GameMaster:
    def __init__(self):
        self.object_detector = ObjectDetector()
        self.screen_service = ScreenService()

    def test_integration(self):
        frame = self.screen_service.grab_frame()
        output = 'test.png'
        tools.to_png(frame.rgb, frame.size, output=output)
        print(output)
        # print(frame)
        print(self.object_detector.detect('test.png'))


if __name__ == '__main__':
    master = GameMaster()
    master.test_integration()
