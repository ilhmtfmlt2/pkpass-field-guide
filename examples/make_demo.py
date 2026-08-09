#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成「去品牌」演示模板 demo-template.pkpass

设计目标：
- 字段结构、key/label、布局与真实电影票 eventTicket 完全一致（直接复刻猫眼原版骨架）
- 但去掉一切品牌标识：icon/logo 用纯色占位图，颜色换成中性深蓝，内容用示例数据
- 这样文档用它做演示时，不会牵扯任何第三方品牌的 logo / 视觉资产

用法：
    python make_demo.py
产物：
    demo-template.pkpass   （含 6 张占位图 + pass.json + manifest.json，manifest 已重算 SHA-1）
"""
import io, json, os, zipfile, hashlib
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
TPL = r"c:\AI\apple\开发\maoyan_web_template.json"
OUT = os.path.join(HERE, "demo-template.pkpass")

# 中性色，去品牌
NEUTRAL = (22, 42, 78)
NEUTRAL_LT = (60, 90, 140)
FONT = r"C:\Windows\Fonts\msyh.ttc"

def font(sz):
    try:
        return ImageFont.truetype(FONT, sz, index=0)
    except Exception:
        return ImageFont.load_default()

def tile(size, bg, fg=(255, 255, 255), text=None, ts=None):
    img = Image.new("RGB", size, bg)
    d = ImageDraw.Draw(img)
    if text:
        f = font(ts or size[1] // 4)
        bb = d.textbbox((0, 0), text, font=f)
        w, h = bb[2] - bb[0], bb[3] - bb[1]
        d.text(((size[0] - w) / 2 - bb[0], (size[1] - h) / 2 - bb[1]),
               text, fill=fg, font=f)
    return img

# ---- 读取骨架 ----
with open(TPL, encoding="utf-8") as f:
    tpl = json.load(f)
p = tpl["pass"]

# ---- 去品牌：颜色 + 组织名 ----
p["backgroundColor"] = "rgb(22,42,78)"
p["foregroundColor"] = "rgb(255,255,255)"
p["labelColor"] = "rgb(190,205,230)"
p["organizationName"] = "Demo Pass"

# ---- 示例数据（字段值与真实票同构，仅内容中性化）----
ev = p["eventTicket"]
def setf(sec, key, val):
    for fld in ev.get(sec, []):
        if fld.get("key") == key:
            fld["value"] = val
            return

setf("primaryFields", "movie", "示例影片：星海")
setf("secondaryFields", "exchangeCode", "1385-6042")
setf("auxiliaryFields", "cinemaName", "示例国际影城")
setf("auxiliaryFields", "seats", "7排6座,7排7座,7排8座")
setf("auxiliaryFields", "show", "2月12日 周一 20:42")
setf("backFields", "cinemaInfo", "地址：示例市示例路1号\r\n电话：1010-5335")
setf("backFields", "takeTicketInfo",
     "2月12日20:42示例国际影城示例影片：星海4号厅7排6座,7排7座,7排8座已购，"
     "凭码1385-6042至影院内自助取票机取票")
setf("backFields", "customerServicePhone", "1010-5335")

# 二维码取末 8 位（与真实猫眼规律一致）
raw = "13856042"
p["barcode"]["message"] = raw
p["barcodes"][0]["message"] = raw
p["description"] = "示例国际影城02月12日示例影片：星海影票3张"
# passThatWasSet = 整张票字段快照（原版对象格式）
p["passThatWasSet"] = json.loads(json.dumps(ev, ensure_ascii=False))
p["expirationDate"] = "2024-02-12T22:30:00Z"

# ---- 占位图（无品牌）----
tiles = {
    "icon.png": tile((29, 29), NEUTRAL, text="P", ts=18),
    "icon@2x.png": tile((58, 58), NEUTRAL, text="P", ts=36),
    "logo.png": tile((319, 80), NEUTRAL, text="DEMO PASS", ts=34),
    "logo@2x.png": tile((639, 160), NEUTRAL, text="DEMO PASS", ts=68),
    "thumbnail.png": tile((68, 95), NEUTRAL_LT, text="示例影片", ts=14),
    "thumbnail@2x.png": tile((135, 189), NEUTRAL_LT, text="示例影片", ts=26),
}

# ---- 打包 + 重算 manifest SHA-1 ----
parts = {"pass.json": json.dumps(p, ensure_ascii=False).encode("utf-8")}
for name, img in tiles.items():
    buf = io.BytesIO()
    img.save(buf, "PNG")
    parts[name] = buf.getvalue()
manifest = {k: hashlib.sha1(v).hexdigest() for k, v in parts.items()}
parts["manifest.json"] = json.dumps(manifest, ensure_ascii=False).encode("utf-8")

if os.path.exists(OUT):
    os.remove(OUT)
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    for k, v in parts.items():
        z.writestr(k, v)
print("生成:", OUT, os.path.getsize(OUT), "bytes")
with zipfile.ZipFile(OUT) as z:
    man = json.loads(z.read("manifest.json"))
    ok = all(hashlib.sha1(z.read(n)).hexdigest() == man[n]
             for n in z.namelist() if n != "manifest.json")
print("manifest 自洽校验:", ok)
