# 参数全解

> AnyWallet 归根结底是一件事：把一张带签名的 `.pkpass` 改写成免签名、仍能被 iOS Wallet 添加的 `.pkpass`。
> 这一篇只讲**参数**——一张 `pass.json` 里每个字段：免签下**生不生效**、**怎么填**、**填错会怎样**、**代码里怎么用**。结论全部来自真机实测（**iOS 27 beta 4**，40+ 次壳实验）与项目内的实测脚本（`maoyan_to_wallet.py` / `wanda_to_wallet.py` / `build_pass.py`）。

---

## 0 先说结论：免签壳到底能覆盖什么

### 能生效的场景（实测确认）

| 能力 | 字段 | 实测表现 |
|---|---|---|
| 票面完整布局 | `eventTicket` 五区（primary/secondary/auxiliary/back/header） | 渲染正常，和签名版无差异 |
| 颜色与文字 | `backgroundColor` / `foregroundColor` / `labelColor` / `logoText` / `organizationName` / `description` | 正常 |
| 二维码 / 条形码 | `barcode` + `barcodes`（含 `altText`） | 扫码出 `message` 内容，正常核销 |
| 缩略图 | `thumbnail`（`@2x`/`@3x`） | 票面右侧正常显示 |
| 本地触发通知 | `relevantDate` / `locations` / `beacons` / `maxDistance` / `ignoresTimeZone` | **实测真弹锁屏通知**（relevantDate 到点、进围栏都验证过） |
| 列表显示城市 | `locations` 坐标 | 有坐标→列表显示城市；无坐标→只显示「活动门票」 |
| 背面地址可点 | `backFields` 里写地址/电话文字 | iOS Data Detectors 自动识别成链接，实测可点 |
| 过期归档 | `expirationDate` | 到点自动移出活跃列表，实测确认 |
| 禁止分享 | `sharingProhibited` | **生效**：设 true 长按不再出现分享/添加入口（万达脚本实测开启） |
| 标记作废 | `voided` | **生效**：票面渲染出作废态 |
| 分组显示 | `groupingIdentifier` | 生效：同组多张票归在一处 |
| 语义理解 | `semantics`（嵌套 `eventTicket` 子键） | 生效：Spotlight 可搜到、钱包智能分类生效（02/03/06 实验确认） |
| 关联 App 入口 | `associatedStoreIdentifiers` | 生效：票面出现「打开 App」入口（需 App 真在商店上架） |
| 唤醒 App | `appLaunchURL` | 生效：点票面唤起对应 https App |
| 鉴权令牌 | `authenticationToken` | 免签下**可留可删**（见第 7 节，实测带令牌也能添加） |
| 自定义数据 | `userInfo` | 生效：不显示，仅供 App/系统内部读取 |
| 免签身份 | `teamIdentifier=com.apple.wallet` + `passTypeIdentifier=userpass.com.apple.wallet.<uuid>` | 放行，跳过验签 |

### 不能生效 / 必删的场景（实测确认）

| 能力 | 字段 | 实测表现 |
|---|---|---|
| 服务器推送 | `webServiceURL` | **硬拒**：免签 + 此字段在添加阶段直接打不开（12 轮实验全失败，含 5 轮正经 HTTPS） |
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
| `thumbnail.png` / `thumbnail@2x.png` / `thumbnail@3x.png` | 票面右侧缩略图 | 可选，但尺寸须与模板一致 |
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
  "semantics": { "eventTicket": { ... } },
  "passThatWasSet": { ... },
  "relevantDate": "2024-02-12T20:42:00Z",
  "expirationDate": "2024-02-12T22:30:00Z",
  "locations": [ { "latitude": 39.92, "longitude": 116.47, "relevantText": "示例影城" } ],
  "sharingProhibited": false,
  "associatedStoreIdentifiers": [504274740],
  "userInfo": { "generator": "your-script" }
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

**两个必须每次变的量**（同一规则的两种表现，不是两条独立要求）：

- `passTypeIdentifier` 末尾 `<uuid>`：**每次生成都换**（`uuid4().hex`）。
- `serialNumber`：建议带随机性（如 `t.` + 随机串，猫眼批量脚本实测用 `t.` + uuid 前 12 位）。

原因只有一条：**同一 `passTypeIdentifier` 下，`serialNumber` 不能重复**。两次生成若 PTI 相同、serialNumber 不同，Wallet 列表只留一张。所以只要保证"每次生成 PTI 换新 uuid"，serialNumber 撞车概率就趋于零。

`formatVersion`、`teamIdentifier` 是死的，别动。

---

## 3 外观与标识

| 键 | 取值 | 免签下 | 说明 |
|---|---|---|---|
| `organizationName` | 字符串 | 生效 | 锁屏通知、Wallet 列表显示的发行方名；**不是**票面大字 |
| `description` | 字符串 | 生效 | 无障碍/搜索描述。实测规律：`{影院}{MM}月{DD}日{影片}影票N张`（猫眼样本）；你自己定，关键是简介可读 |
| `backgroundColor` / `foregroundColor` / `labelColor` | `rgb(r,g,b)` 或 `#RRGGBB` | 生效 | 底色 / 主文字色 / 标签色；三者需足够对比，否则部分机型字段看不清（不报错，只是难看） |
| `logoText` | 字符串 | 生效 | 左上角 logo 旁纯文字（无 logo 图也能显示文字标）。原版无此字段时可不主动添加，忠于模板 |

颜色实测：免签渲染器 `rgb()` 和 `#` 两种写法都认。无 `background.png` 时，可用 `backgroundColor` 做底色补偿（万达脚本实测用暖米底色补偿背景图不可渲染）。

---

## 4 票面五区（eventTicket 专属，全部生效）

`eventTicket` 内分五个数组，每个元素是 `{key, label, value}`（可带 `attributedValue` / `dateStyle` 等）。位置从上到下：

| 区 | 键 | 屏幕位置 | 通常放什么 |
|---|---|---|---|
| 主区 | `primaryFields` | 票面最大一行 | 影片名 / 活动名 |
| 副区 | `secondaryFields` | 主区下方 | 验证码 / 时间 |
| 辅助区 | `auxiliaryFields` | 再下方两列 | 影院、座位、场次 |
| 背景区 | `backFields` | 点 ⓘ 才看到的背面 | 取票信息、客服电话、地址 |
| 页眉区 | `headerFields` | 票面右上角小字 | **堆叠头**：多张票在 Wallet 里叠在一起时，唯一可见的就是 headerFields（最多 3 个），用于快速区分 |

每个 field 写法：

```json
{"key": "movie", "label": "影片", "value": "示例影片：星海"}
```

**value 的几种形态（均生效）**：

- 纯字符串：最常见。
- 日期对象：`{"key":"show","label":"场次","value":"2024-02-12T20:42:00Z","dateStyle":"medium","timeStyle":"short"}` —— iOS 按本机时区/格式渲染；不写 dateStyle/timeStyle 就原样显示字符串。
- 带换行：value 里用 `\r\n`（猫眼原版）或 `\n`（万达脚本）换行，背面信息常用，地址+电话分两行。

**长度与字体缩放（实测）**：Wallet 按内容长度自动缩小字号。同一辅助区，座位行 23 字比 7 字明显小一档。**没有字号开关**——想字大就缩短文字。原版把座位全列（如 `7排6座,7排7座,7排8座`）就照原样列，别替它省略。

**key 规则**：同区内 key 必须唯一；跨区可重名（互不影响）。

**背面字段顺序**：`backFields` 数组顺序即显示顺序，可按需重排（万达脚本按 `cinemaInfo → takeTicketInfo → customerServicePhone` 等顺序重建）。

---

## 5 图片规格（免签渲染器对图片有硬约束）

图片是免签下最容易踩坑的地方——不是"放了就行"，尺寸和命名都有讲究。

| 图片 | 作用 | 规格要求（实测） |
|---|---|---|
| `icon.png` / `icon@2x.png` | 列表缩略图标 | **必须有**，否则添加报错。尺寸从模板继承（样本实测有 29×29/58×58 与 50×50/25×25 两种），**用原版尺寸，别写死** |
| `logo.png` / `logo@2x.png` | 票面左上角标志 | 可选。尺寸样本实测 319×80 / 639×160 |
| `thumbnail.png` / `thumbnail@2x.png` / `thumbnail@3x.png` | 票面右侧缩略图 | 可选。尺寸样本实测 68×95 与 67×90 两种（**同品牌不同票都不同**），换壳时从模板运行时读取，写死必错 |
| `background.png` / `strip.png` | 背景/横幅 | **免签丢弃**，别放 |

**关键规则（实测反复验证）**：

- **尺寸绝不硬编码**。同一品牌不同票，thumbnail 实测有 68×95 和 67×90 两种，icon 有 50×50 和 25×25 两种。换壳脚本必须从模板运行时读取尺寸，写死一种必错。
- **双图/@3x 命名**：`@2x`、`@3x` 是 iOS 多分辨率约定，按模板现有命名保留（猫眼脚本遍历 `thumbnail.png`/`thumbnail@2x.png`/`thumbnail@3x.png` 逐个替换）。
- **封面替换用 3:4 居中裁切**：把海报塞进 thumbnail 时按目标宽高比居中裁切（猫眼脚本 `fit_cover` 实测），避免拉伸变形。
- `logo`/`icon` 可保留原版品牌图，只换 `thumbnail` 海报位——去品牌时只动 thumbnail。

---

## 6 条码

两张写法并存，缺一不可（旧版 `barcode` 单对象 + 新版 `barcodes` 数组）。iOS 以 `barcodes` 为准，但留着 `barcode` 更稳：

```json
"barcode":  {"format": "PKBarcodeFormatQR", "message": "13856042", "messageEncoding": "UTF-8", "altText": "取票码 13856042"},
"barcodes": [{"format": "PKBarcodeFormatQR", "message": "13856042", "messageEncoding": "UTF-8", "altText": "取票码 13856042"}]
```

| 键 | 取值 | 免签下 | 说明 |
|---|---|---|---|
| `format` | `PKBarcodeFormatQR` / `PKBarcodeFormatPDF417` / `PKBarcodeFormatAztec` | 生效 | 二维码 / 条形码 / Aztec |
| `message` | 字符串 | 生效 | **扫码后得到的内容**，通常是取票码；实测扫出来就是这个串 |
| `messageEncoding` | `"UTF-8"` | 生效 | 填 UTF-8 即可 |
| `altText` | 可选字符串 | 生效 | 条码下方可读文字，通常 `取票码 XXXXXXXX`（万达/猫眼脚本均注入） |

**message 末位规则（实测自猫眼样本）**：取票码去分隔符后若超过 8 位，条码 message 取末 8 位。例：完整码 `1385-6042` → 去分隔符 `13856042`（正好 8 位）→ message 用 `13856042`；若原码 `1385604288`（10 位）→ 取末 8 位 `85604288`。这不是 iOS 强制，是数据源本身的规律——你按自己数据定，重点是**扫出来要能核销**。

---

## 7 本地触发（免签唯一能用的通知路径，实测真弹）

| 键 | 类型 | 元素结构 | 免签下 | 说明 |
|---|---|---|---|---|
| `relevantDate` | W3C 字符串 | — | **生效，实测弹** | 到点附近锁屏弹通知。应与显示场次时间**单一来源一致**（万达脚本：relevantDate 与 `show` 字段用同一 `show_dt`，不再独立计算） |
| `locations` | 坐标数组 | `{latitude, longitude, relevantText}` | **生效，实测弹 + 决定列表城市** | `relevantText` 进场时显示；坐标同时决定列表是否显示城市 |
| `maxDistance` | 数字（米） | — | 生效 | 地理围栏半径，实测用 500 |
| `beacons` | 蓝牙信标数组 | `{major, minor, proximityUUID, relevantText}` | 生效 | 靠近指定信标弹通知；`proximityUUID` 用标准 UUID 格式 |
| `ignoresTimeZone` | 布尔 | — | 生效 | `relevantDate` 是否忽略时区（默认 false，按本机时区）；实测脚本多设 true |

`locations` 反查城市机制（实测关键）：列表显不显示城市，由 `locations` 坐标经 iOS 地图反查决定。

- 有 `locations` → 列表显示城市名（如「北京市」）。
- 无 `locations` → 列表只显示「活动门票」之类中性文案。

所以"显不显示城市"不是开关字段，是**有没有给坐标**的副产物。背面地址文字（`backFields[].value`）走另一套——iOS Data Detectors 自动识别成可点链接，不影响列表城市，也不需坐标。

**关于 `authenticationToken`**：它是 `webServiceURL` 拉取 pass 更新的鉴权凭据。文档曾写"必须删除"——**实测纠正**：免签下**没有 `webServiceURL` 时，留着 `authenticationToken` 无害，带令牌的票照样能添加**（猫眼/万达/build_pass 三个脚本都主动写入 `my_xxx`/`wd_xxx` 令牌且实测通过）。唯一硬规则是：**`webServiceURL` 必删；`authenticationToken` 可留可删，删了更干净**。

---

## 8 状态与生命周期

| 键 | 类型 | 免签下 | 实测表现 / 填错后果 |
|---|---|---|---|
| `expirationDate` | W3C 字符串 | 生效 | 到点自动归档移出活跃列表（实测确认）。规律：场次结束时刻 +2h（猫眼/万达脚本均按此，非写死） |
| `voided` | 布尔 | 生效 | 设 true 票面渲染出作废态。默认 false |
| `sharingProhibited` | 布尔 | 生效，可选项 | 设 true 长按不再出现分享/添加入口（万达脚本实测开启）；猫眼脚本主动设 false 允许分享。**两种都实测过，按你需求定** |
| `passThatWasSet` | **对象**（整张 eventTicket 快照） | 生效，必填 | 见下，必须是对象不是字符串 |
| `groupingIdentifier` | 字符串 | 生效 | 同组多张票归一处显示。**不能含空格**，否则添加报错（脚本实测用 `movie-stub` 这类无空格串） |
| `appLaunchURL` | 字符串 | 生效 | 点票面唤起 App。**必须 `https://` 开头，否则报错**（脚本实测：非 https 一律改写为 https） |
| `associatedStoreIdentifiers` | 数字数组 | 生效 | 填了票面出现「打开 App」入口（需 App 真在商店上架）。可不填 |
| `userInfo` | 对象 | 生效，**不显示** | 自定义键值对，仅供 App/系统内部读取，票面不渲染（三个脚本都注入 generator/version/generatedAt 元数据） |

**`passThatWasSet`**（我们踩了三轮才定）：让 Wallet 知道「这张票最初长什么样」，用于判断用户是否改过、通知去重。免签下必须填，且**必须是 eventTicket 对象的深拷贝**（即把 `eventTicket` 整个结构再写一份进来），不是时间戳字符串、也不是 `{datetime, timestamp}` 对象。

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

## 9 语义 semantics（生效，必须嵌 eventTicket 子键）

`semantics` 给 iOS 系统理解票内容，用于 Spotlight 搜索、钱包智能分类、日历/地图集成。它**必须放在 `eventTicket` 子键下**，且**只放良性子键**——提到 pass.json 顶层、或整对象塞 `eventTicket` 同级，实测触发字段级防火墙，票直接加不进去。

**安全写法（02/03/06 壳实验确认可加）**：
```json
"semantics": {
  "eventTicket": {
    "eventStartDate": "2024-02-12T20:42:00Z",
    "eventEndDate":   "2024-02-12T22:30:00Z",
    "eventType": "movie",
    "venue": {
      "name": "示例国际影城",
      "location": {"latitude": 39.9215, "longitude": 116.4766}
    }
  }
}
```

| 键 | 含义 | 取值 | 免签下 |
|---|---|---|---|
| `eventTicket` | 容器子键（必写） | 对象 | 良性子键放这里面才安全 |
| `eventStartDate` / `eventEndDate` | 活动起止 | W3C 字符串 | 生效，日历集成 |
| `eventType` | 活动类型 | `"movie"` / `"generic"` 等 | 生效（按票种选） |
| `venue.name` | 场馆名 | 字符串 | 生效，地图集成 |
| `venue.location` | 场馆坐标 | `{latitude, longitude}` | 生效 |

`eventStartDate` / `eventEndDate` 和 `relevantDate` 是两套东西：前者喂系统语义理解，后者管锁屏通知触发。两者都给最稳。

---

## 10 必删清单（写了就炸，与第 0 节一致）

这些在免签下必须没有，留着反而坏事：

| 目标 | 动作 | 原因（实测） |
|---|---|---|
| `signature` 文件 | 不写进 zip | 留着 iOS 反而要验签，失败被拒 |
| `webServiceURL` | 从 pass.json 删除 | 免签 + 此字段添加阶段硬拒（12 轮全失败，含 5 轮 HTTPS） |
| `nfc` / `transitType` | eventTicket 不写 | eventTicket 不支持，写了报错；generic 样式可实验性支持 |
| `storeCard` 样式 | 换 eventTicket / generic | storeCard 免签拒收 |
| `background.png` / `strip.png` | 不写 | 免签渲染器丢弃，写了白写 |

> 注：`authenticationToken` 不在必删之列——无 `webServiceURL` 时留着无害（见第 7 节）。

---

## 11 改完必做：重算 manifest

任何对 `pass.json` 字符、任何图片字节的改动，都必须重算 `manifest.json` 对应文件的 SHA-1，否则添加时报「凭证无效」拒收。**没有捷径，改一处算一处。**

算法：对每个包内文件（不含 manifest.json 本身、不含 signature）算 `sha1_hex`，写成 `{文件名: 哈希}` 的 JSON，UTF-8 编码写回 `manifest.json`，zip 用 `ZIP_DEFLATED` 重打包。代码见 `examples/build_pass.py` 的 `rebuild()`，但那只是工具——参数对不对才是这张票能不能用的关键。

### SHA-256 风险（iOS 28+ 预警）

⚠️ 当前 `.pkpass` 规范的 `manifest` 是 **SHA-1** 清单，iOS 27 beta 4 实测通过。但苹果在 iOS 17 已把 App Store 收据校验全面迁移到 SHA-256，Wallet 的 manifest 校验未来存在同步升级可能。

若 iOS 未来版本要求 SHA-256，需把 `examples/build_pass.py` 的 `rebuild()` 里 `hashlib.sha1(data)` 换成 `hashlib.sha256(data)`，其余打包逻辑不变。本项目**不保证对 iOS 27 之后版本向前兼容，需重新真机验证**。

---

## 12 iOS 27 新增字段（仅 poster event ticket 生效）

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
  "serialNumber": "t.<随机串>",
  "organizationName": "示例影城",
  "description": "示例影城02月12日示例影片影票3张",
  "backgroundColor": "rgb(22,42,78)",
  "foregroundColor": "rgb(255,255,255)",
  "labelColor": "rgb(190,205,230)",
  "barcode":  {"format": "PKBarcodeFormatQR", "message": "13856042", "messageEncoding": "UTF-8", "altText": "取票码 13856042"},
  "barcodes": [{"format": "PKBarcodeFormatQR", "message": "13856042", "messageEncoding": "UTF-8", "altText": "取票码 13856042"}],
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
    ]
  },
  "semantics": {
    "eventTicket": {
      "eventStartDate": "2024-02-12T20:42:00Z",
      "eventEndDate":   "2024-02-12T22:30:00Z",
      "eventType": "movie",
      "venue": {"name": "示例国际影城", "location": {"latitude": 39.9215, "longitude": 116.4766}}
    }
  },
  "passThatWasSet": { "primaryFields":[...], "secondaryFields":[...], "auxiliaryFields":[...], "backFields":[...] },
  "relevantDate": "2024-02-12T20:42:00Z",
  "locations": [{"latitude": 39.9215, "longitude": 116.4766, "relevantText": "示例国际影城"}],
  "expirationDate": "2024-02-12T22:30:00Z",
  "sharingProhibited": false,
  "userInfo": {"generator": "your-script"}
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
- `semantics` 顶层整对象 vs `eventTicket` 子键对比（02/03/06 实验确认子键安全）
- `sharingProhibited` / `voided` / `groupingIdentifier` / `appLaunchURL` / `associatedStoreIdentifiers` / `userInfo` / `authenticationToken` 生效场景逐一实测（见 `maoyan_to_wallet.py` / `wanda_to_wallet.py` / `build_pass.py`）

样本均不在本仓库。AnyWallet 公开的部分只有算法、字段手册、一份去品牌模板。
