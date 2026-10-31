#!/usr/bin/env python3
"""Generate icon.ico + icon.png for the yt-dlp GUI (stdlib only, no PIL).

Drawing: YouTube-red rounded square with a white play triangle and a small
download arrow underneath — matches the in-app logo and dark/red theme.
Rendered with 4x supersampling so the rounded corners stay smooth at 16px.
"""
import os
import struct
import zlib

RED = (255, 0, 51)          # YouTube red used by the app theme
RED_SHADE = (196, 0, 40)    # bottom-right falloff for a subtle gloss
WHITE = (255, 255, 255)
SS = 4                      # supersampling factor


def _inside_round_rect(x, y, N, rad):
    if x < rad and y < rad:
        dx, dy = rad - x, rad - y
    elif x >= N - rad and y < rad:
        dx, dy = x - (N - rad), rad - y
    elif x < rad and y >= N - rad:
        dx, dy = rad - x, y - (N - rad)
    elif x >= N - rad and y >= N - rad:
        dx, dy = x - (N - rad), y - (N - rad)
    else:
        return True
    return dx * dx + dy * dy <= rad * rad


def _inside_triangle(x, y, N):
    """Play triangle, pointing right, centred in the square."""
    cx, cy = N * 0.495, N * 0.46
    half_h = N * 0.195
    half_w = N * 0.150
    if abs(y - cy) > half_h:
        return False
    t = (x - (cx - half_w)) / (half_w * 2)
    if t < 0 or t > 1:
        return False
    return abs(y - cy) <= half_h * (1 - t)


def _inside_arrow(x, y, N):
    """Small download arrow in the lower-right corner."""
    cx = N * 0.775
    # vertical stem
    if N * 0.615 <= y <= N * 0.755 and abs(x - cx) <= N * 0.026:
        return True
    # arrow head
    if N * 0.745 <= y <= N * 0.875:
        t = (y - N * 0.745) / (N * 0.875 - N * 0.745)
        if abs(x - cx) <= N * 0.085 * (1 - t):
            return True
    return False


def make_pixels(N):
    """Return N x N RGBA pixels (list of rows), supersampled for smooth edges."""
    M = N * SS
    rad = 0.235 * M
    # --- render at M x M, then box-downsample to N x N
    hi = [[(0, 0, 0, 0)] * M for _ in range(M)]
    for y in range(M):
        for x in range(M):
            if not _inside_round_rect(x + 0.5, y + 0.5, M, rad):
                continue
            # vertical gloss: lighter at the top, deeper red at the bottom
            v = (y + 0.5) / M
            base = tuple(int(RED[i] + (RED_SHADE[i] - RED[i]) * (v ** 1.6))
                         for i in range(3))
            if _inside_triangle(x + 0.5, y + 0.5, M):
                px = WHITE
            elif _inside_arrow(x + 0.5, y + 0.5, M):
                px = WHITE
            else:
                px = base
            hi[y][x] = px + (255,)

    out = []
    for y in range(N):
        row = []
        for x in range(N):
            r = g = b = a = 0
            for sy in range(SS):
                for sx in range(SS):
                    pr, pg, pb, pa = hi[y * SS + sy][x * SS + sx]
                    # premultiply so transparent pixels don't bleed dark fringes
                    r += pr * pa
                    g += pg * pa
                    b += pb * pa
                    a += pa
            n = SS * SS
            if a == 0:
                row.append((0, 0, 0, 0))
            else:
                row.append((r // a, g // a, b // a, a // n))
        out.append(row)
    return out


def _bmp32(px, N):
    rows = b""
    for y in range(N - 1, -1, -1):  # bottom-up
        for x in range(N):
            r, g, b, a = px[y][x]
            rows += bytes((b, g, r, a))
    androw = b"\x00" * (((N + 31) // 32) * 4)
    andmask = androw * N
    header = struct.pack("<IiiIIIIiiII", 40, N * 2, N, 1, 32, 0,
                         len(rows) + len(andmask), 0, 0, 0, 0)
    return header + rows + andmask


def write_ico(path, sizes):
    images = [_bmp32(make_pixels(N), N) for N in sizes]
    out = struct.pack("<HHH", 0, 1, len(sizes))
    offset = 6 + 16 * len(sizes)
    for N, data in zip(sizes, images):
        w = 0 if N >= 256 else N
        out += struct.pack("<BBBBHHII", w, w, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
    with open(path, "wb") as f:
        f.write(out + b"".join(images))


def _png_chunk(tag, data):
    return (struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


def write_png(path, N):
    px = make_pixels(N)
    raw = b"".join(b"\x00" + b"".join(bytes(p) for p in row) for row in px)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n"
                + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", N, N, 8, 6, 0, 0, 0))
                + _png_chunk(b"IDAT", zlib.compress(raw, 9))
                + _png_chunk(b"IEND", b""))


if __name__ == "__main__":
    out = os.path.dirname(os.path.abspath(__file__))
    write_ico(os.path.join(out, "icon.ico"), [16, 24, 32, 48, 64, 128, 256])
    write_png(os.path.join(out, "icon.png"), 256)
    print("wrote", os.path.join(out, "icon.ico"), "and", os.path.join(out, "icon.png"))
