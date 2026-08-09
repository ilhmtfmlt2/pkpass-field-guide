<img src="assets/icon.png" width="72" align="right">

# AnyWallet

> 脚本化、字段级可控、可批量的免签名 `.pkpass` 生成器。

iOS 27（预计 2026 年 9 月）起，Wallet 内置原生 Create a Pass，能把二维码直接包成 pass——但它只做二维码包装，不支持 eventTicket / generic 的完整字段布局、`relevantDate` 本地触发、`locations` 地理围栏，也不能批量或接 CI/CD。**这些正是 AnyWallet 的覆盖范围。**

> **验证状态**：免签机制已在 **iOS 27 beta 4** 真机 40+ 次验证通过。iOS 27 正式版及后续小版本按 [`IOS27_TEST_CHECKLIST.md`](IOS27_TEST_CHECKLIST.md) 回归。下文标注「iOS 27」的行为，均基于 iOS 27 beta 4 实测与苹果官方文档。

---

| | |
|---|---|
| **AnyWallet 的核心是一个算法**<br>把一张第三方 `.pkpass` 改写成免签名、仍能被 iOS 接受的 `.pkpass`，字段完全由你掌控。<br><br>一份字段手册讲清每个参数，一份脚本做完整改写。 | <img src="assets/preview.jpg" width="220" alt="Wallet 预览"><br><sub>图 1 · 真机预览（iOS 27 beta 4）</sub> |

---

## 它是什么

任何第三方 `.pkpass` 本质是 zip：`pass.json`（数据）+ 图片 + `manifest.json`（SHA-1 清单）+ `signature`（开发者签名）。Wallet 验签通过才收。

AnyWallet 借 iOS 自带的 `com.apple.wallet` 系统身份当壳——改身份、剥签名链字段、重算 SHA-1。iOS 看到这个 Team ID 就当系统自家的票放行，签名链这一步直接绕过。

代价是物理的：没有服务器推送，通知只能走本地触发。

**这张票每个字段怎么填、填错会怎样，全在 [`docs/algorithm.md`](docs/algorithm.md)**——那是本项目的核心文档，不是 README 的附录。

---

## iOS 27 时代：原生 Create a Pass 做不到的

iOS 27 起苹果在 Wallet 里加了原生 pass 创建，能包二维码。但它是「轻量包装」，能力天花板很低：

| 能力 | iOS 27 原生 Create a Pass | AnyWallet |
|---|---|---|
| 二维码包装 | ✅ | ✅ |
| eventTicket / generic 完整字段布局 | ❌ | ✅ |
| `relevantDate` 本地触发通知 | ❌ | ✅ |
| `locations` 地理围栏 | ❌ | ✅ |
| 字段级定制（颜色 / 五区 / 背面） | ❌ | ✅ |
| 批量生成 / 接 CI/CD | ❌ | ✅ |
| 服务器推送 | ❌ | ❌（同原生，免签均无） |

结论很直接：**iOS 27 原生的能力 < AnyWallet 的能力**。苹果替你省掉了开发者账号，但没替你省掉字段和批量——那是 AnyWallet 的活。

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

### 碰了就炸（iOS 27 标注）

| 字段 | iOS 27 结论 | 备注 |
|---|---|---|
| `webServiceURL` | 死刑 | 免签 + 此字段 = 添加阶段硬拒 |
| `signature` / `authenticationToken` | 必须删除 | 否则 iOS 验签失败；二者绑死 |
| `storeCard` 样式 | 拒收 | 换 `eventTicket` 或 `generic` |
| `nfc` / `transitType` | eventTicket 不支持 | generic 样式可实验性支持 |
| `background.png` / `strip.png` | 渲染丢弃 | 免签渲染器不读 |
| `transferURL` / `changeSeatURL` / `auxiliaryStoreIdentifiers` | 仅 poster event ticket 有效 | iOS 27 新增字段；普通 eventTicket 填了无效，非 bug |

完整字段行为 + 踩坑数据：[`docs/algorithm.md`](docs/algorithm.md) · [`docs/pitfalls.md`](docs/pitfalls.md)。

---

## 仓库

| 路径 | 说明 |
|---|---|
| `examples/make_demo.py` | 生成去品牌演示票 `demo-template.pkpass` |
| `examples/build_pass.py` | `rebuild()`：改完字段后重算 manifest |
| `examples/pass_template.json` | 去品牌演示票骨架（eventTicket 字段结构） |
| `examples/demo-template.pkpass` | 现成的去品牌样例 |
| `docs/algorithm.md` | 参数全解（每个字段怎么填、填错怎样） |
| `docs/pitfalls.md` | 实战踩坑（每条带实验数据） |
| `IOS27_TEST_CHECKLIST.md` | iOS 27 真机回归清单（每次大改后必跑） |
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

前三条任一挂了，回头查 `manifest.json` 的 SHA-1。完整 iOS 27 回归项见 [`IOS27_TEST_CHECKLIST.md`](IOS27_TEST_CHECKLIST.md)。

---

## 免责声明

文中截图（含图 1 真机预览）来自真机实测渲染，**仅作字段效果与呈现形式的参考**。实际添加至 Wallet 后的显示效果可能因以下因素存在差异：

- iOS / Wallet 版本差异（不同版本对字段渲染、字体缩放、通知触发策略可能不一）
- 设备差异（屏幕尺寸、缩放设置、可访问性选项）
- 票面字段内容差异（字段长度、字符集直接影响字体缩放与排版）
- 模板与字段组合差异（同一字段在不同布局下表现可能不同）
- 网络与时区差异（影响 `locations` 反查、`relevantDate` 触发时间）

### iOS 27 兼容性声明

本项目免签机制已在 **iOS 27 beta 4** 真机验证通过。iOS 27 起苹果在 Wallet 中内置原生 pass 创建能力，本项目面向需要脚本化、字段级定制、批量生成的进阶场景——原生能力覆盖不到的部分。

对于 iOS 27 之后的版本（iOS 28+），苹果可能调整 Wallet 的校验逻辑（参考 iOS 17 已将 App Store 收据校验全面迁移至 SHA-256）。`.pkpass` 的 `manifest` 当前仍是 SHA-1，但存在未来升级到 SHA-256 的风险。**本项目不保证对 iOS 27 之后版本的向前兼容，需在对应版本重新真机验证。**

本项目及文档涉及的票面样式、字段取值均**用于技术研究与字段效果演示**，不涉及任何商业票务平台的实际运营。文末展示的票面示例仅作免签壳机制下的渲染效果参考，与对应品牌实际产品、运营策略无关。如用于商业用途，请自行评估合规风险。

---

## License

MIT。
