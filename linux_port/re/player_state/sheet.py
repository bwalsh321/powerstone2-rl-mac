import sys, glob
from PIL import Image, ImageDraw
fs = sorted(glob.glob(sys.argv[1])); cols = int(sys.argv[3]) if len(sys.argv) > 3 else 5
ims = [Image.open(f).resize((320, 240)) for f in fs]
rows = (len(ims) + cols - 1)//cols
W = Image.new("RGB", (320*cols, 240*rows))
for i, (f, im) in enumerate(zip(fs, ims)):
    ImageDraw.Draw(im).text((4, 4), f.split("/")[-1], fill=(255, 255, 0))
    W.paste(im, ((i % cols)*320, (i//cols)*240))
W.save(sys.argv[2])
