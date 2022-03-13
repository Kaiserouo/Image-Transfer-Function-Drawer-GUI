# transfer function drawer. you can draw transfer function & the change will apply immediately
# click on function graph to add inflection point
# click on point to remove them
# ref. https://matplotlib.org/stable/users/explain/event_handling.html

import argparse
import cv2 as cv
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider

description = """
    A GUI to draw & apply a piecewise linear transfer function to an image.
    
    Click on transfer function to add an inflection point.
    CLick on point to remove that inflection point.

    Adjust the bottom slider to resize image.
    Used for when image is too large, etc. But the saved image will be original sized.

    The inflection points will be printed on change to transfer function,
    and you can store it and import by option `--inflect`

    Press "m" to save image to output path (set in `--output`).
    Press "q" to exit the program.
"""

parser = argparse.ArgumentParser(description=description, formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument("-i", "--input", required=True, 
                    help="Image to apply transfer function")
parser.add_argument("-o", "--output", 
                    help="Output path of saved image,\n"
                         "if it is not set, then will not be able to save.")
parser.add_argument("--inflect", 
                    help="Load inflection points from before. e.g. \"[(0, 0), (128, 32), (255, 255)]\".\n"
                         "Must all be contained in a single string, with format like above.\n"
                         "You can directly import it if you have the previous inflection point output of program.")
parser.add_argument("-g", "--grey", action='store_true',
                    help="Use grey image (i.e. read by cv2.IMREAD_GRAYSCALE)\n"
                         "Default to color version (i.e. read by cv2.IMREAD_COLOR)")
args = parser.parse_args()

input_path = Path(args.input)
output_path = Path(args.output) if args.output is not None else None

# main class for dealing with inputs
class TransferFunctionDrawer:
    def __init__(self, line, img, apply_tf_f, resize_img_f, axsize):
        self.line = line
        self.coords = [(x, y) for x, y in zip(line.get_xdata(), line.get_ydata())]
        self.apply_tf_f = apply_tf_f
        self.resize_img_f = resize_img_f

        self.cid_click = line.figure.canvas.mpl_connect('button_press_event', self.onclick)
        self.cid_pick = line.figure.canvas.mpl_connect('pick_event', self.onpick)
        self.cid_press = line.figure.canvas.mpl_connect('key_press_event', self.onPressKey)

        self.size_slider = Slider(
            ax=axsize,
            label='Size factor\n(only for showing)',
            valmin=0.1,
            valmax=3,
            valinit=1,
        )
        self.size_slider.on_changed(self.onSizeChange)

        # for picking: since when picking, `button_press_event` will also be raised...
        self.just_picked = False

        self.cv_name = 'Image'
        self.cv_ori_name = 'OriginalImage'
        self.tf_img = img       # the transferred resized image
        self.img = img          # the resized image
        self.ori_img = img      # the actual image, with original size
        cv.namedWindow(self.cv_name)
        cv.namedWindow(self.cv_ori_name)
        cv.imshow(self.cv_name, self.tf_img)
        cv.imshow(self.cv_ori_name, self.img)

        # since may give inflection point at start, must process image at beginning
        self.updateImage()
        self.printCoords()

    def onSizeChange(self, factor):
        self.tf_img = self.resize_img_f(self.ori_img, factor)
        self.img = self.resize_img_f(self.ori_img, factor)
        cv.imshow(self.cv_ori_name, self.img)
        self.updateImage()

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
        # which is a somewhat undefined behavior since their y-value are also different...
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
    
    def applyTransferFunction(self, img):
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

        # uses self.apply_tf to get a new image, by giving transfer function
        return self.apply_tf_f(img, makePiecewiseLinearTF(self.coords))
        
    def updateImage(self):
        self.tf_img = self.applyTransferFunction(self.img)
        cv.imshow(self.cv_name, self.tf_img)

    def onPressKey(self, event):
        if event.key in ['q', 'Q']:
            print('[*] Quitting...')
            exit(0)
        elif event.key in ['m', 'M']:
            print('[*] Saving image...')
            self.saveImage()
        
    def saveImage(self):
        if output_path is None:
            print('[x] Cannot save image: did not specify output path.')
        else:
            # note that resizing is just a visual effect when using this program
            # the saved image won't be resized
            cv.imwrite(str(output_path), self.applyTransferFunction(self.ori_img))

class GreyTransferFunctionApplier:
    def __call__(self, img, tf_fn):
        # transfer function (tf_fn) as form of array of size 256
        # also this is way faster than 2 for-iterations
        return cv.LUT(img, tf_fn)

class BGRTransferFunctionApplier:
    def __call__(self, img, tf_fn):
        # transfer function (tf_fn) as form of array of size 256
        # there are some approach for this
        return self.HLSConversion(img, tf_fn)

    def directLUT(self, img, tf_fn):
        # will do LUT on 3 channels individually, and that may not be the best approach...
        # but it looked good enough, and it is very fast
        return cv.LUT(img, tf_fn)
    
    def directMultBrightness(self, img, tf_fn):
        # i.e. direct multiply each pixel's RGB value
        # according to how much bright difference there is.
        # it looks good, but theoretically direct multiplication might change hue...
        img = img.copy()
        grey_img = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
        after_grey_img = cv.LUT(grey_img, tf_fn)
        img = img.astype(float)
        zero_mask = (grey_img == 0)
        after_grey_img[zero_mask] = 1 # to avoid 0 divided by 0
        grey_img[zero_mask] = 1 # to avoid 0 divided by 0
        img = img * (after_grey_img / grey_img)[:,:,np.newaxis]
        img[zero_mask, :] = 0
        return np.clip(img, 0, 255).astype(np.uint8)

    def HLSConversion(self, img, tf_fn):
        # convert to HLS, adjust luminance by LUT, and convert back
        # seems total legit and fast as heck
        img = cv.cvtColor(img, cv.COLOR_BGR2HLS)
        img[:, :, 1] = cv.LUT(img[:, :, 1], tf_fn)
        return cv.cvtColor(img, cv.COLOR_HLS2BGR)
        
def loadInflectionPoints() -> tuple[list[tuple[int, int]]]:
    # returns e.g. [[(0, 255)], [(0, 255)]], which is xs & ys.
    def parsePts(s):
        import json
        return json.loads(s.replace('(', '[').replace(')', ']'))

    if args.inflect is None:
        return ([0, 255], [0, 255])
    else:
        pts = parsePts(args.inflect)
        return ([x for x,y in pts], [y for x,y in pts])


if __name__ == '__main__':
    # check if image valid
    if not Path(args.input).is_file() or cv.imread(str(input_path), cv.IMREAD_GRAYSCALE) is None:
        print('Given input path is not a valid image.')
        exit(1)

    fig, ax = plt.subplots()
    ax.set_title('Transfer function:\nclick to add inflection point, click on point to remove\npress "m" to save image, press "q" to quit')
    line, = ax.plot(*loadInflectionPoints(), 'o-', picker=True, pickradius=5)

    # make axes for resizing
    # the slider will be built inside linebuilder
    plt.subplots_adjust(bottom=0.25)
    axsize = plt.axes([0.25, 0.1, 0.65, 0.03])

    if args.grey:
        resize_img_f = lambda img, factor: cv.resize(
            img, tuple((np.array(img.shape).astype(float) * factor).astype(int))
        )
        linebuilder = TransferFunctionDrawer(
            line, cv.imread(str(input_path), cv.IMREAD_GRAYSCALE), GreyTransferFunctionApplier(),
            resize_img_f, axsize
        )
    else:
        resize_img_f = lambda img, factor: cv.resize(
            img, tuple((np.array(img.shape)[::-1][1:].astype(float) * factor).astype(int))
        )
        linebuilder = TransferFunctionDrawer(
            line, cv.imread(str(input_path), cv.IMREAD_COLOR), BGRTransferFunctionApplier(),
            resize_img_f, axsize
        )
    
    plt.show()