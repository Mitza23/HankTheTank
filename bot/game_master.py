import time

import cv2
import keyboard
import matplotlib.pyplot as plt
import numpy as np
import pygame
from mss import tools

from bot.constants import red, CT, T, CT_HEAD, T_HEAD, ALL, green
from bot.object_detector import ObjectDetector
from bot.screen_manipulator import ScreenManipulator


# from tkinter import *


class GameMaster:
    def __init__(self):
        self.object_detector = ObjectDetector()
        self.screen_manipulator = ScreenManipulator()
        self.clicks = 0
        self.engaged = False
        self.opponent_team = ALL
        self.aiming_strategy = self.fastest_kill_strategy
        self.draw = False
        self.spray_time = 0.5
        self.display_counter = 0
        self.detection_times = []
        self.strategize_times = []
        self.aiming_times = []
        self.total_times = []

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

    def set_crosshair_on_box(self, box, shoot, spray_time=0.5):
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
            self.screen_manipulator.set_crosshair_and_shoot(crosshair_x, crosshair_y, spray_time)
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
        start_x, start_y = self.screen_manipulator.get_crosshair()
        # start_x, start_y = self.screen_manipulator.screen_width // 2, self.screen_manipulator.screen_height // 2
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

    # Strategy for only targeting headshots
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
        for box in bboxes:
            self.screen_manipulator.draw_line_to_box(box, color=green)
        self.screen_manipulator.draw_line_to_box(chosen_box, color=red)

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

    def demo(self):
        while True:
            frame = self.grab_frame()
            bboxes = self.object_detector.detect_in_frame(frame)
            chosen_box = self.strategize(bboxes, ALL, self.fastest_kill_strategy)
            if self.box_is_valid(chosen_box):
                self.screen_manipulator.clear_screen()
                self.draw_boxes(bboxes, chosen_box)
                print("Boxes drawn")
                # time.sleep(3)
                # self.set_crosshair_on_box(chosen_box, shoot=False, spray_time=0)
                self.engaged = True
            else:
                self.engaged = False
            for event in pygame.event.get():
                print(event)

    def test_shooting(self):
        self.screen_manipulator.test_mouse_movement_and_shoot()

    def play(self, shooting_strategy, spray_time=0.7, draw_boxes=False):
        while True:
            # Process user input Average detection time: 0.31920754507686316
            display_banner = self.get_key_triggers()
            if display_banner:
                self.display_counter = 5
            elif not display_banner and self.display_counter > 0:
                self.display_counter -= 1

            if self.display_counter == 0:
                self.screen_manipulator.clear_screen()
                self.display_counter = -1

            start_total = time.time()
            # self.screen_manipulator.clear_screen()
            frame = self.grab_frame()
            start = time.time()
            bboxes = self.object_detector.detect_in_frame(frame)
            end = time.time()
            self.detection_times.append(end - start)
            start = time.time()
            # chosen_box = self.headshot_only_strategy(bboxes, 'ALL')
            chosen_box = self.strategize(bboxes, self.opponent_team, self.aiming_strategy)
            end = time.time()
            self.strategize_times.append(end - start)
            if self.box_is_valid(chosen_box):
                if self.draw:
                    self.draw_boxes(bboxes, chosen_box)
                    time.sleep(1)
                    self.screen_manipulator.clear_screen()
                start = time.time()
                self.set_crosshair_on_box(chosen_box, shoot=True, spray_time=spray_time)
                end = time.time()
                self.aiming_times.append(end - start)
                self.engaged = True
            else:
                self.engaged = False
            end_total = time.time()
            self.total_times.append(end_total - start_total)
            if keyboard.is_pressed('k'):
                self.screen_manipulator.draw_banner("Hank stopped")
                print("Hank stopped")
                time.sleep(1)
                break

    def test_key_triggers(self):
        while True:
            if keyboard.is_pressed('f9'):
                print('You Pressed k!')
                self.screen_manipulator.draw_banner("TEST")
            for event in pygame.event.get():
                print(event)
            self.screen_manipulator.fpsClock.tick(10)
            # break

    def change_opponent_team(self):
        opponents = ''
        if self.opponent_team == T:
            self.opponent_team = CT
            opponents = 'CT'
        elif self.opponent_team == CT:
            self.opponent_team = ALL
            opponents = 'ALL'
        else:
            self.opponent_team = T
            opponents = 'T'

        self.screen_manipulator.draw_banner(f'Targeting: {opponents} players')

    def change_aiming_strategy(self):
        if self.aiming_strategy == self.fastest_kill_strategy:
            self.aiming_strategy = self.headshot_only_strategy
        elif self.aiming_strategy == self.headshot_only_strategy:
            self.aiming_strategy = self.proximal_strategy
        else:
            self.aiming_strategy = self.fastest_kill_strategy
        self.screen_manipulator.draw_banner(f'Aiming strategy: {self.aiming_strategy.__name__}')

    def toggle_drawing_boxes(self):
        self.draw = not self.draw
        self.screen_manipulator.draw_banner(f'Drawing boxes: {self.draw}')

    def change_spray_time(self):
        self.spray_time += 0.1
        if self.spray_time > 1.0:
            self.spray_time = 0
        self.screen_manipulator.draw_banner(f'Spray time: {self.spray_time}')

    def get_key_triggers(self):
        display_banner = False
        try:
            if keyboard.is_pressed('f1'):
                self.change_opponent_team()
                display_banner = True
                cv2.waitKey(10)
            elif keyboard.is_pressed('f2'):
                self.change_aiming_strategy()
                display_banner = True
                cv2.waitKey(10)
            elif keyboard.is_pressed('f3'):
                self.toggle_drawing_boxes()
                display_banner = True
                cv2.waitKey(10)
            elif keyboard.is_pressed('f4'):
                self.change_spray_time()
                display_banner = True
                cv2.waitKey(10)
            for event in pygame.event.get():
                print(event)
        except:
            return False
        return display_banner

    def start_bot_on_command(self):
        while True:
            if keyboard.is_pressed('k'):
                print('Starting Hank')
                self.screen_manipulator.draw_banner("Hank is here")
                time.sleep(0.3)
                self.play(self.aiming_strategy, spray_time=self.spray_time, draw_boxes=self.draw)
            elif keyboard.is_pressed('q'):
                print("Shutting down Hank")
                break
            for event in pygame.event.get():
                print(event)
            self.screen_manipulator.fpsClock.tick(30)

    def plot_detection_times(self):
        plt.rcParams['figure.figsize'] = [35, 20]
        plt.yticks(np.arange(0, max(self.detection_times) + 0.1, 0.05))
        plt.plot(self.detection_times, color='magenta')  # plot the data
        plt.xticks(range(0, len(self.detection_times) + 1, 1))  # set the tick frequency on x-axis

        plt.ylabel('detection times in seconds')  # set the label for y axis
        plt.xlabel('index')  # set the label for x-axis
        plt.title("Detection times over a playing round")  # set the title of the graph
        average = sum(self.detection_times) / len(self.detection_times)
        print("Average detection time: " + str(average))
        plt.axhline(y=average, color='green', linestyle='-')
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

    def plot_total_times(self):
        plt.rcParams['figure.figsize'] = [35, 20]
        plt.yticks(np.arange(0, max(self.total_times) + 0.1, 0.05))
        plt.plot(self.total_times, color='orange')  # plot the data
        plt.xticks(range(0, len(self.total_times) + 1, 1))  # set the tick frequency on x-axis

        plt.ylabel('cycle times in seconds')  # set the label for y axis
        plt.xlabel('index')  # set the label for x-axis
        plt.title("Cycle running times over a playing round")  # set the title of the graph
        average = sum(self.total_times) / len(self.total_times)
        print("total average: ", average)
        plt.axhline(y=average, color='green', linestyle='-')
        plt.savefig('plot_total.png', bbox_inches='tight')
        # plt.show()  # display the graph
        plt.cla()
        plt.clf()


def start():
    game_master = GameMaster()
    try:
        game_master.start_bot_on_command()
        pygame.quit()
        quit()
    except KeyboardInterrupt:
        pygame.quit()
        quit()


if __name__ == '__main__':
    # start()
    master = GameMaster()
    master.demo()
    # # master.test_key_triggers()
    # # master.test_detection_speed_frame()
    # try:
    #     # master.demo()
    #     # master.test_shooting()
    #     # master.test_continuous()
    #     # master.test_strategize()
    #     # master.play()
    #     master.start_bot_on_command()
    # except KeyboardInterrupt:
    #     print("Plotting...")
    #     master.plot_detection_times()
    #     master.plot_strategize_times()
    #     master.plot_aiming_times()
    #     master.plot_total_times()
    #     print(f"Clicks made: {master.clicks}")
    #     pygame.quit()
    #     quit()
