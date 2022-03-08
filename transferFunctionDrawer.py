# transfer function drawer. you can draw transfer function & the change will apply immediately
# click on function graph to add inflection point
# click on point to remove them
# ref. https://matplotlib.org/stable/users/explain/event_handling.html

import argparse
import cv2 as cv
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt

description = """
    A GUI to draw & apply a piecewise linear transfer function to an image.
    
    Click on transfer function to add an inflection point.
    CLick on point to remove that inflection point.

    Press "m" to save image to output path (set in `--output`).
    Press "q" to exit the program.
"""

parser = argparse.ArgumentParser(description=description, formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument("--input", help="Image to apply transfer function", required=True)
parser.add_argument("--output", help="Output path of saved image", required=True)
args = parser.parse_args()

input_path = Path(args.input)
output_path = Path(args.output)

# check if image valid
if not Path(args.input).is_file() or cv.imread(str(input_path), cv.IMREAD_GRAYSCALE) == None:
    print('Given input path is not a valid image.')
    exit(1)

# main class for dealing with inputs
class TransferFunctionDrawer:
    def __init__(self, line, img):
        self.line = line
        self.coords = [(x, y) for x, y in zip(line.get_xdata(), line.get_ydata())]

        self.cid_click = line.figure.canvas.mpl_connect('button_press_event', self.onclick)
        self.cid_pick = line.figure.canvas.mpl_connect('pick_event', self.onpick)
        self.cid_press = line.figure.canvas.mpl_connect('key_press_event', self.onPressKey)

        # for picking: since when picking, `button_press_event` will also be raised...
        self.just_picked = False

        self.cv_name = 'Image'
        self.cv_ori_name = 'OriginalImage'
        self.tf_img = img
        self.img = img
        cv.namedWindow(self.cv_name)
        cv.namedWindow(self.cv_ori_name)
        cv.imshow(self.cv_name, self.tf_img)
        cv.imshow(self.cv_ori_name, self.img)

    def onclick(self, event):
        def inRange(a, inf, sup):
            return a <= sup and a >= inf
        
        # avoid simultaneous pick & click event, note that pick will always be first
        if self.just_picked:    
            self.just_picked = False
            return

        if event.inaxes != self.line.axes: 
            return

        # avoid out-of-bound inflection points.
        # that include rendering (0, 0), (255, 255) not being the first & last point of self.coords.
        # however this won't avoid the case that 2 inflection points having the same x-value
        # which is a somewhat undefined behavior if their y-value are also different...
        if not inRange(int(event.xdata), 1, 254) or not inRange(int(event.ydata), 0, 255):
            return

        self.coords.append((int(event.xdata), int(event.ydata)))

        # must draw from small x points to large x points
        # also required for updateImage::makePiecewiseLinearTF
        self.coords = sorted(self.coords, key=lambda coord: coord[0])
        self.updateLine()
        self.updateImage()
        self.printCoords()
    
    def onpick(self, event):
        self.just_picked = True

        # avoid deleting (0, 0) and (255, 255)
        if event.ind[0] in [0, len(self.coords)-1]:
            return

        self.coords.pop(event.ind[0])
        self.updateLine()
        self.updateImage()
        self.printCoords()

    def printCoords(self):
        print(f'Inflection points: {self.coords}')
        
    def updateLine(self):
        self.line.set_data([i for i, j in self.coords], [j for i, j in self.coords])
        self.line.figure.canvas.draw()
    
    def updateImage(self):
        def applyTransferFunction(img, tf_fn):
            # transfer function (tf_fn) as form of array of size 256
            img = img.copy()
            for r in range(img.shape[0]):
                for c in range(img.shape[1]):
                    img[r, c] = tf_fn[img[r, c]]
            return img

        def makePiecewiseLinearTF(pts):
            # make a piecewise linear transfer function with inflection points `pts`
            # pts is List[Tuple(int_x, int_y)] and must be sorted by their x-values

            # in case pts doesn't contain edge points ((0, 0), (255, 255)).
            # note that if pts actually have edge points, this addition won't affect correctness
            pts = [(0, 0)] + pts + [(255, 255)]

            tf = [0]
            for i, j in zip(pts[:-1], pts[1:]):
                tf.pop()
                tf.extend(list(np.linspace(i[1], j[1], j[0]-i[0]+1)))
            return np.array(tf).astype(np.uint8)

        self.tf_img = applyTransferFunction(self.img, makePiecewiseLinearTF(self.coords))
        cv.imshow(self.cv_name, self.tf_img)

    def onPressKey(self, event):
        if event.key in ['q', 'Q']:
            print('[*] Quitting...')
            exit(0)
        elif event.key in ['m', 'M']:
            print('[*] Saving image...')
            self.saveImage()
        
    def saveImage(self):
        cv.imwrite(str(output_path), self.tf_img)
        
fig, ax = plt.subplots()
ax.set_title('Transfer function:\nclick to add inflection point, click on point to remove\npress "m" to save image, press "q" to quit')
line, = ax.plot([0, 255], [0, 255], 'o-', picker=True, pickradius=5)
linebuilder = TransferFunctionDrawer(line, cv.imread(str(input_path), cv.IMREAD_GRAYSCALE))
plt.show()