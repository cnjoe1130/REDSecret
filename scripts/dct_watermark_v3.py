#!/usr/bin/env python3
"""
DCT频域水印 v3 — 强度自适应版
核心：嵌入强度 > JPEG量化步长 = 数据存活

用法：
  python3 dct_watermark_v3.py --img input.png --secret "密语" --key "密钥" --quality 75

依赖：pip install reedsolo scipy Pillow numpy
"""
import hashlib, io, numpy as np
from PIL import Image
from reedsolo import RSCodec, ReedSolomonError
from scipy.fftpack import dctn, idctn

QUANT_75 = np.array([
    [16,11,10,16,24,40,51,61],[12,12,14,19,26,58,60,55],
    [14,13,16,24,40,57,69,56],[14,17,22,29,51,87,80,62],
    [18,22,37,56,68,109,103,77],[24,35,55,64,81,104,113,92],
    [49,64,78,87,103,121,120,101],[72,92,95,98,112,100,103,99]
], dtype=np.float32)

def quant_table(q):
    scale = (100-q)/50.0 if q >= 50 else 50.0/q
    qt = np.round(QUANT_75*scale).astype(np.float32)
    qt[qt==0]=1; return qt

def gen_pos(key, total):
    h=hashlib.sha256(key.encode()).digest()
    rng=np.random.RandomState(int.from_bytes(h[:4],'big'))
    return np.where(rng.randint(0,2,size=total)==1)[0]

def embed(cover_gray, secret, key, strength=12.0):
    arr=np.array(cover_gray,dtype=np.float32)
    h,w=arr.shape; hp,wp=(8-h%8)%8,(8-w%8)%8
    if hp or wp: arr=np.pad(arr,((0,hp),(0,wp)),'reflect')
    bh,bw=arr.shape[0]//8,arr.shape[1]//8; total=bh*bw
    rs=RSCodec(40); encoded=rs.encode(secret.encode('utf-8'))
    bits=''.join(format(b,'08b') for b in encoded)
    payload=format(len(bits),'032b')+bits
    positions=gen_pos(key,total)
    if len(payload)>len(positions): raise ValueError("数据太长")
    out=arr.copy()
    for i,bit in enumerate(payload):
        idx=positions[i]; by,bx=(idx//bw)*8,(idx%bw)*8
        d=dctn(out[by:by+8,bx:bx+8],type=2,norm='ortho')
        d[1,2]+=strength if int(bit) else -strength
        out[by:by+8,bx:bx+8]=idctn(d,type=2,norm='ortho')
    result=np.clip(out[:h,:w] if hp or wp else out,0,255).astype(np.uint8)
    ps=10*np.log10(255**2/np.mean((arr[:h,:w]-result.astype(np.float32))**2))
    return Image.fromarray(result),len(payload),ps

def extract(img_gray, key):
    arr=np.array(img_gray,dtype=np.float32)
    h,w=arr.shape; hp,wp=(8-h%8)%8,(8-w%8)%8
    if hp or wp: arr=np.pad(arr,((0,hp),(0,wp)),'reflect')
    bh,bw=arr.shape[0]//8,arr.shape[1]//8
    positions=gen_pos(key,bh*bw)
    raw=[]
    for i in range(min(32,len(positions))):
        idx=positions[i]; by,bx=(idx//bw)*8,(idx%bw)*8
        d=dctn(arr[by:by+8,bx:bx+8],type=2,norm='ortho')
        raw.append('1' if d[1,2]>0 else '0')
    bitlen=int(''.join(raw),2)
    if bitlen<=0: return '','NO_DATA'
    for i in range(32,min(32+bitlen,len(positions))):
        idx=positions[i]; by,bx=(idx//bw)*8,(idx%bw)*8
        d=dctn(arr[by:by+8,bx:bx+8],type=2,norm='ortho')
        raw.append('1' if d[1,2]>0 else '0')
    data_bits=''.join(raw[32:32+bitlen])
    data_bytes=bytes([int(data_bits[i:i+8],2) for i in range(0,len(data_bits)-7,8)])
    for nsym in [40,60,80]:
        try:
            result=RSCodec(nsym).decode(data_bytes)
            decoded=result[0] if isinstance(result,tuple) else result
            return decoded.decode('utf-8'),'OK'
        except: continue
    return data_bytes.decode('utf-8',errors='replace'),'FAIL'

def jpeg_compress(img, q):
    buf=io.BytesIO(); img.save(buf,format='JPEG',quality=q)
    buf.seek(0); return Image.open(buf)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument('--img',required=True); p.add_argument('--secret',required=True)
    p.add_argument('--key',required=True); p.add_argument('--quality',type=int,default=75)
    args=p.parse_args()
    img=Image.open(args.img).convert('L')
    qt=quant_table(args.quality); s=max(qt[1,2]*1.2+2,8.0)
    w,bits,ps=embed(img,args.secret,args.key,strength=s)
    print(f"嵌入: {bits} bits, PSNR: {ps:.1f} dB, 强度: {s:.1f}")
    for q in [95,85,75,70,60,50]:
        comp=jpeg_compress(w,q); text,msg=extract(comp,args.key)
        ok="✅" if text==args.secret else "❌"
        print(f"q{q:>3}: {ok} {msg} -> {text[:30]}")
