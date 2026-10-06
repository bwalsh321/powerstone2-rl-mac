"""montage.py out.png in1.png in2.png ... -- flip vertically, label, grid 4 wide."""
import sys, os
from PIL import Image, ImageDraw, ImageOps
out, ins = sys.argv[1], sys.argv[2:]
ims = []
for p in ins:
    im = Image.open(p).convert("RGB"); im = ImageOps.flip(im) if os.environ.get("FLIP") else im; im = im.resize((320, 240))
    d = ImageDraw.Draw(im); d.rectangle([0, 0, 320, 14], fill=(0, 0, 0))
    d.text((2, 1), os.path.basename(p), fill=(255, 255, 0)); ims.append(im)
cols = min(4, len(ims)); rows = (len(ims) + cols - 1) // cols
M = Image.new("RGB", (320 * cols, 240 * rows))
for i, im in enumerate(ims): M.paste(im, ((i % cols) * 320, (i // cols) * 240))
M.save(out)
