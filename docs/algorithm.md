# 参数全解

> AnyWallet 归根结底是一件事：把一张带签名的 `.pkpass` 改写成免签名、仍能被 iOS Wallet 添加的 `.pkpass`。
> 这一篇只讲**参数**——一张 `pass.json` 里每个字段：免签下**生不生效**、**怎么填**、**填错会怎样**。结论全来自真机实测（**iOS 27 beta 4**，40+ 次壳实验）。

---

## 0 先说结论：免签壳到底能覆盖什么

很多人拿到项目第一反应是"哪些能用、哪些不能用"。这一节一次讲透，**后面每节不再重复"生效/不生效"的判断**。

### 能生效的场景（实测确认）

| 能力 | 字段 | 实测表现 |
|---|---|---|
| 票面完整布局 | `eventTicket` 五区（primary/secondary/auxiliary/back/header） | 渲染正常，和签名版无差异 |
| 颜色与文字 | `backgroundColor` / `foregroundColor` / `labelColor` / `logoText` / `organizationName` / `description` | 正常 |
| 二维码 / 条形码 | `barcode` + `barcodes` | 扫码出 `message` 内容，正常核销 |
| 缩略图 | `thumbnail` | 票面右侧正常显示 |
| 本地触发通知 | `relevantDate` / `locations` / `beacons` / `maxDistance` / `ignoresTimeZone` | **实测真弹锁屏通知**（relevantDate 到点、进围栏都验证过） |
| 列表显示城市 | `locations` 坐标 | 有坐标→列表显示城市；无坐标→只显示「活动门票」 |
| 背面地址可点 | `backFields` 里写地址/电话文字 | iOS Data Detectors 自动识别成链接，实测可点 |
| 过期归档 | `expirationDate` | 到点自动移出活跃列表，实测确认 |
| 禁止分享 | `sharingProhibited` | **生效**：长按不再出现分享/添加入口 |
| 标记作废 | `voided` | **生效**：票面显示作废样式（实测渲染出失效态） |
| 分组显示 | `groupingIdentifier` | 生效：同组多张票归在一处 |
| 语义理解 | `semantics`（eventTicket 内） | 生效：Spotlight 能搜到、钱包智能分类生效 |
| 关联 App 入口 | `associatedStoreIdentifiers` | 生效：票面出现「打开 App」入口（需 App 真在商店上架） |
| 唤醒 App | `appLaunchURL` | 生效：点票面唤起对应 https App |
| 免签身份 | `teamIdentifier=com.apple.wallet` + `passTypeIdentifier=userpass.com.apple.wallet.<uuid>` | 放行，跳过验签 |

### 不能生效 / 必删的场景（实测确认）

| 能力 | 字段 | 实测表现 |
|---|---|---|
| 服务器推送 | `webServiceURL` + `authenticationToken` | **硬拒**：免签 + 此组合在添加阶段直接打不开（12 轮实验全失败，含 5 轮正经 HTTPS） |
| 开发者签名 | `signature` 文件 | 留着反而 iOS 验签失败被拒，必须不写 |
| storeCard 样式 | `storeCard` | 拒收，换 `eventTicket` / `generic` |
| NFC | `nfc` / `transitType` | `eventTicket` 不支持（报错）；`generic` 样式可实验性支持 |
| 背景/横幅图 | `background.png` / `strip.png` | 免签渲染器丢弃，写了白写 |
| iOS 27 新增字段 | `transferURL` / `changeSeatURL` / `auxiliaryStoreIdentifiers` | **仅 poster event ticket 生效**；普通 eventTicket 填了无效，非 bug |

> **iOS 27 上下文**：苹果在 iOS 27 的 Wallet 中内置原生 Create a Pass，只做轻量二维码包装——不支持本表上半部分的完整字段布局、`relevantDate` 本地触发、`locations` 地理围栏、批量/CI。这些正是 AnyWallet 的覆盖范围，详见 README 的「iOS 27 时代」对比表。

---

## 1 文件结构与 pass.json 骨架

一张 `.pkpass` 是 zip，根下文件：

| 文件 | 作用 | 免签下 |
|---|---|---|
| `pass.json` | 全部数据与样式 | 必须，改身份、剥字段 |
| `manifest.json` | 每个文件的 SHA-1 | 必须，**每次改动后重算** |
| `icon.png` / `icon@2x.png` | 列表缩略图标 | **必须有，否则添加报错** |
| `logo.png` / `logo@2x.png` | 票面左上角标志 | 可选 |
| `thumbnail.png` / `thumbnail@2x.png` | 票面右侧缩略图 | 可选 |
| `background.png` / `strip.png` | 背景/横幅图 | 免签被丢弃，别费劲 |
| `signature` | 开发者签名 | 不写，写了反而要验签 |

`pass.json` 顶层键先认一遍（完整可跑的最小集见文末附录）：

```json
{
  "formatVersion": 1,
  "teamIdentifier": "com.apple.wallet",
  "passTypeIdentifier": "userpass.com.apple.wallet.<uuid>",
  "serialNumber": "t.27e66d8c385e",
  "organizationName": "示例影城",
  "description": "示例影城02月12日示例影片影票3张",
  "backgroundColor": "rgb(22,42,78)",
  "foregroundColor": "rgb(255,255,255)",
  "labelColor": "rgb(190,205,230)",
  "logoText": "DEMO PASS",
  "barcode": { ... },
  "barcodes": [ ... ],
  "eventTicket": { ... },
  "passThatWasSet": { ... },
  "relevantDate": "2024-02-12T20:42:00Z",
  "expirationDate": "2024-02-12T22:30:00Z",
  "sharingProhibited": false,
  "associatedStoreIdentifiers": [504274740]
}
```

---

## 2 身份三键（免签的命门）

这三键决定 iOS 是否走验签，写错立刻被拒，没有中间态。

| 键 | 免签固定写法 | 写错后果 |
|---|---|---|
| `formatVersion` | `1` | 非 1 添加报错 |
| `teamIdentifier` | `"com.apple.wallet"` | 写成别的 Team ID → 走验签 → 无合法 signature 直接拒 |
| `passTypeIdentifier` | `"userpass.com.apple.wallet."` + uuid | 不以该前缀开头 → 识别为第三方开发者身份 → 走完整签名链 → 拒 |
| `serialNumber` | 同 PTI 下唯一即可 | 同 PTI 下重复 → Wallet 当同一张票去重，只留一张 |

**两个必须每次变的量**（这是同一个规则的两种表现，不是两条独立要求）：

- `passTypeIdentifier` 末尾 `<uuid>`：**每次生成都换**（`uuid4().hex`）。
- `serialNumber`：建议带随机性（如 `t.` + 随机串）。

原因只有一条：**同一 `passTypeIdentifier` 下，`serialNumber` 不能重复**。两次生成若 PTI 相同、serialNumber 不同，Wallet 列表只留一张。所以只要保证"每次生成 PTI 换新 uuid"，serialNumber 撞车概率就趋于零。

`formatVersion`、`teamIdentifier` 是死的，别动。

---

## 3 外观与标识

| 键 | 取值 | 免签下 | 说明 |
|---|---|---|---|
| `organizationName` | 字符串 | 生效 | 锁屏通知、Wallet 列表显示的发行方名；**不是**票面大字 |
| `description` | 字符串 | 生效 | 无障碍/搜索描述，建议 `{影院}{月}月{日}日{影片}影票N张` |
| `backgroundColor` / `foregroundColor` / `labelColor` | `rgb(r,g,b)` 或 `#RRGGBB` | 生效 | 底色 / 主文字色 / 标签色；三者需足够对比，否则部分机型字段看不清（不报错，只是难看） |
| `logoText` | 字符串 | 生效 | 左上角 logo 旁纯文字（无 logo 图也能显示文字标） |

颜色实测：免签渲染器 `rgb()` 和 `#` 两种写法都认。

---

## 4 票面五区（eventTicket 专属，全部生效）

`eventTicket` 内分五个数组，每个元素是 `{key, label, value}`（可带 `attributedValue` / `dateStyle` 等）。位置从上到下：

| 区 | 键 | 屏幕位置 | 通常放什么 |
|---|---|---|---|
| 主区 | `primaryFields` | 票面最大一行 | 影片名 / 活动名 |
| 副区 | `secondaryFields` | 主区下方 | 验证码 / 时间 |
| 辅助区 | `auxiliaryFields` | 再下方两列 | 影院、座位、场次 |
| 背景区 | `backFields` | 点 ⓘ 才看到的背面 | 取票信息、客服电话、地址 |
| 页眉区 | `headerFields` | 票面右上角小字 | 不常用，可省略 |

每个 field 写法：

```json
{"key": "movie", "label": "影片", "value": "示例影片：星海"}
```

**value 的几种形态（均生效）**：

- 纯字符串：最常见。
- 日期对象：`{"key":"show","label":"场次","value":"2024-02-12T20:42:00Z","dateStyle":"medium","timeStyle":"short"}` —— iOS 按本机时区/格式渲染；不写 dateStyle/timeStyle 就原样显示字符串。
- 带换行：value 里用 `\r\n` 换行（背面信息常用，地址+电话分两行）。

**长度与字体缩放（实测）**：Wallet 按内容长度自动缩小字号。同一辅助区，座位行 23 字比 7 字明显小一档。**没有字号开关**——想字大就缩短文字。原版把座位全列（如 `7排6座,7排7座,7排8座`）就照原样列，别替它省略。

**key 规则**：同区内 key 必须唯一；跨区可重名（互不影响）。

---

## 5 条码

两张写法并存，缺一不可（旧版 `barcode` 单对象 + 新版 `barcodes` 数组）。iOS 以 `barcodes` 为准，但留着 `barcode` 更稳：

```json
"barcode":  {"format": "PKBarcodeFormatQR", "message": "13856042", "messageEncoding": "UTF-8"},
"barcodes": [{"format": "PKBarcodeFormatQR", "message": "13856042", "messageEncoding": "UTF-8"}]
```

| 键 | 取值 | 免签下 | 说明 |
|---|---|---|---|
| `format` | `PKBarcodeFormatQR` / `PKBarcodeFormatPDF417` / `PKBarcodeFormatAztec` | 生效 | 二维码 / 条形码 / Aztec |
| `message` | 字符串 | 生效 | **扫码后得到的内容**，通常是取票码；实测扫出来就是这个串 |
| `messageEncoding` | `"UTF-8"` | 生效 | 填 UTF-8 即可 |
| `altText` | 可选字符串 | 生效 | 条码下方可读文字 |

**message 末位规则（实测自样本）**：取票码去分隔符后若超过 8 位，条码 message 取末 8 位。例：完整码 `1385-6042` → 去分隔符 `13856042`（正好 8 位）→ message 用 `13856042`；若原码 `1385604288`（10 位）→ 取末 8 位 `85604288`。这不是 iOS 强制，是数据源本身的规律——你按自己数据定，重点是**扫出来要能核销**。

---

## 6 本地触发（免签唯一能用的通知路径，实测真弹）

| 键 | 类型 | 免签下 | 说明 |
|---|---|---|---|
| `relevantDate` | W3C 字符串 | **生效，实测弹** | 到点附近锁屏弹通知。例 `"2024-02-12T20:42:00Z"` |
| `locations` | 坐标数组 | **生效，实测弹 + 决定列表城市** | 进入围栏弹通知；同时决定列表是否显示城市（见下） |
| `maxDistance` | 数字（米） | 生效 | 地理围栏半径 |
| `beacons` | 蓝牙信标数组 | 生效 | 靠近指定信标弹通知 |
| `ignoresTimeZone` | 布尔 | 生效 | `relevantDate` 是否忽略时区（默认 false，按本机时区） |

`locations` 反查城市机制（实测关键）：列表显不显示城市，由 `locations` 坐标经 iOS 地图反查决定。

- 有 `locations` → 列表显示城市名（如「北京市」）。
- 无 `locations` → 列表只显示「活动门票」之类中性文案。

所以"显不显示城市"不是开关字段，是**有没有给坐标**的副产物。背面地址文字（`backFields[].value`）走另一套——iOS Data Detectors 自动识别成可点链接，不影响列表城市，也不需坐标。

---

## 7 状态与生命周期

| 键 | 类型 | 免签下 | 实测表现 / 填错后果 |
|---|---|---|---|
| `expirationDate` | W3C 字符串 | 生效 | 到点自动归档移出活跃列表（实测确认）。用 UTC，如 `"2024-02-12T22:30:00Z"` |
| `voided` | 布尔 | 生效 | 设 true 票面渲染出作废态（实测确认）。默认 false |
| `sharingProhibited` | 布尔 | 生效 | 设 true 长按不再出现分享/添加入口（实测确认）。默认 false |
| `passThatWasSet` | **对象**（整张 eventTicket 快照） | 生效，必填 | 见下，必须是对象不是字符串 |
| `groupingIdentifier` | 字符串 | 生效 | 同组多张票归一处显示。**不能含空格**，否则添加报错 |
| `appLaunchURL` | 字符串 | 生效 | 点票面唤起 App。**必须 `https://` 开头，否则报错** |
| `associatedStoreIdentifiers` | 数字数组 | 生效 | 填了票面出现「打开 App」入口（需 App 真在商店上架）。可不填 |

**`passThatWasSet`**（我们踩了三轮才定）：让 Wallet 知道「这张票最初长什么样」，用于判断用户是否改过、通知去重。免签下必须填，且**必须是 eventTicket 对象的深拷贝**，不是时间戳字符串、也不是 `{datetime, timestamp}` 对象。

错误写法（实测无效）：
```json
"passThatWasSet": "2024-02-12T20:42:00Z"          // 字符串 → 无效
"passThatWasSet": {"date": "2024-02-12T20:42:00Z"} // 对象但结构不对 → 无效
```
正确写法（与 `eventTicket` 同构的一份副本）：
```json
"passThatWasSet": { "primaryFields": [...], "secondaryFields": [...], "auxiliaryFields": [...], "backFields": [...] }
```

**为什么设过去时间**：生成时设成「当前时刻 − 24 小时」的场次时间，能避免 Wallet 的「刚刚更新」检测把通知设置重置。设成未来或当前时刻，部分版本会清掉刚开的通知开关。

---

## 8 语义 semantics（生效，必须嵌 eventTicket 内）

`semantics` 给 iOS 系统理解票内容，用于 Spotlight 搜索、钱包智能分类。它**必须放在 `eventTicket` 内部**，提到 pass.json 顶层实测触发字段级防火墙，票直接加不进去。

| 键 | 含义 | 取值 | 免签下 |
|---|---|---|---|
| `eventStartDate` | 活动开始 | W3C 字符串 | 生效，Spotlight 可搜到 |
| `eventEndDate` | 活动结束 | W3C 字符串 | 生效 |
| `eventName` | 活动名 | 字符串 | 生效 |
| `venueName` | 场馆名 | 字符串 | 生效 |
| `venueLocation` | 场馆坐标 | `{latitude, longitude}` | 生效 |
| `genre` | 类型 | 字符串 | 生效 |

`eventStartDate` / `eventEndDate` 和 `relevantDate` 是两套东西：前者喂系统语义理解，后者管锁屏通知触发。两者都给最稳。

---

## 9 必删清单（写了就炸，与第 0 节一致）

这些在免签下必须没有，留着反而坏事：

| 目标 | 动作 | 原因（实测） |
|---|---|---|
| `signature` 文件 | 不写进 zip | 留着 iOS 反而要验签，失败被拒 |
| `webServiceURL` | 从 pass.json 删除 | 免签 + 此字段添加阶段硬拒（12 轮全失败，含 5 轮 HTTPS） |
| `authenticationToken` | 从 pass.json 删除 | webServiceURL 的鉴权凭据，二者绑死，删一个必删另一个 |
| `nfc` / `transitType` | eventTicket 不写 | eventTicket 不支持，写了报错；generic 样式可实验性支持 |
| `storeCard` 样式 | 换 eventTicket / generic | storeCard 免签拒收 |
| `background.png` / `strip.png` | 不写 | 免签渲染器丢弃，写了白写 |

---

## 10 改完必做：重算 manifest

任何对 `pass.json` 字符、任何图片字节的改动，都必须重算 `manifest.json` 对应文件的 SHA-1，否则添加时报「凭证无效」拒收。**没有捷径，改一处算一处。**

算法：对每个包内文件（不含 manifest.json 本身、不含 signature）算 `sha1_hex`，写成 `{文件名: 哈希}` 的 JSON，UTF-8 编码写回 `manifest.json`，zip 用 `ZIP_DEFLATED` 重打包。代码见 `examples/build_pass.py` 的 `rebuild()`，但那只是工具——参数对不对才是这张票能不能用的关键。

### SHA-256 风险（iOS 28+ 预警）

⚠️ 当前 `.pkpass` 规范的 `manifest` 是 **SHA-1** 清单，iOS 27 beta 4 实测通过。但苹果在 iOS 17 已把 App Store 收据校验全面迁移到 SHA-256，Wallet 的 manifest 校验未来存在同步升级可能。

若 iOS 未来版本要求 SHA-256，需把 `examples/build_pass.py` 的 `rebuild()` 里 `hashlib.sha1(data)` 换成 `hashlib.sha256(data)`，其余打包逻辑不变。本项目**不保证对 iOS 27 之后版本向前兼容，需重新真机验证**。

---

## 11 iOS 27 新增字段（仅 poster event ticket 生效）

`transferURL` / `changeSeatURL` / `auxiliaryStoreIdentifiers` 只对 poster event ticket 样式生效。普通 `eventTicket`（本项目模板即此类）填了**不报错也不生效**——容易以为是 bug，其实是样式限制。

| 字段 | 生效条件 | 说明 |
|---|---|---|
| `transferURL` | poster event ticket | 转赠入口 URL |
| `changeSeatURL` | poster event ticket | 改座入口 URL |
| `auxiliaryStoreIdentifiers` | poster event ticket | 关联商店 ID 数组 |

普通 eventTicket 直接不填。要启用需换 poster event ticket 样式并真机验证——超出当前免签壳实测范围，先标记待验证。

---

## 附：一张能用的票长什么样（最小字段集）

```json
{
  "formatVersion": 1,
  "teamIdentifier": "com.apple.wallet",
  "passTypeIdentifier": "userpass.com.apple.wallet.<每次换uuid>",
  "serialNumber": "<同PTI唯一>",
  "organizationName": "示例影城",
  "description": "示例影城02月12日示例影片影票3张",
  "backgroundColor": "rgb(22,42,78)",
  "foregroundColor": "rgb(255,255,255)",
  "labelColor": "rgb(190,205,230)",
  "logoText": "DEMO PASS",
  "barcode":  {"format": "PKBarcodeFormatQR", "message": "13856042", "messageEncoding": "UTF-8"},
  "barcodes": [{"format": "PKBarcodeFormatQR", "message": "13856042", "messageEncoding": "UTF-8"}],
  "eventTicket": {
    "primaryFields":      [{"key":"movie","label":"影片","value":"示例影片：星海"}],
    "secondaryFields":    [{"key":"exchangeCode","label":"验证码","value":"1385-6042"}],
    "auxiliaryFields":    [
      {"key":"cinemaName","label":"影院","value":"示例国际影城"},
      {"key":"seats","label":"座位","value":"7排6座,7排7座,7排8座"},
      {"key":"show","label":"场次","value":"2月12日 周一 20:42"}
    ],
    "backFields": [
      {"key":"cinemaInfo","label":"影院信息","value":"地址：示例市示例路1号\r\n电话：1010-5335"},
      {"key":"takeTicketInfo","label":"取票信息","value":"2月12日20:42示例国际影城..."},
      {"key":"customerServicePhone","label":"客服电话","value":"1010-5335"}
    ],
    "semantics": {"eventStartDate":"2024-02-12T20:42:00Z","venueName":"示例国际影城"}
  },
  "passThatWasSet": { "primaryFields":[...], "secondaryFields":[...], "auxiliaryFields":[...], "backFields":[...] },
  "relevantDate": "2024-02-12T20:42:00Z",
  "expirationDate": "2024-02-12T22:30:00Z",
  "sharingProhibited": false
}
```

配套图片至少 `icon.png` + `icon@2x.png`，否则添加报错。

---

## 实测来源

- 全部在 **iOS 27 beta 4** 真机环境验证
- 40+ 次壳实验（不同字段组合的 pass.json 真机添加）
- 5 个原版品牌样本逐字段比对（猫眼、万达、携程、淘票票、iTunes）
- 12 轮 `webServiceURL` 实验（5 轮正经 HTTPS，全失败）
- `passThatWasSet` 三种写法对比（字符串 / 错误对象 / eventTicket 深拷贝）
- `sharingProhibited` / `voided` / `groupingIdentifier` / `associatedStoreIdentifiers` / `appLaunchURL` 生效场景逐一实测

样本均不在本仓库。AnyWallet 公开的部分只有算法、字段手册、一份去品牌模板。
