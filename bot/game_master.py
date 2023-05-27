import time
from tkinter import *

import cv2
import keyboard
import matplotlib.pyplot as plt
import numpy as np
import pygame
from mss import tools

from bot.constants import red, CT, T, CT_HEAD, T_HEAD, ALL
from bot.object_detector import ObjectDetector
from bot.screen_manipulator import ScreenManipulator


class GameMaster:
    def __init__(self):
        self.object_detector = ObjectDetector()
        self.screen_manipulator = ScreenManipulator()
        self.clicks = 0
        self.engaged = False
        self.opponent_team = T
        self.detection_times = []
        self.strategize_times = []
        self.aiming_times = []

    @staticmethod
    # Convert the ScreenShot from ScreenManipulator to a data type accepted by the model
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
        return True

    # @staticmethod
    # def unpack_box(box):
    #     # Format of unpacking: x_top, y_left, width, height, confidence of prediction, _class predicted
    #     x, y, w, h, c, _class = int(box[0]), int(box[1]), int(box[2] - box[0]), int(box[3] - box[1]), box[4], box[5]
    #     return x, y, w, h, c, _class

    def set_crosshair_on_box(self, box, shoot):
        # Bounding box format: x_left, y_top, x_right, y_bottom, probability, class
        x, y, w, h, c, _class = self.screen_manipulator.unpack_box(box)
        x_center, y_center = int(box[2] + box[0]) / 2, int(box[3] + box[1]) / 2
        crosshair_x, crosshair_y = x_center, y_center
        print("Box class: ", _class)
        if _class in [CT, T]:
            # Case for enemy bodies, aiming will be above the center of the box to avoid shooting between the legs
            print("Body shot")
            crosshair_y -= h / 4
        if shoot:
            self.screen_manipulator.set_crosshair_and_shoot(crosshair_x, crosshair_y)
        else:
            self.screen_manipulator.set_crosshair(crosshair_x, crosshair_y)

    def get_box_class(self, box):
        x, y, w, h, c, _class = self.screen_manipulator.unpack_box(box)
        return _class

    def get_box_certainty(self, box):
        x, y, w, h, c, _class = self.screen_manipulator.unpack_box(box)
        return c

    def get_box_aiming_point(self, box):
        x, y, w, h, c, _class = self.screen_manipulator.unpack_box(box)
        x_center, y_center = int(box[2] + box[0]) / 2, int(box[3] + box[1]) / 2
        crosshair_x, crosshair_y = x_center, y_center
        if _class in [CT, T]:
            # Case for enemy bodies, aiming will be above the center of the box to avoid shooting between the legs
            crosshair_y -= h / 6
        return crosshair_x, crosshair_y

    def get_box_area(self, box):
        x, y, w, h, c, _class = self.screen_manipulator.unpack_box(box)
        return w * h

    def get_distance_to_box(self, box):
        # start_x, start_y = self.screen_manipulator.get_crosshair()
        start_x, start_y = self.screen_manipulator.screen_width // 2, self.screen_manipulator.screen_height // 2
        dest_x, dest_y = self.get_box_aiming_point(box)
        # No need to compute the square root, adds unnecessary complexity
        # return int(math.sqrt((start_x - dest_x) ** 2 + (start_y - dest_y) ** 2))
        return (start_x - dest_x) ** 2 + (start_y - dest_y) ** 2

    # Remove bounding boxes of the characters from the player's team
    def remove_allies(self, bboxes, opponent_team):
        if opponent_team == T:
            allies = [CT, CT_HEAD]
        elif opponent_team == CT:
            allies = [T, T_HEAD]
        else:
            allies = []

        bboxes = list(filter(lambda box: self.get_box_class(box) not in allies, bboxes))
        return bboxes

    # Filter predictions by removing those below a certain threshold of certainty
    def remove_uncertain_predictions(self, bboxes, certainty_threshold=50):
        bboxes = list(filter(lambda box: self.get_box_certainty(box) > certainty_threshold, bboxes))
        bboxes.sort(key=lambda box: self.get_box_certainty(box))
        return bboxes

    # Keeps only the boxes for the heads
    def headshots_only(self, bboxes):
        bboxes = list(filter(lambda box: self.get_box_class(box) in [T_HEAD, CT_HEAD], bboxes))
        return bboxes

    # Orders the boxes according to their distance to the crosshair
    def closest_box(self, bboxes):
        bboxes.sort(key=lambda box: self.get_distance_to_box(box))
        return bboxes

    # Orders the boxes according to their distance to the player
    def proximal_box(self, bboxes):
        bboxes.sort(key=lambda box: self.get_box_area(box), reverse=True)
        return bboxes

    # Strategy for prioritizing headshots and has as fallback the closest player box in case
    def headshot_only_strategy(self, bboxes, opponent_team):
        bboxes = self.remove_allies(bboxes, opponent_team)
        bboxes = self.remove_uncertain_predictions(bboxes, certainty_threshold=50)
        bboxes = self.headshots_only(bboxes)
        bboxes = self.closest_box(bboxes)
        if len(bboxes) > 0:
            return bboxes[0]
        else:
            return None

    # Strategy for prioritizing headshots and has as fallback the closest player box in case
    def headshot_priority_strategy(self, bboxes, opponent_team):
        bboxes = self.remove_allies(bboxes, opponent_team)
        bboxes = self.remove_uncertain_predictions(bboxes, certainty_threshold=50)
        bboxes = self.proximal_box(bboxes)
        fallback_box = None
        if len(bboxes):
            fallback_box = bboxes[0]
        bboxes = self.headshots_only(bboxes)
        bboxes = self.closest_box(bboxes)
        if len(bboxes) > 0:
            return bboxes[0]
        else:
            return fallback_box

    # Strategy for prioritizing the enemy closest to the player
    def proximal_strategy(self, bboxes, opponent_team):
        bboxes = self.remove_allies(bboxes, opponent_team)
        bboxes = self.remove_uncertain_predictions(bboxes, certainty_threshold=50)
        bboxes = self.proximal_box(bboxes)
        if len(bboxes) > 0:
            return bboxes[0]
        else:
            return None

    # Strategy for prioritizing the enemy closest to the crosshair
    def fastest_kill_strategy(self, bboxes, opponent_team):
        bboxes = self.remove_allies(bboxes, opponent_team)
        bboxes = self.remove_uncertain_predictions(bboxes, certainty_threshold=50)
        bboxes = self.closest_box(bboxes)
        if len(bboxes) > 0:
            return bboxes[0]
        else:
            return None

    # The method that will be called by the main loop to decide which box to aim at. In case the player is already
    # engaged in a battle, the strategy will be to prioritize the enemy closest to the crosshair
    def strategize(self, bboxes, opponent_team, aiming_strategy):
        if self.engaged:
            chosen_box = self.fastest_kill_strategy(bboxes, opponent_team)
        else:
            chosen_box = aiming_strategy(bboxes, opponent_team)
        return chosen_box
        # return aiming_strategy(bboxes, opponent_team)

    def grab_frame(self):
        frame = self.screen_manipulator.grab_frame()
        frame = self.mss_to_cv2(frame)
        return frame

    def draw_boxes(self, bboxes, chosen_box):
        self.screen_manipulator.draw_boxes(bboxes)
        self.screen_manipulator.draw_boxes([chosen_box], box_color=red)
        self.screen_manipulator.draw_line_to_box(chosen_box)

    def detect_in_frame(self, opponent_team, aiming_strategy, draw_bboxes, shoot, demo_time=1):
        _start = time.time()

        start = time.time()
        frame = self.grab_frame()
        bboxes = self.object_detector.detect_in_frame(frame)
        end = time.time()
        print(f'detection: {end - start}')

        # print(bboxes)
        start = time.time()
        chosen_box = self.strategize(bboxes, opponent_team, aiming_strategy)
        end = time.time()
        print(f'strategize: {end - start}')

        if self.box_is_valid(chosen_box):
            if draw_bboxes:
                start = time.time()
                self.draw_boxes(bboxes, chosen_box)
                end = time.time()
                print(f'draw: {end - start}')
                time.sleep(demo_time)
            start = time.time()
            self.set_crosshair_on_box(chosen_box, shoot=shoot)
            end = time.time()
            print(f'aiming: {end - start}')
            self.engaged = True
        else:
            self.engaged = False
        end = time.time()
        print(f'total: {end - _start}')

    def detect_continuous(self, opponent_team, aiming_strategy, draw_bboxes, shoot, delay=0.01):
        while True:
            self.detect_in_frame(opponent_team=opponent_team, aiming_strategy=aiming_strategy, draw_bboxes=draw_bboxes,
                                 shoot=shoot)
            if self.engaged:
                # Used to wait for the character to recover from recoil
                time.sleep(delay)
            if draw_bboxes:
                self.screen_manipulator.clear_screen()

            if keyboard.is_pressed('k'):
                print(f"Clicks made: {self.clicks}")
                pygame.quit()
                quit()
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_k:
                        pygame.quit()
                        quit()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.clicks += 1
                if event.type == pygame.QUIT:
                    print(f"Clicks made: {self.clicks}")
                    pygame.quit()
                    quit()
            # self.screen_manipulator.fpsClock.tick(60)

    def test_detection_speed_frame(self):
        for _ in range(5):
            frame = self.screen_manipulator.grab_frame()
            frame = self.mss_to_cv2(frame)
            start = time.time()
            self.object_detector.detect_in_frame(frame)
            end = time.time()
            print(end - start)

    def test_integration_from_source(self):
        start = time.time()
        frame = self.screen_manipulator.grab_frame()
        frame = self.mss_to_cv2(frame)
        output = 'test.png'
        frame = tools.to_png(frame.rgb, frame.size, output=output)
        bboxes = self.object_detector.detect_from_source(output)
        print(bboxes)

        self.screen_manipulator.draw_boxes(bboxes)
        self.screen_manipulator.set_crosshair(bboxes[0][0], bboxes[0][1])
        end = time.time()
        print(end - start)
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    quit()

    def test_integration_from_frame(self):
        start = time.time()
        self.detect_in_frame(opponent_team=ALL, aiming_strategy=self.fastest_kill_strategy, draw_bboxes=False,
                             shoot=True)
        end = time.time()
        print(end - start)
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    quit()

    def test_strategize(self):
        bboxes = [[2258, 645, 2402, 906, 84, 0], [2300, 652, 2356, 700, 81, 1]]
        opponent_team = ALL
        self.engaged = False
        self.strategize(bboxes, opponent_team, self.fastest_kill_strategy)

    def test_continuous(self):
        self.detect_continuous(ALL, self.fastest_kill_strategy, draw_bboxes=False, shoot=True)

    def demo(self):
        self.detect_continuous(ALL, self.headshot_priority_strategy, draw_bboxes=True, shoot=True)

    def test_shooting(self):
        self.screen_manipulator.test_mouse_movement_and_shoot()

    def play(self, shooting_strategy):
        while True:
            frame = self.grab_frame()
            start = time.time()
            bboxes = self.object_detector.detect_in_frame(frame)
            end = time.time()
            self.detection_times.append(end - start)
            start = time.time()
            # chosen_box = self.headshot_only_strategy(bboxes, 'ALL')
            chosen_box = self.strategize(bboxes, 'ALL', shooting_strategy)
            end = time.time()
            self.strategize_times.append(end - start)
            if self.box_is_valid(chosen_box):
                start = time.time()
                self.set_crosshair_on_box(chosen_box, shoot=True)
                end = time.time()
                self.aiming_times.append(end - start)
                self.engaged = True
            else:
                self.engaged = False

    def test_key_triggers(self):
        while True:
            if keyboard.is_pressed('k'):
                print('You Pressed k!')
            for event in pygame.event.get():
                print(event)
            self.screen_manipulator.fpsClock.tick(10)
            # break

    def start_bot_on_command(self):
        while True:
            if keyboard.is_pressed('k'):
                break
            for event in pygame.event.get():
                print(event)
            self.screen_manipulator.fpsClock.tick(10)
        self.play(self.headshot_only_strategy)

    def plot_detection_times(self):
        plt.rcParams['figure.figsize'] = [35, 20]
        plt.yticks(np.arange(0, max(self.detection_times) + 0.1, 0.05))
        plt.plot(self.detection_times, color='magenta')  # plot the data
        plt.xticks(range(0, len(self.detection_times) + 1, 1))  # set the tick frequency on x-axis

        plt.ylabel('detection times in seconds')  # set the label for y axis
        plt.xlabel('index')  # set the label for x-axis
        plt.title("Detection times over a playing round")  # set the title of the graph
        plt.savefig('plot_detection.png', bbox_inches='tight')
        # plt.show()  # display the graph
        plt.cla()
        plt.clf()

    def plot_strategize_times(self):
        plt.rcParams['figure.figsize'] = [35, 20]
        plt.yticks(np.arange(0, max(self.strategize_times) + 0.1, 0.001))
        plt.plot(self.strategize_times, color='blue')  # plot the data
        plt.xticks(range(0, len(self.strategize_times) + 1, 1))  # set the tick frequency on x-axis

        plt.ylabel('strategizing times in seconds')  # set the label for y axis
        plt.xlabel('index')  # set the label for x-axis
        plt.title("Strategizing times times over a playing round")  # set the title of the graph
        plt.savefig('plot_strategize.png', bbox_inches='tight')
        # plt.show()  # display the graph
        plt.cla()
        plt.clf()

    def plot_aiming_times(self):
        plt.rcParams['figure.figsize'] = [35, 20]
        plt.yticks(np.arange(0, max(self.aiming_times) + 0.1, 0.001))
        plt.plot(self.aiming_times, color='red')  # plot the data
        plt.xticks(range(0, len(self.aiming_times) + 1, 1))  # set the tick frequency on x-axis

        plt.ylabel('aiming times in seconds')  # set the label for y axis
        plt.xlabel('index')  # set the label for x-axis
        plt.title("Aiming times over a playing round")  # set the title of the graph
        plt.savefig('plot_aiming.png', bbox_inches='tight')
        # plt.show()  # display the graph
        plt.cla()
        plt.clf()


if __name__ == '__main__':
    master = GameMaster()
    # master.test_detection_speed_frame()
    try:
        # master.demo()
        # master.test_shooting()
        # master.test_continuous()
        # master.test_strategize()
        # master.play()
        master.start_bot_on_command()
    except KeyboardInterrupt:
        print("Plotting...")
        master.plot_detection_times()
        master.plot_strategize_times()
        master.plot_aiming_times()
        print(f"Clicks made: {master.clicks}")
        pygame.quit()
        quit()
