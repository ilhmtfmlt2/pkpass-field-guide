# 核心算法

> AnyWallet 归结为**一个算法**：把一张第三方 `.pkpass` 改写成免签名、仍能被 iOS Wallet 添加的 `.pkpass`。
> 这一篇只讲清楚它：参数、步骤、边界、与签名版的差异。

---

## 概述

**输入**：任意一张带签名的 `.pkpass`（zip）。

**输出**：去掉签名链后仍能被 iOS 添加的 `.pkpass`（zip）。

**代价**：没有服务器推送。`webServiceURL` 走不通，因为 APNs 证书绑在原 PTI 上，免签身份拿不到。

**核心动作三步**：

1. 改写身份三键（`teamIdentifier` / `passTypeIdentifier` / `serialNumber`）
2. 剥除签名链字段（`signature` 文件 / `webServiceURL` / `authenticationToken`）
3. 重算 `manifest.json` 的 SHA-1，重打包 zip（不写 `signature`）

---

## 参数表

### 身份三键

| 参数 | 类型 | 免签下的取值 | 说明 |
|---|---|---|---|
| `teamIdentifier` | 字符串 | `"com.apple.wallet"`（固定） | 借 Apple 系统身份。iOS 对此值跳过验签 |
| `passTypeIdentifier` | 字符串 | `"userpass.com.apple.wallet.<uuid>"` | `<uuid>` 每次生成都换（如 `uuid4().hex`） |
| `serialNumber` | 字符串 | 自定义 | 同 PTI 下必须唯一；建议加品牌前缀风格（如 `t.`） |

### 剥除清单

| 字段/文件 | 类型 | 动作 | 原因 |
|---|---|---|---|
| `signature` | zip 文件 | 不写入 | 免签跳过验签，存在反要主动跳过 |
| `webServiceURL` | pass.json 顶层 | 删除 | 必删。免签 + 此字段 iOS 添加阶段硬拒（与 HTTP/HTTPS 无关） |
| `authenticationToken` | pass.json 顶层 | 删除 | 签名链一环，免签无意义 |

### Manifest 重算参数

| 参数 | 取值 | 说明 |
|---|---|---|
| 哈希算法 | SHA-1 | iOS 硬要求，不可换 |
| 输入文件集 | `pass.json` + 所有 png/jpg | 不含 `manifest.json`、不含 `signature` |
| 编码 | UTF-8（`pass.json`）/ 二进制（图片） | `json.dumps(..., ensure_ascii=False).encode("utf-8")` |
| 写入方式 | `manifest.json = {filename: sha1_hex, ...}` | 完整覆盖旧 manifest |
| zip 压缩 | `ZIP_DEFLATED` | 与原包一致 |
| 文件顺序 | 任意 | iOS 按文件名读取 |

---

## 步骤详解

### 步骤 1：身份改写

在 `pass.json` 顶层做三处替换：

```python
pass_json["teamIdentifier"] = "com.apple.wallet"
pass_json["passTypeIdentifier"] = "userpass.com.apple.wallet." + uuid.uuid4().hex
# serialNumber 保持原值或按品牌风格加前缀
```

**为什么必须是这样的值**：

- `teamIdentifier == "com.apple.wallet"` 是 iOS 系统身份特例，触发"跳过验签"。
- `passTypeIdentifier` 必须以 `userpass.com.apple.wallet.` 开头。改成别的（如 `pass.com.example.x`）会被识别为第三方开发者身份，仍要走完整签名链，立刻被拒。
- `passTypeIdentifier` 的 `<uuid>` 部分每次生成都换——同一 PTI 下 `serialNumber` 不能重复，会被 iOS 当作"同一张票"去重。

### 步骤 2：剥除签名链

从 `pass.json` 顶层删键：

```python
for key in ("webServiceURL", "authenticationToken"):
    pass_json.pop(key, None)
```

从 zip 删文件：

```python
# 步骤 4 重打包时直接不写入 signature 文件
```

**为什么三个都要剥**：

- `signature`：免签身份不验签，存在反成冗余字节。
- `webServiceURL`：壳实验 12 轮全失败（其中 5 轮用正经 HTTPS 地址）。iOS 在添加阶段就拒。
- `authenticationToken`：是 `webServiceURL` 服务器拉取 pass 更新的鉴权凭据，二者绑死，删一个必须删另一个。

### 步骤 3：（可选）字段值改写

**只改 `field.value`，不新增字段、不删非签名链字段**。

免签对"额外字段"容忍度不高。原版有什么就留什么，多塞一个字段可能触发 iOS 的字段级防火墙（`semantics` 塞顶层而非 `eventTicket` 嵌套下时实测触发过）。

### 步骤 4：重算 Manifest

```python
import hashlib, json, zipfile

manifest = {}
data = json.dumps(pass_json, ensure_ascii=False).encode("utf-8")
manifest["pass.json"] = hashlib.sha1(data).hexdigest()

# 图片逐个算
for fname, img_bytes in images.items():
    manifest[fname] = hashlib.sha1(img_bytes).hexdigest()
```

### 步骤 5：重打包

```python
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("pass.json", json.dumps(pass_json, ensure_ascii=False).encode("utf-8"))
    for fname, img_bytes in images.items():
        z.writestr(fname, img_bytes)
    z.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False).encode("utf-8"))
    # 注意：不写 signature
```

---

## 代码实现

`examples/build_pass.py` 的 `rebuild()` 是步骤 4 + 5 的最小实现：

```python
def rebuild(path):
    tmp = path + ".tmp"
    manifest = {}
    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist() if n != "manifest.json"]
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as out:
            for n in names:
                data = z.read(n)
                out.writestr(n, data)
                if n != "signature":
                    manifest[n] = hashlib.sha1(data).hexdigest()
            out.writestr("manifest.json",
                         json.dumps(manifest, ensure_ascii=False).encode("utf-8"))
    os.replace(tmp, path)
```

`examples/make_demo.py` 是完整链路：读骨架 → 改身份 → 剥字段 → 改 value → 算 manifest → 打包。它还做一件事：生成后**自检 manifest 自洽**，确保包内文件 SHA-1 与 manifest 一致。

---

## 边界条件

### 改了任何字节都要重算

`pass.json` 里一个字符、任何一张图，都必须重算对应文件的 SHA-1。否则 iOS 添加时直接报"凭证无效"拒收。**没有捷径**。

### `passTypeIdentifier` 必须每次换 uuid

同 PTI 下 `serialNumber` 不能重复。两次生成若 PTI 相同但 serialNumber 不同，Wallet 列表里只会留一张。建议每次 `uuid4().hex`。

### 不需要 `signature` 文件存在

原包若带 `signature`，重打包时跳过它。原包若没有，也别补——补了 iOS 反而要验签。

### 图片尺寸不要硬编码

同一品牌不同票，thumbnail 实测有 68×95 和 67×90 两种；icon 实测有 50×50 和 25×25 两种。换壳脚本**从模板运行时读取尺寸**，写死必错。

### 字体缩放是 Wallet 自动行为

字段内容越长，字号自动越小。座位行 23 字会比 7 字明显小一档。想字大就缩短文字，**没有开关**。

---

## 通知系统：两条独立路径

免签 pass 的通知只能走本地触发。两条路径机制完全不同：

| 路径 | 机制 | 免签下可用 |
|---|---|---|
| 服务器推送 | `webServiceURL` + APNs 证书 + Apple 推送 | ❌（删 `webServiceURL`） |
| 本地触发 | `relevantDate` / `locations` / `beacons` | ✅ |

`passThatWasSet` 设过去时间（生成时刻 −24h）的 `eventTicket` 对象深拷贝，避免 Wallet 的"刚刚更新"检测重置通知设置。**必须是对象快照，不是时间戳字符串**——早期试过字符串与 `{datetime, timestamp}` 对象格式均无效。

---

## 与签名版的差异

| 维度 | 签名版 | 免签 |
|---|---|---|
| 证书 | 开发者账号申请 | 无 |
| 验签 | Wallet 验签 | 跳过 |
| 服务器推送 | `webServiceURL` + APNs | 不可用 |
| 本地触发 | 可用 | 可用 |
| `signature` 文件 | 必有 | 无 |
| `passTypeIdentifier` | `pass.com.<brand>.<x>` | `userpass.com.apple.wallet.<uuid>` |
| `teamIdentifier` | 开发者 Team ID | `com.apple.wallet` |
| `webServiceURL` | 可有 | 删除 |
| `authenticationToken` | 可有 | 删除 |

---

## 实测结论来源

- 40+ 次壳实验（不同字段组合的 `pass.json`）
- 5 个原版品牌样本（猫眼、万达、携程、淘票票、iTunes）逐字段比对
- 12 轮 `webServiceURL` 实验（其中 5 轮用正经 HTTPS）
- 多张图实测的图片尺寸样本（thumbnail 68×95、67×90；icon 50×50、25×25）

样本均不在本仓库内。AnyWallet 公开的部分只有算法本身、一份字段手册、一份去品牌模板。