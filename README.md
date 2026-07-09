# 🔴 REDSecret

> A secret makes a woman woman. — 《名侦探柯南》

**把真心话藏起来。**

REDSecret 是一个浏览器端的隐写工具，让你在图片和文字中隐藏秘密信息。只有知道密钥的人才能读出你藏起来的话。**零依赖，打开网页即用。**

## ✨ 三种隐写模式

| 模式 | 原理 | 特点 |
|------|------|------|
| ◧ **QR 隐写** | 加密数据编码为QR码，嵌入图片 | 有微小可见标记，容错强，抗压缩 |
| ▣ **LSB 隐写** | 数据藏在像素RGB最低有效位 | 完全不可见，必须用PNG原图传递 |
| ﹂ **零宽字符** | 数据编码为Unicode零宽字符 | 无需图片，粘贴到聊天/微博即可传递 |

## 🔐 加密方式

- **XOR 流加密** — 密钥循环异或，简单高效
- **自定义载荷格式** — REDS magic header + 长度 + 校验和
- **密钥保护** — 错误密钥输出乱码

## 🚀 使用方式

直接在浏览器中打开：

**[在线使用 →](https://cnjoe1130.github.io/REDSecret/demos/tool.html)**

或者本地运行：

```bash
git clone https://github.com/cnjoe1130/REDSecret.git
cd REDSecret/demos
python3 -m http.server 8090
# 打开 http://localhost:8090/tool.html
```

无需安装任何依赖。

## 📱 使用场景

| 场景 | 推荐模式 | 说明 |
|------|---------|------|
| 1v1 文件传输 | LSB 隐写 | 完全不可见，用PNG原图 |
| 飞书/微信发图 | QR 隐写 | 抗压缩，Reed-Solomon 纠错 |
| 微信/微博发文字 | 零宽字符 | 藏在文案里，肉眼不可见 |
| 社交平台 | QR 隐写 | 有微小标记但信息完整 |

## ⚠️ 注意事项

- **LSB 隐写**：必须保存为 PNG，截图/压缩/滤镜会损坏数据
- **零宽字符**：部分平台（微信公众号编辑器等）可能过滤零宽字符
- **QR 隐写**：图片角落会有微小QR标记，选择远离主体的位置

## 🔐 安全说明

- XOR 流加密 + 自定义载荷格式（REDS magic header）
- 正确密钥 → 解密成功
- 错误密钥 → 输出乱码
- 所有运算在浏览器本地完成，数据不上传服务器

## 📄 License

MIT

## 🙏 致谢

- [qrcode.js](https://github.com/soldair/node-qrcode) — QR码生成
- [jsQR](https://github.com/cozmo/jsQR) — QR码检测
- Unicode 零宽字符编码（U+200B, U+200C, U+200D, U+FEFF）
