<img src="assets/icon.png" width="72" align="right">

# AnyWallet

> 不签名，也能进 iPhone 钱包的凭证。

不申请开发者账号、不签证书、不开 APNs，做出一张能直接加进 Wallet 的 `.pkpass`——电影票、会员卡、优惠券都行。

---

| | |
|---|---|
| **AnyWallet 的核心是一个算法**<br>把一张第三方 `.pkpass` 改写成免签名、仍能被 iOS 接受的 `.pkpass`。<br><br>一份字段手册讲清边界，一份脚本做完整改写。结论全部来自真机实测。 | <img src="assets/preview.jpg" width="220" alt="Wallet 预览"><br><sub>图 1 · 真机预览</sub> |

---

## 它是什么

任何第三方 `.pkpass` 本质是 zip：`pass.json`（数据）+ 图片 + `manifest.json`（SHA-1 清单）+ `signature`（开发者签名）。Wallet 验签通过才收。

AnyWallet 借 iOS 自带的 `com.apple.wallet` 系统身份当壳——改身份、剥签名链字段、重算 SHA-1。iOS 看到这个 Team ID 就当系统自家的票放行，签名链这一步直接绕过。

代价是物理的：没有服务器推送，通知只能走本地触发。

**这张票每个字段怎么填、填错会怎样，全在 [`docs/algorithm.md`](docs/algorithm.md)**——那是本项目的核心文档，不是 README 的附录。

---

## 能力边界

### 能填的字段

| 类别 | 字段 |
|---|---|
| 身份 | `formatVersion` · `serialNumber` · `organizationName` · `description` |
| 外观 | `backgroundColor` · `foregroundColor` · `labelColor` · `logoText` |
| 票面 | `headerFields` · `primaryFields` · `secondaryFields` · `auxiliaryFields` · `backFields` |
| 条码 | `barcode` · `barcodes` |
| 本地触发 | `relevantDate` · `locations` · `maxDistance` · `beacons` · `ignoresTimeZone` |
| 语义 | `semantics` |
| 状态 | `expirationDate` · `passThatWasSet` · `voided` · `sharingProhibited` |
| 杂项 | `groupingIdentifier` · `appLaunchURL` · `associatedStoreIdentifiers` · `userInfo` |

### 碰了就炸

| 字段 | 结论 |
|---|---|
| `webServiceURL` | **死刑**（免签 + 此字段 iOS 添加阶段硬拒） |
| `signature` / `authenticationToken` | 删除（签名链一环） |
| `storeCard` 样式 | 拒收。换 `eventTicket` 或 `generic` |
| `background.png` / `strip.png` | 渲染丢弃 |
| `nfc` / `transitType` | `eventTicket` 不支持 |

完整字段行为 + 踩坑数据：[`docs/algorithm.md`](docs/algorithm.md) · [`docs/pitfalls.md`](docs/pitfalls.md)。

---

## 仓库

| 路径 | 说明 |
|---|---|
| `examples/make_demo.py` | 生成去品牌演示票 `demo-template.pkpass` |
| `examples/build_pass.py` | `rebuild()`：改完字段后重算 manifest |
| `examples/pass_template.json` | 去品牌演示票骨架（eventTicket 字段结构） |
| `examples/demo-template.pkpass` | 现成的去品牌样例 |
| `docs/algorithm.md` | 核心算法详解（参数、步骤、边界） |
| `docs/pitfalls.md` | 实战踩坑（每条带实验数据） |
| `assets/icon.png` | 项目图标 |
| `assets/preview.jpg` | 真机预览缩略图 |
| `assets/field-layout.svg` | 票面区域图 |

---

## 附赠：可跑的示例（非必需）

仓库里有一份能直接生成的去品牌票，方便你对照字段手册看实际效果，但**不是项目主线**——你照着 `docs/algorithm.md` 手写一张也完全可行。

```bash
# 生成去品牌演示票
python examples/make_demo.py
# 用 AirDrop / 邮件传到 iPhone，点开加进 Wallet
```

`examples/` 下：`pass_template.json`（骨架）、`make_demo.py`（生成器）、`build_pass.py` 的 `rebuild()`（改完字段后重算 manifest 的小工具）、`demo-template.pkpass`（现成样例）。

---

## 真机验证清单

- 能否正常添加（不报错即过）
- 颜色、文案、二维码是否正常
- 锁屏是否在 `relevantDate` 附近弹通知（详情页 ⓘ 里看通知开关在不在）
- 点 ⓘ 背面信息是否完整
- 过期时间到点后是否自动归档

前三条任一挂了，回头查 `manifest.json` 的 SHA-1。

---

## 免责声明

文中截图（含图 1 真机预览）来自真机实测渲染，**仅作字段效果与呈现形式的参考**。实际添加至 Wallet 后的显示效果可能因以下因素存在差异：

- iOS / Wallet 版本差异（不同版本对字段渲染、字体缩放、通知触发策略可能不一）
- 设备差异（屏幕尺寸、缩放设置、可访问性选项）
- 票面字段内容差异（字段长度、字符集直接影响字体缩放与排版）
- 模板与字段组合差异（同一字段在不同布局下表现可能不同）
- 网络与时区差异（影响 `locations` 反查、`relevantDate` 触发时间）

本项目及文档涉及的票面样式、字段取值均**用于技术研究与字段效果演示**，不涉及任何商业票务平台的实际运营。文末展示的票面示例仅作免签壳机制下的渲染效果参考，与对应品牌实际产品、运营策略无关。如用于商业用途，请自行评估合规风险。

---

## License

MIT。