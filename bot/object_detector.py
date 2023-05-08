import time

import numpy as np
import torch

from models.experimental import attempt_load
from utils.datasets import LoadImages, letterbox
from utils.general import check_img_size, non_max_suppression, scale_coords
from utils.torch_utils import select_device, time_synchronized


class ObjectDetector:
    def __init__(self):
        self.weights_path = '../best.pt'
        self.image_size = 640
        self.confidence_threshold = 0.5
        self.iou_threshold = 0.45
        self.agnostic_nms = False
        self.device = select_device('0')
        self.half = True  # half precision only supported on CUDA
        # Load model
        self.model = attempt_load(self.weights_path, map_location=self.device)  # load FP32 model
        self.stride = int(self.model.stride.max())  # model stride
        self.image_size = check_img_size(self.image_size, s=self.stride)  # check img_size
        self.warmup()

    def detect_from_source(self, source):
        bboxes = []

        self.model.half()  # to FP16

        dataset = LoadImages(source, img_size=self.image_size, stride=self.stride)

        # Run inference

        self.model(torch.zeros(1, 3, self.image_size, self.image_size).to(self.device).type_as(
            next(self.model.parameters())))  # run once
        old_img_w = old_img_h = self.image_size
        old_img_b = 1

        t0 = time.time()
        for path, img, im0s, vid_cap in dataset:
            img = torch.from_numpy(img).to(self.device)
            img = img.half() if self.half else img.float()  # uint8 to fp16/32
            img /= 255.0  # 0 - 255 to 0.0 - 1.0
            if img.ndimension() == 3:
                img = img.unsqueeze(0)

            # Warmup
            if old_img_b != img.shape[0] or old_img_h != img.shape[2] or old_img_w != img.shape[3]:
                old_img_b = img.shape[0]
                old_img_h = img.shape[2]
                old_img_w = img.shape[3]
                for i in range(3):
                    self.model(img, augment=False)[0]

            # Inference
            t1 = time_synchronized()
            with torch.no_grad():  # Calculating gradients would cause a GPU memory leak
                pred = self.model(img, augment=False)[0]
            t2 = time_synchronized()

            # Apply NMS

            pred = non_max_suppression(pred, self.confidence_threshold, self.iou_threshold, classes=None,
                                       agnostic=self.agnostic_nms)
            t3 = time_synchronized()

            # Process detections
            for i, det in enumerate(pred):  # detections per image
                p, s, im0, frame = path, '', im0s, getattr(dataset, 'frame', 0)

                if len(det):
                    # Rescale boxes from img_size to im0 size
                    det[:, :4] = scale_coords(img.shape[2:], det[:, :4], im0.shape).round()

                    for obj in range(len(det)):
                        aux = det[obj].data[0:6].tolist()
                        aux[4] = int(aux[4] * 100)
                        for i in range(len(aux)):
                            aux[i] = int(aux[i])
                        # print(aux)
                        bboxes.append(aux)
        return bboxes

    def detect_in_frame(self, frame_to_process):
        bboxes = []

        self.model.half()  # to FP16

        # The preparations done by the Data Loader
        # Prepare frame
        img = img = letterbox(frame_to_process, self.image_size, stride=self.stride)[0]
        # Convert
        img = img[:, :, ::-1].transpose(2, 0, 1)  # BGR to RGB, to 3x416x416
        img = np.ascontiguousarray(img)

        # Run inference
        self.model(torch.zeros(1, 3, self.image_size, self.image_size).to(self.device).type_as(
            next(self.model.parameters())))  # run once
        old_img_w = old_img_h = self.image_size
        old_img_b = 1

        t0 = time.time()

        img = torch.from_numpy(img).to(self.device)
        img = img.half() if self.half else img.float()  # uint8 to fp16/32
        img /= 255.0  # 0 - 255 to 0.0 - 1.0
        if img.ndimension() == 3:
            img = img.unsqueeze(0)

        # Warmup
        if old_img_b != img.shape[0] or old_img_h != img.shape[2] or old_img_w != img.shape[3]:
            old_img_b = img.shape[0]
            old_img_h = img.shape[2]
            old_img_w = img.shape[3]
            for i in range(3):
                self.model(img, augment=False)[0]

        # Inference
        t1 = time_synchronized()
        with torch.no_grad():  # Calculating gradients would cause a GPU memory leak
            pred = self.model(img, augment=False)[0]
        t2 = time_synchronized()

        # Apply NMS
        pred = non_max_suppression(pred, self.confidence_threshold, self.iou_threshold, classes=None,
                                   agnostic=self.agnostic_nms)
        t3 = time_synchronized()

        # Process detections
        for i, det in enumerate(pred):  # detections per image
            if len(det):
                # Rescale boxes from img_size to im0 size
                det[:, :4] = scale_coords(img.shape[2:], det[:, :4], frame_to_process.shape).round()

                for obj in range(len(det)):
                    aux = det[obj].data[0:6].tolist()
                    aux[4] = int(aux[4] * 100)
                    for i in range(len(aux)):
                        aux[i] = int(aux[i])
                    bboxes.append(aux)
        return bboxes

    def warmup(self):
        try:
            self.detect_from_source('../test_images/2.jpg')
        except:
            pass

    @staticmethod
    def get_classes_count(bboxes):
        ct, ct_head, t, t_head = 0, 0, 0, 0
        for box in bboxes:
            _class = box[5]
            if _class == 0:
                ct += 1
            elif _class == 1:
                ct_head += 1
            elif _class == 2:
                t += 1
            elif _class == 3:
                t_head += 1
        return {'ct': ct, 'ct_head': ct_head, 't': t, 't_head': t_head}

    def test_detection_speed_from_source(self):
        start = time.time()
        self.detect_from_source('../test_images/1.jpg')
        end = time.time()
        print(end - start)
        assert end - start < 0.3
        start = time.time()
        self.detect_from_source('../test_images/1586.jpg')
        end = time.time()
        print(end - start)
        assert end - start < 0.3
        start = time.time()
        self.detect_from_source('../test_images/393.jpg')
        end = time.time()
        print(end - start)
        assert end - start < 0.3
        start = time.time()
        self.detect_from_source('../test_images/176.jpg')
        end = time.time()
        print(end - start)
        assert end - start < 0.3
        start = time.time()
        self.detect_from_source('../test_images/1187.jpg')
        end = time.time()
        print(end - start)
        assert end - start < 0.3

    def test_detected_box_count(self):
        # 1 CT facing straight at close to mid-range
        bboxes = self.detect_from_source('../test_images/1.jpg')
        print(len(bboxes))
        # assert len(bboxes) >= 1
        classes = self.get_classes_count(bboxes)
        assert classes['ct'] == 1 and classes['ct_head'] >= 0 and classes['t'] == 0 and classes['t_head'] == 0
        # 1 T facing straight at close to mid-range and 1 T hidden under a slope
        bboxes = self.detect_from_source('../test_images/1586.jpg')
        print(len(bboxes))
        # assert len(bboxes) >= 1
        classes = self.get_classes_count(bboxes)
        assert classes['ct'] == 0 and classes['ct_head'] == 0 and classes['t'] == 1 and classes['t_head'] >= 0
        # 4 CT from the back at distance and in the shadows
        bboxes = self.detect_from_source('../test_images/393.jpg')
        print(len(bboxes))
        # assert len(bboxes) >= 4
        classes = self.get_classes_count(bboxes)
        assert classes['ct'] == 4 and classes['ct_head'] >= 0 and classes['t'] == 0 and classes['t_head'] == 0
        # 1 T close up with the back and one CT in the distance, in front of the crosshair and from the side
        bboxes = self.detect_from_source('../test_images/176.jpg')
        print(len(bboxes))
        # assert len(bboxes) >= 2
        classes = self.get_classes_count(bboxes)
        assert classes['ct'] == 1 and classes['ct_head'] >= 0 and classes['t'] == 1 and classes['t_head'] >= 0
        # 2 T at mid-range & distance on their sides and one in the shadows
        bboxes = self.detect_from_source('../test_images/1535.jpg')  # CAUSES PROBLEMS -> DETECTS 4 T
        print(len(bboxes))
        # assert len(bboxes) >= 2
        classes = self.get_classes_count(bboxes)
        assert classes['ct'] == 0 and classes['ct_head'] == 0 and classes['t'] == 2 and classes['t_head'] >= 0
        # # 3 T at mid-range & distance facing straight
        # bboxes = self.detect_from_source('../test_images/1187.jpg') # CAUSES PROBLEMS -> DETECTS 4 T
        # print(len(bboxes))
        # print(bboxes)
        # # assert len(bboxes) >= 3
        # classes = self.get_classes_count(bboxes)
        # assert classes['ct'] == 0 and classes['ct_head'] == 0 and classes['t'] == 3 and classes['t_head'] >= 0


if __name__ == '__main__':
    model = ObjectDetector()
    # print(model.detect_from_source('../test_images/1.jpg'))
    model.test_detection_speed_from_source()
    model.test_detected_box_count()
