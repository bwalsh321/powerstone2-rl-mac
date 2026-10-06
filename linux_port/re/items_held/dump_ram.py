"""Dump full 16 MiB RAM after loading a state + N frames -> ram_<tag>.bin"""
import sys
from common import *
br = boot(); load(br, sys.argv[1]); br.run_frames(int(sys.argv[2]))
open(os.path.join(HERE, sys.argv[3]), "wb").write(bytes(br.emu.get_ram()))
print("ok")
