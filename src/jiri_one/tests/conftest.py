import struct

import pytest


def s15(x):
    return struct.pack(">i", round(x * 65536))


@pytest.fixture
def cmyk_profile():
    """A tiny ICC profile for CMYK in which cyan prints red, so a picture converted without it
    stays cyan: white paper, cyan as L*a*b* 54/81/70, every other ink black."""
    clut = b""
    for corner in range(16):  # C, M, Y, K at 0 or 100 %, C changing slowest
        clut += bytes((255, 128, 128) if corner == 0 else (138, 209, 198) if corner == 8 else (0, 128, 128))
    same = bytes(range(256))
    a2b0 = b"mft1" + bytes(4) + bytes((4, 3, 2, 0)) + b"".join(s15(v) for v in (1, 0, 0, 0, 1, 0, 0, 0, 1))
    a2b0 += same * 4 + clut + same * 3
    tags = [(b"wtpt", b"XYZ " + bytes(4) + s15(0.9642) + s15(1.0) + s15(0.8249)), (b"A2B0", a2b0)]
    start = 128 + 4 + 12 * len(tags)
    table = data = b""
    for signature, body in tags:
        table += signature + struct.pack(">II", start + len(data), len(body))
        data += body + bytes(-len(body) % 4)
    header = struct.pack(">I", start + len(data)) + bytes(4) + struct.pack(">I", 0x02100000)
    header += b"prtrCMYKLab " + bytes(12) + b"acsp" + bytes(28) + s15(0.9642) + s15(1.0) + s15(0.8249) + bytes(48)
    return header + struct.pack(">I", len(tags)) + table + data
