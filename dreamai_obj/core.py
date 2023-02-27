# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/00_core.ipynb.

# %% auto 0
__all__ = ['obj_model', 'obj_detect', 'box_overlap', 'distance_to_camera', 'detect_obstacles_3', 'blur_face', 'blur_faces',
           'save_video']

# %% ../nbs/00_core.ipynb 3
from dreamai.core import *
from dreamai.vision import *
from dreamai.imports import *
from .imports import *

# %% ../nbs/00_core.ipynb 4
def obj_model():
    return yolov5.load('yolov5s.pt')

def obj_detect(model, img, conf=0.3, iou=0.45, agnostic=False, multi_label=False, max_det=1000):
    
    model.conf = conf
    model.iou = iou
    model.agnostic = agnostic
    model.multi_label = multi_label
    model.max_det = max_det
    results = model(img, augment=True)
    # print()
    # print(results.names)
    predictions = results.pred[0]
    boxes = predictions[:,:4]
    scores = predictions[:,4]
    categories = predictions[:,5]
    # print(f'\ncategories: {categories}')
    return boxes.detach().cpu(), [results.names[int(cat)] for cat in categories]

def box_overlap(box1, box2, limit=0):
    x1, y1, x2, y2 = box1
    x3, y3, x4, y4 = box2
    x_overlap = max(0, min(x2,x4) - max(x1,x3))
    y_overlap = max(0, min(y2,y4) - max(y1,y3))
    overlap = (x_overlap * y_overlap) > limit
    return overlap

def distance_to_camera(width, focal_len, pixel_width):
    return (width * focal_len) / pixel_width

def detect_obstacles_3(model, img, targets=[], alert=True, h_limit=1024, show=False, box_thicknes=7,
                       avoidance_x=0, avoidance_y=0.5, avoidance_w=0.5, avoidance_h=0.5, obj_h_limit=0.5,
                       conf=0.3, overlap_limit=0, color='red'):
    
    color = color_to_rgb(color)
    img = copy.deepcopy(img)
    h,w = get_hw(img)
    if h > h_limit:
        img = imutils.resize(img, height=h_limit)
    h,w = get_hw(img)
    if is_float(avoidance_h):
        avoidance_h = int(h*avoidance_h)
    if is_float(avoidance_w):
        avoidance_w = int(w*avoidance_w)
    if is_float(avoidance_x):
        avoidance_x = int(w*avoidance_x)
    if is_float(avoidance_y):
        avoidance_y = int(h*avoidance_y)
    if obj_h_limit is not None:
        if is_float(obj_h_limit):
            obj_h_limit = int(h*obj_h_limit)
    else:
        obj_h_limit = h
    green = solid_color_img((avoidance_h, avoidance_w, 3), 'green', alpha=150)
    red = solid_color_img_like(green, 'red', alpha=150)
    # gx,gy = get_pos(green, img, [0,1.])
    if show:
        print('\nIMAGE:\n')
        plt_show(paste_img(green, img, [avoidance_x,avoidance_y]))
    found = False
    boxes,cats = obj_detect(model, img, conf=conf)
    if len(targets) == 0:
        targets = cats
    # print(f'{len(boxes)}, {len(cats)}')
    cat_boxes = []
    for box,cat in zip(boxes, cats):
        if cat in targets:
            # print(f'\nBOX: {box}\n')
            # print(f'\nCATEGORY: {cat}\n')
            x1, y1, x2, y2 = [int(x) for x in box]
            bh = y2-y1
            if bh > obj_h_limit:
                continue
            bw = x2-x1
            c_area = bh*bw
            box1 = [x1, y1, x2, y2]
            cat_boxes.append(box1)
            box2 = [avoidance_x, avoidance_y, avoidance_x+avoidance_w, avoidance_y+avoidance_h]
            if not box_overlap(box1, box2, overlap_limit) and alert:
                continue
            if not found:
                found = True
                if show:
                    print('\nOBSTACLE(S) FOUND:\n')
            if show:
                print(f'Area: {c_area}, x: {x1}, y: {y1}, bw: {bw}, bh: {bh}')
            # try:
            txt_y = y1 - 10 if y1 - 10 > 10 else y1 + 10
            cv2.putText(img, cat, (x1, txt_y), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)
            cv2.rectangle(img, (x1,y1), (x2,y2), color, box_thicknes)
            # except:
                # pass
            if show:
                plt_show(paste_img(red, img, [avoidance_x,avoidance_y]))
    if not found and show:
        print('NO OBSTACLES FOUND')
    if found and alert:
        img = paste_img(red, img, [avoidance_x,avoidance_y])
    elif alert:
        img = paste_img(green, img, [avoidance_x,avoidance_y])
    torch.cuda.empty_cache()
    return img, cat_boxes

def blur_face(model, img, conf=0.3, h_div=3):
    boxes, cats = obj_detect(model, img, conf=conf)
    for box,cat in zip(boxes, cats):
        if cat == 'person':
            x1, y1, x2, y2 = [int(x) for x in box]
            h = y2-y1
            face_coords = y1, y1+h//h_div, x1, x2
            face = img[face_coords[0]:face_coords[1], face_coords[2]:face_coords[3]]
            img[face_coords[0]:face_coords[1], face_coords[2]:face_coords[3]] = cv2.GaussianBlur(face, (35,35), 100)
    return img

def blur_faces(model, video, conf=0.3, h_div=3):
    if path_or_str(video):
        video = mp.VideoFileClip(video)
    frames = [blur_face(model, frame.copy(), conf=conf, h_div=h_div) for frame in video.iter_frames()]
    return mp.ImageSequenceClip(frames, fps=video.fps)

def save_video(v, path='video.mp4', audio=True, codec='libx264',ffmpeg_path='/usr/bin/ffmpeg'):
    
    if type(v).__name__ == 'ProntoClip':
        v = v.v
    if 'Image' in type(v).__name__:
        v.write_videofile(path,audio=audio,fps=v.fps, audio_codec='aac', bitrate=str(np.power(10, 6)),
                          preset='ultrafast', verbose=False, threads=6, logger=None, codec=codec)
    else:
        try:
            if not audio:
                v = v.set_audio(None)
            v.save(bitrate='10000000', output_file=path, ffmpeg_path=ffmpeg_path, codec=codec)
        except:
            v.write_videofile(path,audio=audio,fps=v.fps, audio_codec='aac', bitrate=str(np.power(10, 6)),
                              preset='ultrafast', verbose=False, threads=6, logger=None, codec=codec)

