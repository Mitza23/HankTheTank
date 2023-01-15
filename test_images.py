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

warnings.filterwarnings("ignore")


def main():
    process_folder('test_images')


def process_folder(folder_path, output_path='test_detect/'):
    images = os.listdir(folder_path)
    for image in images:
        name = image.split('.')[0]
        detect_in_image(folder_path + '/' + image, output_path, name)


def detect_in_image(input_path, output_path, name):
    start = time.time()
    bboxes = detect(input_path)
    end = time.time()
    print(end - start)
    img = cv2.imread(input_path)
    for box in bboxes:
        img = plot_bounding_box(img, box)
    cv2.imwrite(output_path + name + '_detected.jpg', img)


def plot_bounding_box(img, bbox):
    x1, y1, x2, y2, conf, clasz = bbox
    # Draw bounding box on image
    if clasz == 0:  # CT-body
        cv2.circle(img, ((x1 + x2) // 2, ((y1 + y2) // 2) - (y2 - y1) // 6), radius=0, color=(100, 100, 255), thickness=5)
        cv2.rectangle(img, (x1, y1), (x2, y2), (255, 0, 150), 2)

    elif clasz == 1:  # CT-head
        cv2.circle(img, ((x1 + x2) // 2, ((y1 + y2) // 2)), radius=0, color=(0, 255, 0), thickness=3)
        cv2.rectangle(img, (x1, y1), (x2, y2), (255, 255, 0), 1)

    elif clasz == 2:  # T-body
        cv2.circle(img, ((x1 + x2) // 2, ((y1 + y2) // 2) - (y2 - y1) // 6), radius=0, color=(100, 100, 255), thickness=5)
        cv2.rectangle(img, (x1, y1), (x2, y2), (255, 255, 0), 2)

    elif clasz == 3:  # T-head
        cv2.circle(img, ((x1 + x2) // 2, ((y1 + y2) // 2)), radius=0, color=(0, 255, 0), thickness=3)
        cv2.rectangle(img, (x1, y1), (x2, y2), (100, 100, 255), 1)

    return img


def detect(source, weights='best.pt', imgsz=640, conf_thres=0.5, iou_thres=0.45, agnostic_nms=False):
    bboxes = []
    webcam = source.isnumeric() or source.endswith('.txt') or source.lower().startswith(
        ('rtsp://', 'rtmp://', 'http://', 'https://'))

    # Initialize
    # set_logging()
    device = select_device('0')
    half = device.type != 'cpu'  # half precision only supported on CUDA

    # Load model
    model = attempt_load(weights, map_location=device)  # load FP32 model
    stride = int(model.stride.max())  # model stride
    imgsz = check_img_size(imgsz, s=stride)  # check img_size

    if half:
        model.half()  # to FP16

    # Second-stage classifier
    classify = False
    if classify:
        modelc = load_classifier(name='resnet101', n=2)  # initialize
        modelc.load_state_dict(torch.load('weights/resnet101.pt', map_location=device)['model']).to(device).eval()

    # Set Dataloader
    vid_path, vid_writer = None, None
    if webcam:
        view_img = check_imshow()
        cudnn.benchmark = True  # set True to speed up constant image size inference
        dataset = LoadStreams(source, img_size=imgsz, stride=stride)
    else:
        dataset = LoadImages(source, img_size=imgsz, stride=stride)

    # Get names and colors
    names = model.module.names if hasattr(model, 'module') else model.names
    colors = [[random.randint(0, 255) for _ in range(3)] for _ in names]

    # Run inference
    if device.type != 'cpu':
        model(torch.zeros(1, 3, imgsz, imgsz).to(device).type_as(next(model.parameters())))  # run once
    old_img_w = old_img_h = imgsz
    old_img_b = 1

    t0 = time.time()
    for path, img, im0s, vid_cap in dataset:
        img = torch.from_numpy(img).to(device)
        img = img.half() if half else img.float()  # uint8 to fp16/32
        img /= 255.0  # 0 - 255 to 0.0 - 1.0
        if img.ndimension() == 3:
            img = img.unsqueeze(0)

        # Warmup
        if device.type != 'cpu' and (
                old_img_b != img.shape[0] or old_img_h != img.shape[2] or old_img_w != img.shape[3]):
            old_img_b = img.shape[0]
            old_img_h = img.shape[2]
            old_img_w = img.shape[3]
            for i in range(3):
                model(img, augment=False)[0]

        # Inference
        t1 = time_synchronized()
        with torch.no_grad():  # Calculating gradients would cause a GPU memory leak
            pred = model(img, augment=False)[0]
        t2 = time_synchronized()

        # Apply NMS

        pred = non_max_suppression(pred, conf_thres, iou_thres, classes=None, agnostic=agnostic_nms)
        t3 = time_synchronized()

        # Apply Classifier
        if classify:
            pred = apply_classifier(pred, modelc, img, im0s)

        # Process detections
        for i, det in enumerate(pred):  # detections per image
            if webcam:  # batch_size >= 1
                p, s, im0, frame = path[i], '%g: ' % i, im0s[i].copy(), dataset.count
            else:
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


main()
