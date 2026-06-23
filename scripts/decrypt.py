#!/usr/bin/env python3
"""舅的密语 - 解密引擎 v1.2 (纯PIL版,无numpy依赖)
算法: QIM 空间域隐写, STEP=8, round() 提取
优化: 移除numpy依赖,纯PIL实现,更轻量
新增: 自动检测文件格式与扩展名是否匹配,支持 --fix 自动改名
用法: python3 decrypt.py <图片路径> [密钥] [--fix]
"""
import sys
import os
import struct
import hashlib
from PIL import Image

STEP = 8
_EXT_MAP = {".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG", ".webp": "WEBP", ".bmp": "BMP"}


def _fix_ext(path):
    """检测扩展名是否与实际格式匹配, --fix 模式下自动改名"""
    img = Image.open(path)
    real_fmt = img.format
    ext = os.path.splitext(path)[1].lower()
    img.close()

    if _EXT_MAP.get(ext) == real_fmt:
        return path  # 匹配, 无需处理

    expected_ext = f".{real_fmt.lower()}"
    new_path = os.path.splitext(path)[0] + expected_ext
    print(f"⚠️  格式不匹配: 扩展名={ext}, 实际={real_fmt}")

    if "--fix" in sys.argv:
        if os.path.exists(new_path) and os.path.abspath(new_path) != os.path.abspath(path):
            base = os.path.splitext(new_path)[0]
            new_path = f"{base}_fixed{expected_ext}"
        os.rename(path, new_path)
        print(f"   ✅ 已改名: {os.path.basename(new_path)}")
        return new_path
    else:
        print(f"   💡 数据完好, 可直接解密。加 --fix 可自动改名为: {os.path.basename(new_path)}")
        return path


def _b(bits):
    r = bytearray()
    for i in range(0, len(bits) - 7, 8):
        v = 0
        for j in range(8):
            if i + j < len(bits): v = (v << 1) | bits[i + j]
            else: v <<= 1
        r.append(v)
    return bytes(r)


def _c(data_bytes, key):
    kb = key.encode("utf-8")
    if not kb: return data_bytes
    r = bytearray(len(data_bytes))
    for i in range(len(data_bytes)): r[i] = data_bytes[i] ^ kb[i % len(kb)]
    return bytes(r)


def miyu_decode(path, key=""):
    """解密图片中的隐写内容 (纯PIL实现)"""
    try:
        img = Image.open(path).convert("RGB")
        pixels = list(img.getdata())

        hb = [round(pixels[i][0] / STEP) & 1 for i in range(32)]
        hb_bytes = _b(hb)
        kb = key.encode("utf-8")
        if not kb:
            hd = hb_bytes
        else:
            hd = bytes(hb_bytes[i] ^ kb[i % len(kb)] for i in range(4))
        sl = struct.unpack("<I", hd)[0]

        print(f"📏 内容长度: {sl} 字节")
        if sl <= 0 or sl > 10000: return None

        tb = (4 + sl + 4) * 8
        ab = [round(pixels[i][0] / STEP) & 1 for i in range(min(tb, len(pixels)))]
        enc = _b(ab[:tb])
        pl = _c(enc, key)

        dl = struct.unpack("<I", pl[:4])[0]
        sc = pl[4:4 + dl]
        cs = pl[4 + dl:8 + dl]

        if cs != hashlib.md5(sc).digest()[:4]:
            print("❌ MD5 校验失败")
            return None
        return sc.decode("utf-8", errors="replace")

    except Exception as e:
        print(f"❌ 错误: {e}")
        return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 decrypt.py <image> [key] [--fix]")
        print("  --fix  自动修正扩展名 (如 .jpeg→.png)")
        sys.exit(1)

    path = sys.argv[1]
    key = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("-") else ""

    print(f"🔍 解密图片: {path}")
    print(f"🔑 密钥: {key if key else '(空)'}\n")

    # 自动检测格式匹配
    path = _fix_ext(path)

    result = miyu_decode(path, key)

    if result:
        print(f"🤫 密语解密成功:\n\n> {result}")
    else:
        print("NO_SECRET")
