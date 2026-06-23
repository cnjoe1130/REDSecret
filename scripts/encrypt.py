#!/usr/bin/env python3
"""
「舅的密语」加密引擎 v2.0 — 一句话输入 → 生成隐写情绪图
用法: python3 encrypt.py "你想说的话" --key "暗号" --style midnight_emo
"""
import sys, os, struct, hashlib, random, argparse
import numpy as np
from PIL import Image, ImageDraw, ImageFont

STEP = 8

PALETTES = [
    {"name": "midnight_emo", "bg_top": (25, 20, 60), "bg_bottom": (60, 30, 80),
     "text_color": (255, 255, 255), "accent": (180, 140, 255)},
    {"name": "gentle_pink", "bg_top": (255, 220, 220), "bg_bottom": (255, 180, 190),
     "text_color": (80, 40, 50), "accent": (220, 100, 120)},
    {"name": "cream", "bg_top": (250, 245, 235), "bg_bottom": (240, 230, 215),
     "text_color": (60, 50, 45), "accent": (180, 150, 120)},
    {"name": "ocean", "bg_top": (100, 180, 220), "bg_bottom": (60, 120, 180),
     "text_color": (255, 255, 255), "accent": (255, 200, 150)},
    {"name": "warm_orange", "bg_top": (255, 200, 150), "bg_bottom": (255, 160, 100),
     "text_color": (80, 40, 20), "accent": (200, 80, 50)},
    {"name": "dark_minimal", "bg_top": (30, 30, 35), "bg_bottom": (45, 40, 50),
     "text_color": (220, 220, 220), "accent": (120, 180, 255)},
]


def _get_font(size, bold=False):
    paths = [
        "/System/Library/Fonts/Supplemental/Songti.ttc" if not bold
        else "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
    ]
    for p in paths:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except Exception: continue
    return ImageFont.load_default()


def _create_gradient(w, h, c_top, c_bot):
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        r = y / h
        c = tuple(int(c_top[i] + (c_bot[i] - c_top[i]) * r) for i in range(3))
        for x in range(w): px[x, y] = c
    return img


def _add_noise(img, intensity=3):
    px = img.load()
    w, h = img.size
    for _ in range(w * h // 20):
        x, y = random.randint(0, w - 1), random.randint(0, h - 1)
        r, g, b = px[x, y]
        n = random.randint(-intensity, intensity)
        px[x, y] = (max(0, min(255, r+n)), max(0, min(255, g+n)), max(0, min(255, b+n)))
    return img


def _wrap_text(text, font, max_w, draw):
    lines, cur = [], ""
    for ch in text:
        if ch == "\n": lines.append(cur); cur = ""; continue
        test = cur + ch
        if draw.textbbox((0, 0), test, font=font)[2] > max_w:
            if cur: lines.append(cur)
            cur = ch
        else: cur = test
    if cur: lines.append(cur)
    return lines


def generate_image(surface_text, output_path, palette=None, size=(1080, 1440)):
    """生成小红书风格情绪图"""
    w, h = size
    if palette is None: palette = random.choice(PALETTES)
    elif isinstance(palette, str):
        palette = next((p for p in PALETTES if p["name"] == palette), random.choice(PALETTES))

    img = _create_gradient(w, h, palette["bg_top"], palette["bg_bottom"])
    draw = ImageDraw.Draw(img)

    for _ in range(random.randint(2, 5)):
        cx, cy = random.randint(0, w), random.randint(0, h)
        r = random.randint(50, 200)
        ov = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(ov).ellipse([cx-r, cy-r, cx+r, cy+r], fill=palette["accent"]+(random.randint(15,40),))
        img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
        draw = ImageDraw.Draw(img)

    img = _add_noise(img)
    draw = ImageDraw.Draw(img)

    font = _get_font(48)
    lines = _wrap_text(surface_text, font, w - 200, draw)
    total_h = len(lines) * 70
    sy = (h - total_h) // 2
    for i, line in enumerate(lines):
        bb = draw.textbbox((0, 0), line, font=font)
        lx = (w - (bb[2] - bb[0])) // 2
        draw.text((lx+2, sy+i*70+2), line, font=font, fill=(0,0,0,50))
        draw.text((lx, sy+i*70), line, font=font, fill=palette["text_color"])

    sf = _get_font(24)
    hint = "有些话，只说给懂的人听 🤫"
    hb = draw.textbbox((0, 0), hint, font=sf)
    draw.text(((w-(hb[2]-hb[0]))//2, h-100), hint, font=sf, fill=palette["accent"])
    img.save(output_path, quality=95)
    return output_path


def _bytes_to_bits(data):
    bits = []
    for byte in data:
        for i in range(7, -1, -1): bits.append((byte >> i) & 1)
    return bits


def _xor_crypt(data, key):
    kb = key.encode("utf-8")
    return bytes(d ^ kb[i % len(kb)] for i, d in enumerate(data))


def embed(image_path, secret_text, key, output_path):
    """嵌入密文到图片 R 通道 (QIM)"""
    img = Image.open(image_path).convert("RGB")
    arr = np.array(img, dtype=np.float64)

    sb = secret_text.encode("utf-8")
    payload = struct.pack("<I", len(sb)) + sb + hashlib.md5(sb).digest()[:4]
    encrypted = _xor_crypt(payload, key)
    bits = _bytes_to_bits(encrypted)

    flat = arr[:, :, 0].flatten().copy()
    for i, bit in enumerate(bits):
        if i >= len(flat): break
        val = int(flat[i])
        q = round(val / STEP)
        if (q & 1) != bit:
            v_up, v_down = (q+1)*STEP, (q-1)*STEP
            if v_up <= 255 and abs(v_up-val) <= abs(v_down-val): q += 1
            elif v_down >= 0: q -= 1
            else: q += 1
        flat[i] = max(0, min(255, q * STEP))

    arr[:, :, 0] = flat.reshape(arr[:, :, 0].shape)
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).save(output_path)
    return output_path


def verify(image_path, key):
    """验证解密"""
    img = Image.open(image_path).convert("RGB")
    flat = np.array(img, dtype=np.float64)[:, :, 0].flatten()

    hb = [round(int(flat[i])/STEP) & 1 for i in range(32)]
    hb_b = bytearray()
    for i in range(0, 32, 8):
        v = 0
        for j in range(8): v = (v << 1) | hb[i+j]
        hb_b.append(v)

    kb = key.encode("utf-8")
    if not kb: return None
    hd = bytes(hb_b[i] ^ kb[i%len(kb)] for i in range(4))
    sl = struct.unpack("<I", hd)[0]
    if sl <= 0 or sl > 10000: return None

    tb = (4 + sl + 4) * 8
    ab = [round(int(flat[i])/STEP) & 1 for i in range(min(tb, len(flat)))]
    enc = bytearray()
    for i in range(0, len(ab), 8):
        v = 0
        for j in range(8):
            if i+j < len(ab): v = (v << 1) | ab[i+j]
            else: v <<= 1
        enc.append(v)

    pl = _xor_crypt(bytes(enc), key)
    dl = struct.unpack("<I", pl[:4])[0]
    sc = pl[4:4+dl]; cs = pl[4+dl:8+dl]
    if cs != hashlib.md5(sc).digest()[:4]: return None
    return sc.decode("utf-8", errors="replace")


SURFACE_TEXTS = [
    "今天的风\n很温柔", "岁月静好\n现世安稳", "晚安\n世界",
    "慢慢来\n一切都是最好的安排", "做自己的\n太阳", "明天\n又是新的一天",
    "生活不止\n眼前的苟且",
]


def create_miyu(secret_text, key="default_key", style=None, output_dir=".", surface_text=None):
    """完整流程：生成表面图 + 嵌入密文 + 验证"""
    fname = f"miyu_{random.randint(1000,9999)}.png"
    final_path = os.path.join(output_dir, fname)
    if surface_text is None:
        surface_text = random.choice(SURFACE_TEXTS)
    tmp_path = os.path.join(output_dir, "_tmp_surface.png")

    print("🎨 生成情绪图...")
    generate_image(surface_text, tmp_path, palette=style)
    print("🔐 嵌入密文...")
    embed(tmp_path, secret_text, key, final_path)
    if os.path.exists(tmp_path): os.remove(tmp_path)

    print("✅ 验证解密...")
    decoded = verify(final_path, key)
    status = "通过" if decoded == secret_text else "失败"

    print(f"\n{'='*50}")
    print(f"📦 生成完成！")
    print(f"  图片: {final_path}")
    print(f"  表面文案: {surface_text}")
    print(f"  隐藏密文: {secret_text}")
    print(f"  解密密钥: {key}")
    print(f"  验证: {status}")
    print(f"{'='*50}")
    return final_path, surface_text


def demo():
    print("🎭 「舅的密语」Demo\n" + "="*50)
    demos = [
        ("有些夜晚，眼泪比笑容更诚实。但天亮了，我还是会笑着出门。", "深夜emo", "midnight_emo"),
        ("今天又被老板骂了，想辞职想到失眠。但是房租不会等我。", "打工人", "dark_minimal"),
        ("其实我一点都不喜欢现在的生活，可是我不知道还能怎样。", "说不出口", "gentle_pink"),
    ]
    for i, (s, label, style) in enumerate(demos):
        print(f"\n--- Demo {i+1}: {label} ---")
        create_miyu(s, key=f"暗号{label}", style=style)
    print(f"\n{'='*50}\n🎉 Demo 完成！")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="「舅的密语」加密引擎")
    parser.add_argument("text", nargs="?", help="要隐藏的真实想法")
    parser.add_argument("--key", "-k", default="default_key", help="解密密钥")
    parser.add_argument("--style", "-s", choices=[p["name"] for p in PALETTES], help="配色风格")
    parser.add_argument("--output", "-o", default=".", help="输出目录")
    parser.add_argument("--surface", "-st", help="自定义表面文案（支持\\n换行）")
    parser.add_argument("--demo", action="store_true", help="运行演示")
    args = parser.parse_args()

    if args.demo: demo()
    elif args.text: create_miyu(args.text, key=args.key, style=args.style, output_dir=args.output, surface_text=args.surface)
    else: parser.print_help()
