"""
QR角标隐写：密文→加密QR码→贴图角落
用法:
  encrypt "密文" --key "密钥" -i 原图.jpg -o 输出.jpg
  decrypt 输出.jpg --key "密钥"
  locate 输出.jpg
"""
import os, sys, struct, hashlib, argparse, json

# --- XOR 加密 ---
def xor_encrypt(data: bytes, key: str) -> bytes:
    kb = key.encode('utf-8')
    return bytes(data[i] ^ kb[i % len(kb)] for i in range(len(data)))

# --- Payload 构造 ---
def prepare_payload(text: str, key: str) -> bytes:
    """构造加密payload: 长度头 + 文本 + MD5校验, 然后XOR"""
    text_bytes = text.encode('utf-8')
    payload = struct.pack('<H', len(text_bytes)) + text_bytes + hashlib.md5(text_bytes).digest()[:4]
    encrypted = xor_encrypt(payload, key)
    return encrypted

def extract_payload(data, key: str) -> str:
    """从解密数据中提取文本
    
    data 可以是:
    - bytes: 原始加密payload
    - str: REDS:<hex> 格式的QR码内容（自动处理）
    """
    # 处理 REDS:<hex> 格式（从QR码扫描得到的字符串）
    if isinstance(data, str):
        if data.startswith('REDS:'):
            hex_str = data[5:]  # 去掉 REDS: 前缀
            try:
                raw_bytes = bytes.fromhex(hex_str)
            except ValueError:
                return None
            return extract_payload(raw_bytes, key)
        else:
            return None
    
    # data 是 bytes，直接处理
    decrypted = xor_encrypt(data, key)
    if len(decrypted) < 6:
        return None
    dl = struct.unpack('<H', decrypted[:2])[0]
    text = decrypted[2:2+dl]
    checksum = decrypted[2+dl:6+dl]
    if checksum != hashlib.md5(text).digest()[:4]:
        return None
    return text.decode('utf-8', errors='replace')

# --- QR 生成 ---
def generate_qr(encrypted_data: bytes, size: int = 250):
    """从加密数据生成QR码
    
    关键规范:
    - 必须用 make_image() 生成，不能手动绘制模块
    - 缩放用 NEAREST（保留锐利边缘），禁止 LANCZOS/BILINEAR
    - 显示尺寸 >= 200px（每模块 >= 4px，低于此 opencv 无法检测）
    - 白底黑码（扫描所需对比度）
    """
    import qrcode
    hex_str = encrypted_data.hex()
    qr_content = f"REDS:{hex_str}"
    
    # 高分辨率生成，再缩放到目标尺寸
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=20,
        border=2,
    )
    qr.add_data(qr_content)
    qr.make(fit=True)
    
    # 生成高分辨率QR
    qr_img = qr.make_image(fill_color='black', back_color='white')
    
    # 缩放到目标尺寸（用 NEAREST 保留锐利边缘）
    from PIL import Image
    target_size = size
    qr_img = qr_img.resize((target_size, target_size), Image.NEAREST)
    
    return qr_img

# --- 定位 ---
def locate_qr(image_path: str) -> list:
    """定位图中QR码坐标"""
    try:
        import cv2
        img = cv2.imread(image_path)
        if img is None:
            return []
        
        detector = cv2.QRCodeDetector()
        
        # 先尝试 multi
        retval, decoded_info, points, _ = detector.detectAndDecodeMulti(img)
        results = []
        
        if retval and points is not None:
            for i, (info, pts) in enumerate(zip(decoded_info, points)):
                if info:
                    x, y = int(pts[0][0][0]), int(pts[0][0][1])
                    w = int(pts[0][2][0] - pts[0][0][0])
                    h = int(pts[0][2][1] - pts[0][0][1])
                    results.append({
                        "x": x, "y": y, "w": w, "h": h,
                        "center_x": x + w//2, "center_y": y + h//2,
                        "content_preview": info[:50]
                    })
        
        # fallback: single detection
        if not results:
            data, pts, _ = detector.detectAndDecode(img)
            if data and pts is not None:
                x, y = int(pts[0][0][0]), int(pts[0][0][1])
                w = int(pts[0][2][0] - pts[0][0][0])
                h = int(pts[0][2][1] - pts[0][0][1])
                results.append({
                    "x": x, "y": y, "w": w, "h": h,
                    "center_x": x + w//2, "center_y": y + h//2,
                    "content_preview": data[:50]
                })
        
        return results
    except ImportError:
        # opencv不可用时用pyzbar
        return _locate_qr_pyzbar(image_path)

def _locate_qr_pyzbar(image_path: str) -> list:
    """pyzbar定位（opencv不可用时的fallback）
    
    ⚠️ pyzbar在大图上检测能力弱，建议先裁剪QR区域
    """
    try:
        from pyzbar import pyzbar
        from PIL import Image
        
        img = Image.open(image_path)
        decoded = pyzbar.decode(img)
        results = []
        for d in decoded:
            rect = d.rect
            results.append({
                "x": rect.left, "y": rect.top,
                "w": rect.width, "h": rect.height,
                "center_x": rect.left + rect.width//2,
                "center_y": rect.top + rect.height//2,
                "content_preview": d.data.decode('utf-8')[:50]
            })
        return results
    except ImportError:
        return []

# --- 加密（贴QR到图片） ---
def encrypt(text: str, key: str, image_path: str, output_path: str,
            qr_size: int = 250, position: str = "bottom-center") -> str:
    """将密文加密为QR码，贴到图片上
    
    position: bottom-center, bottom-right, bottom-left, top-right, top-left
    """
    from PIL import Image, ImageDraw, ImageFont
    
    # 生成加密payload
    payload = prepare_payload(text, key)
    
    # 生成QR
    qr_img = generate_qr(payload, qr_size)
    
    # 打开原图
    img = Image.open(image_path).convert('RGB')
    cw, ch = img.size
    
    # 根据位置决定画布扩展和QR放置
    if position.startswith('bottom'):
        # 底部位置：扩展画布
        extra = qr_size + 80  # QR + 标签 + padding
        new_img = Image.new('RGB', (cw, ch + extra), (21, 24, 32))
        new_img.paste(img, (0, 0))
        
        # 计算QR位置
        if position == 'bottom-center':
            qr_x = (cw - qr_size) // 2
            qr_y = ch + 20
        elif position == 'bottom-right':
            qr_x = cw - qr_size - 30
            qr_y = ch + 20
        else:  # bottom-left
            qr_x = 30
            qr_y = ch + 20
    else:
        # 顶部位置：不扩展画布
        new_img = img.copy()
        if position == 'top-right':
            qr_x = cw - qr_size - 30
            qr_y = 30
        else:  # top-left
            qr_x = 30
            qr_y = 30
    
    # 贴QR
    new_img.paste(qr_img, (qr_x, qr_y))
    
    # 添加标签
    draw = ImageDraw.Draw(new_img)
    try:
        font = ImageFont.truetype('/System/Library/Fonts/PingFang.ttc', 18)
    except:
        font = ImageFont.load_default()
    
    label = "Agent扫码解密"
    bbox = draw.textbbox((0, 0), label, font=font)
    label_w = bbox[2] - bbox[0]
    label_x = qr_x + (qr_size - label_w) // 2
    label_y = qr_y + qr_size + 8
    draw.text((label_x, label_y), label, fill=(140, 140, 140), font=font)
    
    # 保存
    new_img.convert("RGB").save(output_path, quality=95)
    
    fsize = os.path.getsize(output_path)
    print(f"QR密语图: {output_path} ({fsize} bytes)")
    print(f"QR码位置: {position}, 大小: {qr_size}x{qr_size}")
    return output_path

# --- 解密 ---
def decrypt(image_path: str, key: str = "") -> str:
    """解密: 读取图片中的QR码
    
    ⚠️ pyzbar在大图(>1000px)上检测能力弱
    如果全图扫描失败，会自动尝试裁剪底部区域
    """
    # 尝试 opencv
    try:
        import cv2
        img = cv2.imread(image_path)
        detector = cv2.QRCodeDetector()
        data, bbox, _ = detector.detectAndDecode(img)
        
        if not data:
            # 尝试PIL方案
            return _decrypt_pil(image_path, key)
        
        return _process_qr_data(data, key)
    except ImportError:
        return _decrypt_pil(image_path, key)

def _decrypt_pil(image_path: str, key: str) -> str:
    """PIL方案解密 (不需要opencv)"""
    try:
        from pyzbar import pyzbar
        from PIL import Image
        
        img = Image.open(image_path)
        w, h = img.size
        
        # 策略1: 全图扫描
        decoded = pyzbar.decode(img)
        if decoded:
            return _process_qr_data(decoded[0].data.decode('utf-8'), key)
        
        # 策略2: 裁剪底部区域（QR通常在底部）
        if h > 500:
            # 尝试多个裁剪区域
            for y_start in [h - 400, h - 300, h - 200]:
                if y_start < 0:
                    continue
                crop = img.crop((0, y_start, w, h))
                decoded = pyzbar.decode(crop)
                if decoded:
                    return _process_qr_data(decoded[0].data.decode('utf-8'), key)
        
        # 策略3: 缩小图片再扫描（pyzbar在小图上更灵敏）
        if max(w, h) > 1000:
            scale = 1000 / max(w, h)
            small = img.resize((int(w * scale), int(h * scale)))
            decoded = pyzbar.decode(small)
            if decoded:
                return _process_qr_data(decoded[0].data.decode('utf-8'), key)
        
        return None
    except ImportError:
        print("需要安装: pip3 install pyzbar")
        print("macOS还需要: export DYLD_LIBRARY_PATH=/opt/homebrew/lib")
        return None

def _process_qr_data(data: str, key: str) -> str:
    """处理QR数据，提取密文"""
    if data.startswith('REDS:'):
        hex_str = data[5:]
        try:
            raw_bytes = bytes.fromhex(hex_str)
            return extract_payload(raw_bytes, key)
        except:
            return None
    return None

# --- CLI ---
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='QR角标隐写')
    sub = parser.add_subparsers(dest='cmd')
    
    # encrypt
    enc = sub.add_parser('encrypt')
    enc.add_argument('text', help='密文内容')
    enc.add_argument('--key', '-k', default='default_key')
    enc.add_argument('-i', '--input', help='原图路径')
    enc.add_argument('-o', '--output', help='输出路径')
    enc.add_argument('--qr-size', type=int, default=250)
    enc.add_argument('--position', default='bottom-center')
    
    # decrypt
    dec = sub.add_parser('decrypt')
    dec.add_argument('image', help='图片路径')
    dec.add_argument('--key', '-k', default='')
    
    # locate
    loc = sub.add_parser('locate')
    loc.add_argument('image', help='图片路径')
    
    args = parser.parse_args()
    
    if args.cmd == 'encrypt':
        if not args.input or not args.output:
            print("需要 -i 和 -o 参数")
            sys.exit(1)
        encrypt(args.text, args.key, args.input, args.output,
                qr_size=args.qr_size, position=args.position)
    elif args.cmd == 'decrypt':
        result = decrypt(args.image, args.key)
        if result:
            print(f"解密结果: {result}")
        else:
            print("未找到QR码或解密失败")
    elif args.cmd == 'locate':
        results = locate_qr(args.image)
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        parser.print_help()
