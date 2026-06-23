# 🔴 REDSecret

> A secret makes a woman woman. — 《名侦探柯南》

**把真心话藏起来。**

REDSecret 是一个 AI 驱动的隐写工具，让你在图片和文字中隐藏秘密信息。只有知道密钥的人才能读出你藏起来的话。

## ✨ 功能特性

- 🖼️ **像素隐写** — QIM 加密，藏在图片像素里，肉眼不可见
- 📱 **QR 角标隐写** — 加密二维码贴在图片角落，抗压缩抗损坏
- 📝 **零宽字符隐写** — 藏在文字里，Unicode 零宽字符编码
- 🔐 **双重加密** — QIM/零宽编码 + XOR 流加密
- 🎨 **6 种配色风格** — 暗夜情绪、温柔粉、奶油白、海蓝、暖橘、极简黑
- 📊 **表面伪装** — 可以伪装成盘中分析、心情日记等正常内容

## 🚀 快速开始

### 安装依赖

```bash
pip install Pillow numpy qrcode opencv-python-headless
```

### 加密

```bash
# 基础用法：输入密文 + 密钥
python scripts/encrypt.py "有些夜晚眼泪比笑容更诚实" --key "Joe"

# 指定配色风格
python scripts/encrypt.py "今天又被老板骂了" --key "Joe" --style midnight_emo

# 自定义表面文案（表面一套、背后一套）
python scripts/encrypt.py "其实我快撑不下去了" --key "Joe" --surface "今天也是元气满满的一天☀️"
```

### 解密

```bash
# 带密钥解密
python scripts/decrypt.py 图片路径.png "Joe"

# 自动修正扩展名
python scripts/decrypt.py 图片路径.jpeg "Joe" --fix
```

### QR 角标隐写

```bash
# 加密：生成带QR角标的图
python scripts/qr_stego.py encrypt "密语内容" \
  --key "getrich" \
  -i 原图.png -o 输出.jpg \
  --qr-size 250

# 解密：读取图中QR码
python scripts/qr_stego.py decrypt 输出.jpg --key "getrich"
```

### 零宽字符隐写

```bash
# 加密：将密文嵌入表面文案
python scripts/zw_stego.py encrypt "📊 6.10 盘中快照\n上证 3382 (+0.47%)" \
  "你看到的是盘面，我藏的是人生。" --key "hongli2026"

# 解密
python scripts/zw_stego.py decrypt "含零宽的文案..." --key "hongli2026"
```

## 📱 使用场景

| 场景 | 推荐方案 | 说明 |
|------|---------|------|
| 1v1 文件传输 | QIM + PNG | 最稳，100% 可靠 |
| 飞书发图 | QIM | 飞书保留 PNG 数据 |
| 微信朋友圈（图片） | QR 角标 | 抗压缩，Reed-Solomon 纠错 |
| 微信朋友圈（文案） | 零宽字符 | 藏在文字里，肉眼不可见 |
| 小红书 | QR 角标 | ⚠️ 有审核风险 |

## 🎨 配色风格

| 风格名 | 效果 | 适合场景 |
|--------|------|---------|
| `midnight_emo` | 暗蓝紫调 | 深夜心事 |
| `gentle_pink` | 温柔粉色 | 少女心事 |
| `cream` | 奶油白 ins 风 | 文艺清新 |
| `ocean` | 海蓝色 | 清新治愈 |
| `warm_orange` | 暖橘色 | 温暖活力 |
| `dark_minimal` | 极简黑 | 酷/高级感 |

## 🔐 安全说明

- 加密算法为 QIM (STEP=8) + XOR 流加密
- 解密脚本无注释、无文档，增加逆向难度
- 正确密钥 → 解密成功
- 错误密钥 → 输出乱码

## 📄 License

MIT

## 🙏 致谢

- QIM 隐写算法
- Unicode 零宽字符编码
- QR 码 Reed-Solomon 纠错
