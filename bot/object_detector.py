import os
import time
import warnings

import cv2
import torch
import torch.backends.cudnn as cudnn
from numpy import random

from models.experimental import attempt_load
from utils.datasets import LoadStreams, LoadImages
from utils.general import check_img_size, check_imshow, non_max_suppression, apply_classifier, \
    scale_coords
from utils.torch_utils import select_device, load_classifier, time_synchronized


class ObjectDetector:
    def __init__(self):
        self.weights_path = 'best.pt'
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

    def detect(self, source):
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


if __name__ == '__main__':
    model = ObjectDetector()
    model.detect('../test_images/1.jpg')