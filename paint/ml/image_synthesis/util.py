import re
import importlib
import torch
from argparse import Namespace
import numpy as np
from PIL import Image
import os
import argparse

def tensor2im(image_tensor, imtype=np.uint8, normalize=True):
    if isinstance(image_tensor, list):
        image_numpy = []
        for i in range(len(image_tensor)):
            image_numpy.append(tensor2im(image_tensor[i], imtype, normalize))
        return image_numpy

    if image_tensor.dim() == 4:
        images_np = []
        for b in range(image_tensor.size(0)):
            one_image = image_tensor[b]
            one_image_np = tensor2im(one_image)
            images_np.append(one_image_np.reshape(1, *one_image_np.shape))
        images_np = np.concatenate(images_np, axis=0)
        return images_np

    if image_tensor.dim() == 2:
        image_tensor = image_tensor.unsqueeze(0)
    image_numpy = image_tensor.detach().cpu().float().numpy()
    if normalize:
        image_numpy = (np.transpose(image_numpy, (1, 2, 0)) + 1) / 2.0 * 255.0
    else:
        image_numpy = np.transpose(image_numpy, (1, 2, 0)) * 255.0
    image_numpy = np.clip(image_numpy, 0, 255)
    if image_numpy.shape[2] == 1:
        image_numpy = image_numpy[:, :, 0]
    return image_numpy.astype(imtype)

def convert_output_to_numpy(output):
    t = tensor2im(output)
    return t

def save_image(image_numpy, image_path, create_dir=False):
    if create_dir:
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
    if len(image_numpy.shape) == 2:
        image_numpy = np.expand_dims(image_numpy, axis=2)
    if image_numpy.shape[2] == 1:
        image_numpy = np.repeat(image_numpy, 3, 2)
    image_pil = Image.fromarray(image_numpy)
    image_pil.save(image_path.replace('.jpg', '.png'))
    return image_pil


def mkdirs(paths):
    if isinstance(paths, list) and not isinstance(paths, str):
        for path in paths:
            mkdir(path)
    else:
        mkdir(paths)


def mkdir(path):
    if not os.path.exists(path):
        os.makedirs(path)


def atoi(text):
    return int(text) if text.isdigit() else text


def natural_keys(text):
    '''
    alist.sort(key=natural_keys) sorts in human order
    http://nedbatchelder.com/blog/200712/human_sorting.html
    (See Toothy's implementation in the comments)
    '''
    return [atoi(c) for c in re.split('(\d+)', text)]


def natural_sort(items):
    items.sort(key=natural_keys)


def str2bool(v):
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


def find_class_in_module(target_cls_name, module):
    target_cls_name = target_cls_name.replace('_', '').lower()
    clslib = importlib.import_module(module)
    cls = None
    for name, clsobj in clslib.__dict__.items():
        if name.lower() == target_cls_name:
            cls = clsobj

    if cls is None:
        print("In %s, there should be a class whose name matches %s in lowercase without underscore(_)" % (module, target_cls_name))
        exit(0)

    return cls


def save_network(net, label, epoch, opt):
    save_filename = '%s_net_%s.pth' % (epoch, label)
    save_path = os.path.join(opt.checkpoints_dir, opt.name, save_filename)
    torch.save(net.cpu().state_dict(), save_path)
    if len(opt.gpu_ids) and torch.cuda.is_available():
        net.cuda()


def load_network(net, label, epoch, opt):
    save_filename = '%s_net_%s.pth' % (epoch, label)
    save_dir = os.path.join(opt.checkpoints_dir, opt.name)
    save_path = os.path.join(save_dir, save_filename)
    # print(save_path)
    # exit()
    weights = torch.load(save_path)
    net.load_state_dict(weights)
    return net


# ###############################################################################
# # Code from
# # https://github.com/ycszen/pytorch-seg/blob/master/transform.py
# # Modified so it complies with the Citscape label map colors
# ###############################################################################
# def uint82bin(n, count=8):
#     """returns the binary of integer n, count refers to amount of bits"""
#     return ''.join([str((n >> y) & 1) for y in range(count - 1, -1, -1)])


# def labelcolormap(N):
#     if N == 35:  # cityscape
#         cmap = np.array([(0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (111, 74, 0), (81, 0, 81),
#                          (128, 64, 128), (244, 35, 232), (250, 170, 160), (230, 150, 140), (70, 70, 70), (102, 102, 156), (190, 153, 153),
#                          (180, 165, 180), (150, 100, 100), (150, 120, 90), (153, 153, 153), (153, 153, 153), (250, 170, 30), (220, 220, 0),
#                          (107, 142, 35), (152, 251, 152), (70, 130, 180), (220, 20, 60), (255, 0, 0), (0, 0, 142), (0, 0, 70),
#                          (0, 60, 100), (0, 0, 90), (0, 0, 110), (0, 80, 100), (0, 0, 230), (119, 11, 32), (0, 0, 142)],
#                         dtype=np.uint8)
#     else:
#         cmap = np.zeros((N, 3), dtype=np.uint8)
#         for i in range(N):
#             r, g, b = 0, 0, 0
#             id = i + 1  # let's give 0 a color
#             for j in range(7):
#                 str_id = uint82bin(id)
#                 r = r ^ (np.uint8(str_id[-1]) << (7 - j))
#                 g = g ^ (np.uint8(str_id[-2]) << (7 - j))
#                 b = b ^ (np.uint8(str_id[-3]) << (7 - j))
#                 id = id >> 3
#             cmap[i, 0] = r
#             cmap[i, 1] = g
#             cmap[i, 2] = b

#         if N == 182:  # COCO
#             important_colors = {
#                 'sea': (54, 62, 167),
#                 'sky-other': (95, 219, 255),
#                 'tree': (140, 104, 47),
#                 'clouds': (170, 170, 170),
#                 'grass': (29, 195, 49)
#             }
#             for i in range(N):
#                 name = util.coco.id2label(i)
#                 if name in important_colors:
#                     color = important_colors[name]
#                     cmap[i] = np.array(list(color))

#     return cmap


# class Colorize(object):
#     def __init__(self, n=35):
#         self.cmap = labelcolormap(n)
#         self.cmap = torch.from_numpy(self.cmap[:n])

#     def __call__(self, gray_image):
#         size = gray_image.size()
#         color_image = torch.ByteTensor(3, size[1], size[2]).fill_(0)

#         for label in range(0, len(self.cmap)):
#             mask = (label == gray_image[0]).cpu()
#             color_image[0][mask] = self.cmap[label][0]
#             color_image[1][mask] = self.cmap[label][1]
#             color_image[2][mask] = self.cmap[label][2]

#         return color_image
