# linux_gpu_env.sh — sourced by the relay scripts on Linux (Oct 1 2026, 9950X bring-up).
# The harness still needs a real GL context even headless. Instead of a persistent Xvfb :99
# (software llvmpipe, ~4.5x the CPU per frame), render through SDL's offscreen EGL driver on the
# RTX 3090: no X server, no windows, no sudo. Measured Oct 1: 16 parallel instances x 3600 frames
# = 14.6 s on the 3090 vs 35.8 s on the Radeon iGPU (EGL) vs ~43 s per single instance on Xvfb.
# Fallback to the old Xvfb path: export PS2_RENDER=xvfb (expects Xvfb on :99).
if [ "$(uname)" != "Darwin" ]; then
  if [ "${PS2_RENDER:-egl}" = "xvfb" ]; then
    export DISPLAY="${DISPLAY:-:99}"
  else
    unset DISPLAY
    export SDL_VIDEODRIVER=offscreen
    export __EGL_VENDOR_LIBRARY_FILENAMES="${__EGL_VENDOR_LIBRARY_FILENAMES:-/usr/share/glvnd/egl_vendor.d/10_nvidia.json}"
  fi
fi
