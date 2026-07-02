"""
Generate two test logos (PNG) with slightly different widths (~30% variance)
to validate the logo-fit logic in the renderer.

Output:
  /home/z/my-project/assets/logos/acme.png        (wider)
  /home/z/my-project/assets/logos/eurolab.png     (narrower)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Use PIL if available, else use a tiny pure-Python PNG writer
try:
    from PIL import Image, ImageDraw, ImageFont

    def make_logo(path: Path, w: int, h: int, label: str, bg: tuple, fg: tuple) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        img = Image.new("RGB", (w, h), bg)
        draw = ImageDraw.Draw(img)
        # Try a built-in font
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
        except Exception:
            font = ImageFont.load_default()
        # Center the label
        bbox = draw.textbbox((0, 0), label, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text(((w - tw) / 2, (h - th) / 2 - 2), label, fill=fg, font=font)
        img.save(path)
        print(f"Wrote {path} ({w}x{h})")

except ImportError:
    # No PIL - write minimal PNG via struct
    import struct, zlib

    def make_png(path: Path, w: int, h: int, color: tuple) -> None:
        def chunk(typ, data):
            c = typ + data
            return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xffffffff)
        raw = b""
        for _ in range(h):
            raw += b"\x00" + bytes(color) * w
        png = b"\x89PNG\r\n\x1a\n"
        png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
        png += chunk(b"IDAT", zlib.compress(raw))
        png += chunk(b"IEND", b"")
        path.write_bytes(png)
        print(f"Wrote {path} ({w}x{h}) [no PIL - flat color only]")


if __name__ == "__main__":
    out = Path("/home/z/my-project/assets/logos")
    make_logo(out / "acme.png", 180, 50, "ACME CHEM", (15, 42, 68), (255, 255, 255))
    make_logo(out / "eurolab.png", 140, 50, "EuroLab", (0, 80, 120), (255, 255, 255))
