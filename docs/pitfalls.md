# 踩坑实录

实战里反复栽过的地方记下来，下次少掉坑。每一条都附当时的实验数据，不是凭印象写的。

## 1. `.pkpasses` 一键包的内部结构

`.pkpasses` 是个 zip，里面装多个 `.pkpass`。关键：**每个 `.pkpass` 本身也是个 zip，必须作为整体条目放进去，不能拆开**。

错误写法（把 `.pkpass` 当目录展开，iOS 不认）：

```python
with zipfile.ZipFile(pk) as inner:
    for member in inner.namelist():
        z.writestr(f"{base}/{member}", inner.read(member))
```

这样打出来是 `xxx.pkpass/icon.png`、`xxx.pkpass/pass.json` 这种零散文件，iOS 找不到完整的票。

正确写法（整文件作为一条目）：

```python
with zipfile.ZipFile(BUNDLE, "w", ZIP_DEFLATED) as z:
    for pk in built:
        z.write(pk, arcname=os.path.basename(pk))
```

判断标准：用 `zipinfo` 看 `.pkpasses` 内部，顶层条目应该是 `xxx.pkpass`、`yyy.pkpass` 这种没有斜杠的名字。如果看到 `xxx.pkpass/pass.json`，就是拆错了。

## 2. `webServiceURL` 是死刑

壳实验做了 12 轮，含 8 个挂 `webServiceURL` 的变体，全部添加失败。最关键的证据：07/08/10/11/12 这五个用的就是正经 HTTPS 地址（apple.com、meituan 域名），照样打不开。说明是"免签身份 + webServiceURL"这个组合在添加阶段就被 iOS 硬拒，跟协议无关。

更深层的原因：就算放过了，服务器推送还要 APNs 证书，而证书绑定在 `passTypeIdentifier` 所属的开发者账号下；免签用的是 Apple 自己的 `com.apple.wallet`，你拿不到它的 APNs 证书，推送永远不可能工作。

所以免签 pass 别碰 `webServiceURL`，通知只走本地触发字段（relevantDate / locations / beacons）。

## 3. 字体缩放不是 bug

同一张 `eventTicket` 模板，某个字段字长一倍，显示字号就小一圈。这是 Wallet 的自动缩放，内容长度和字号负相关。想字大就缩短文字，没有别的开关。实测：座位行 23 字 vs 7 字，前者明显小一档。

## 4. 列表城市名：locations 反查 ≠ 详情跳地图

最容易被混为一谈的两件事：

- 归档/列表里显示"新乡市，河南省"这种城市前缀，来自 `locations` 或 `semantics.venue.location` 的 GPS 坐标被反查。猫眼原版这两个字段都是空，所以只显示"活动门票"。万达有真实坐标，就显示了城市。
- 详情页点地址跳地图，靠的是 `backFields` 里的文字被 iOS Data Detectors 识别成链接。不需要坐标，也不影响列表。

两者机制完全独立。想列表干净又想详情能导航，就：不加 `locations`，但在 `backFields` 写真实地址文字。

## 5. `barcode.message` 末 8 位规律

猫眼原版里，票面显示的验证码和二维码内容不是一个东西。取票码超过 8 位时，二维码只取末 8 位；不超过 8 位才取完整。生成时按下面处理：

```python
raw = re.sub(r"[\s-]", "", code)
message = raw[-8:] if len(raw) > 8 else raw
```

## 6. `passThatWasSet` 用对象格式

一开始以为是普通时间戳字符串，实测无效。猫眼原版里它是 `eventTicket` 整个对象的快照（primaryFields / secondaryFields / auxiliaryFields / backFields 全在里面）。填值后直接 `copy.deepcopy(pass_json["eventTicket"])` 塞回去即可。

## 7. 图片尺寸别硬编码

同一个品牌的不同票，图片尺寸可能不一样。实测两个猫眼样本：thumbnail 一个 68×95、一个 67×90；icon 一个 50×50、一个 25×25。换壳脚本里图片尺寸要从模板运行时读，写死必错。

## 8. 免签壳的硬限制（无法绕过）

- `teamIdentifier` 必须是 `com.apple.wallet`，`passTypeIdentifier` 必须是 `userpass.com.apple.wallet.*`，改回真实值 iOS 不认。
- `webServiceURL` / `authenticationToken` / `signature` 全部不能要。
- 通知只能本地触发，没有服务器推送。

这些不是没调好，是物理限制。剩下所有字段都能按原版 1:1 复刻。
