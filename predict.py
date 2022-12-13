import os
import time

import torch
from torchvision import transforms
import numpy as np
from PIL import Image

from unet import UNet


def time_synchronized():
    torch.cuda.synchronize() if torch.cuda.is_available() else None
    return time.time()


def main():
    classes = 1  # exclude background
    # weights_path = "./save_weights/best_model.pth"
    weights_path = "./results/epoch_50_best_model.pth"
    # weights_path = "./results/generailzation_epoch_8_best_model.pth"
    img_path = "./SegmentationData/Domain3/data/V0001.bmp"
    roi_mask_path = "./SegmentationData/Domain3/mask/V0001.bmp"
    assert os.path.exists(weights_path), f"weights {weights_path} not found."
    assert os.path.exists(img_path), f"image {img_path} not found."
    assert os.path.exists(roi_mask_path), f"image {roi_mask_path} not found."

    mean = (0.485, 0.456, 0.406)
    std = (0.229, 0.224, 0.225)

    # get devices
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print("using {} device.".format(device))

    # create model
    model = UNet(in_channels=3, num_classes=classes+1, base_c=32)

    # load weights
    model.load_state_dict(torch.load(weights_path, map_location='cpu')['model'])
    model.to(device)

    # load roi mask
    roi_img = Image.open(roi_mask_path).convert('L')
    roi_img = np.array(roi_img)

    # load image
    original_img = Image.open(img_path).convert('RGB')

    # from pil image to tensor and normalize
    data_transform = transforms.Compose([transforms.ToTensor(),
                                         transforms.Resize(480),
                                         transforms.Normalize(mean=mean, std=std)])
    
    data_transform1 = transforms.Compose([transforms.ToTensor(),
                                         transforms.Resize(480)])
    img = data_transform(original_img)
    roi_img = data_transform1(roi_img)
    # expand batch dimension
    img = torch.unsqueeze(img, dim=0)
    roi_img = torch.squeeze(roi_img)

    model.eval()  # 进入验证模式
    with torch.no_grad():
        # init model
        img_height, img_width = img.shape[-2:]
        init_img = torch.zeros((1, 3, img_height, img_width), device=device)
        model(init_img)

        t_start = time_synchronized()
        output = model(img.to(device))
        t_end = time_synchronized()
        print("inference time: {}".format(t_end - t_start))

        prediction = output['out'].argmax(1).squeeze(0)
        prediction = prediction.to("cpu").numpy().astype(np.uint8)
        # 将前景对应的像素值改成255(白色)
        prediction[prediction == 1] = 255
        # 将不敢兴趣的区域像素设置成0(黑色)
        prediction[roi_img == 0] = 255
        mask = Image.fromarray(prediction)
        mask.save("test_result.png")


if __name__ == '__main__':
    main()