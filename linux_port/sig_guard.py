"""keep_native_fault_handlers — Oct 1 2026, 9950X bring-up.

On Linux, flycast's SH4 dynarec takes deliberate SIGSEGV/SIGBUS faults and resolves them in its own
signal handler (fast memory access). pygame.init() installs pygame's "parachute" over those
handlers, so after it the dynarec's expected faults kill the process (bm_GetCodeByVAddr SIGSEGV,
or SIGILL). macOS flycast uses Mach exceptions, which is why the Mac never saw this. Wrap any
pygame.init() that runs after an emulator boots:

    with keep_native_fault_handlers():
        pygame.init()
"""
import ctypes
import contextlib
import signal
import sys

_SIGS = (signal.SIGSEGV, signal.SIGBUS, signal.SIGILL, signal.SIGFPE)


@contextlib.contextmanager
def keep_native_fault_handlers():
    if not sys.platform.startswith("linux"):
        yield
        return
    libc = ctypes.CDLL(None, use_errno=True)
    saved = {}
    for s in _SIGS:
        buf = ctypes.create_string_buffer(512)          # opaque struct sigaction (152 B on x86_64 glibc)
        if libc.sigaction(int(s), None, buf) == 0:
            saved[s] = buf
    try:
        yield
    finally:
        for s, buf in saved.items():
            libc.sigaction(int(s), buf, None)
