#!/usr/bin/env python3
"""
零宽字符隐写引擎 — 微信朋友圈专用
原理: 把密文编码为零宽字符，嵌入表面文案中
优势: 不依赖像素，微信压缩/截图都不影响
用法:
  加密: python3 zw_stego.py encrypt "表面文案" "密文" [--key KEY]
  解密: python3 zw_stego.py decrypt "含零宽的文案" [--key KEY]
  信息: python3 zw_stego.py info "含零宽的文案"
"""
import sys
import struct
import hashlib

# 零宽字符编码表
ZW_ZERO = '\u200b'      # zero-width space = bit 0
ZW_ONE  = '\u200c'      # zero-width non-joiner = bit 1
ZW_SEP  = '\u200d'      # zero-width joiner = byte分隔符
ZW_START = '\ufeff'     # zero-width no-break space = 起始标记
ZW_END   = '\u2060'     # word joiner = 结束标记

def _text_to_zw(text, key=""):
    """文本 -> 零宽字符序列"""
    data = text.encode('utf-8')
    if key:
        kb = key.encode('utf-8')
        data = bytes(data[i] ^ kb[i % len(kb)] for i in range(len(data)))
    payload = struct.pack('<H', len(data)) + data + hashlib.md5(data).digest()[:4]
    result = ZW_START
    for byte in payload:
        for i in range(7, -1, -1):
            bit = (byte >> i) & 1
            result += ZW_ONE if bit else ZW_ZERO
        result += ZW_SEP
    result += ZW_END
    return result

def _zw_to_text(zw_str, key=""):
    """零宽字符序列 -> 文本"""
    zw_only = ''.join(c for c in zw_str if c in (ZW_ZERO, ZW_ONE, ZW_SEP, ZW_START, ZW_END))
    if not zw_only.startswith(ZW_START):
        return None
    content = zw_only[1:]
    if content.endswith(ZW_END):
        content = content[:-1]
    bytes_list = []
    current_bits = []
    for c in content:
        if c == ZW_ZERO:
            current_bits.append(0)
        elif c == ZW_ONE:
            current_bits.append(1)
        elif c == ZW_SEP:
            if len(current_bits) == 8:
                b = 0
                for bit in current_bits:
                    b = (b << 1) | bit
                bytes_list.append(b)
            current_bits = []
    if len(current_bits) == 8:
        b = 0
        for bit in current_bits:
            b = (b << 1) | bit
        bytes_list.append(b)
    if len(bytes_list) < 6:
        return None
    raw = bytes(bytes_list)
    dl = struct.unpack('<H', raw[:2])[0]
    data = raw[2:2+dl]
    checksum = raw[2+dl:6+dl]
    if checksum != hashlib.md5(data).digest()[:4]:
        return None
    if key:
        kb = key.encode('utf-8')
        data = bytes(data[i] ^ kb[i % len(kb)] for i in range(len(data)))
    return data.decode('utf-8', errors='replace')

def encrypt(surface_text, secret_text, key=""):
    """加密: 将密文嵌入表面文案"""
    zw_payload = _text_to_zw(secret_text, key)
    return surface_text + zw_payload

def decrypt(text_with_zw, key=""):
    """解密: 从含零宽字符的文案中提取密文"""
    return _zw_to_text(text_with_zw, key)

def info(text_with_zw):
    """显示零宽字符信息"""
    zw_count = sum(1 for c in text_with_zw if c in (ZW_ZERO, ZW_ONE, ZW_SEP, ZW_START, ZW_END))
    visible_count = len(text_with_zw) - zw_count
    print(f"📊 文案信息:")
    print(f"   可见字符: {visible_count}")
    print(f"   零宽字符: {zw_count}")
    print(f"   总字符数: {len(text_with_zw)}")
    print(f"   隐藏容量: ~{zw_count // 10} 字节 (~{zw_count // 30} 个中文字)")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法:")
        print('  加密: python3 zw_stego.py encrypt "表面文案" "密文" [--key KEY]')
        print('  解密: python3 zw_stego.py decrypt "含零宽的文案" [--key KEY]')
        print('  信息: python3 zw_stego.py info "含零宽的文案"')
        sys.exit(1)
    mode = sys.argv[1]
    if mode == "encrypt":
        surface = sys.argv[2] if len(sys.argv) > 2 else ""
        secret = sys.argv[3] if len(sys.argv) > 3 else ""
        key = ""
        i = 4
        while i < len(sys.argv):
            if sys.argv[i] == "--key": key = sys.argv[i+1]; i += 2
            else: i += 1
        result = encrypt(surface, secret, key)
        print(f"✅ 加密完成\n")
        print(f"📤 复制以下文案发朋友圈:\n")
        print(result)
        print(f"\n---")
        info(result)
        print(f"\n🔑 解密密钥: {key or '(无)'}")
    elif mode == "decrypt":
        text = sys.argv[2] if len(sys.argv) > 2 else ""
        key = ""
        i = 3
        while i < len(sys.argv):
            if sys.argv[i] == "--key": key = sys.argv[i+1]; i += 2
            else: i += 1
        result = decrypt(text, key)
        if result:
            print(f"🤫 密语解密成功:\n\n> {result}")
        else:
            print("❌ 未找到隐写内容，或密钥不正确")
    elif mode == "info":
        text = sys.argv[2] if len(sys.argv) > 2 else ""
        info(text)
