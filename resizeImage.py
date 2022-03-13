# since image is often too big to handle, this program is to realize `convert img.png --size`
# but instead of defining size, I simply scale by factor
# I don't know why I spent so much effort on this

import cv2 as cv
import numpy as np
import argparse
from pathlib import Path

description = """
    Resize image.
"""


parser = argparse.ArgumentParser(description=description, formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument("-i", "--input", help="Image to resize", required=True)
parser.add_argument("-o", "--output", help="Output path of saved image", required=True)
parser.add_argument("-f", "--factor", help="Factor of resizing", required=True)
args = parser.parse_args()

input_path = Path(args.input)
output_path = Path(args.output)

img = cv.imread(str(input_path), cv.IMREAD_COLOR)

def resizeImage(n):
    return cv.resize(
        img, tuple((np.array(img.shape)[::-1][1:].astype(float) * n).astype(int))
    )

# def showImage(n):
#     cv.imshow(WINDOW_NAME, resizeImage(n))
    
def saveImage(n):
    cv.imwrite(str(output_path), resizeImage(n))


if __name__ == '__main__':
    saveImage(float(args.factor))