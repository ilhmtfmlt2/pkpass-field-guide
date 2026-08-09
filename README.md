<img src="assets/icon.png" width="96" align="right">

# Apple 免签 `.pkpass` 工具集

iPhone 自带 Wallet，谁都能往里塞票。但正经搞电影票、演出票的厂商要走 PassKit 开发者账号、申请 Pass Type ID、签证书、上 APNs 推送——门槛不低。本项目另辟蹊径：借 iOS "Create a Pass" 自带的 `com.apple.wallet` 系统身份当壳子，**不签证书、不开 APNs**，照样把任意 `.pkpass` 塞进用户的 Wallet。

仓库里是这套机制的完整沉淀：免签壳怎么成、哪些字段能动哪些不能动、每个字段到底是什么含义、怎么基于现有工具二次开发一个新品牌的票根。结论全部来自真机实测，不照抄 Apple 文档——40 多次壳实验 + 5 个原版品牌（猫眼/万达/携程/淘票票/iTunes）逐字段对比，够你少走几个月弯路。

## 实际效果

下面这张是真机 AirDrop 后在 Wallet 里渲染出来的票面截图，已经做过精细抠图、背景透明，方便直接嵌文档。视觉效果就是真机添加后的样子，字段全在显示区，二维码可扫，颜色与原版一致。

![图 1 免签壳生成的猫眼票根在 iPhone Wallet 中的实际渲染效果（真机截图）](assets/preview.png)

| 项目 | 值 |
|---|---|
| passTypeIdentifier | `userpass.com.apple.wallet.<uuid>` |
| teamIdentifier | `com.apple.wallet` |
| style | eventTicket |
| 颜色 | `rgb(133,19,10)` |
| 本地触发字段 | relevantDate + locations + beacons + ignoresTimeZone |
| 语义集成 | semantics.eventTicket（电影类型） |
| 真签名 | 无 |

## 免签壳到底是怎么回事

`.pkpass` 本质是 zip：

```
xxx.pkpass/
├── pass.json          # 票面所有数据
├── manifest.json      # 包内每个文件的 SHA-1 清单
├── icon.png / logo.png / thumbnail.png ...
└── signature          # 开发者证书对 manifest 的签名（免签没有）
```

正常流程：开发者拿证书签 `manifest.json`，生成 `signature`，Wallet 验签通过才收。免签的思路是**借身份不借证书**——iOS 自己的 "Create a Pass" 用 `com.apple.wallet` 这个 Team ID 出 pass（用户在备忘录 App 里就能干这事）。我们把一张第三方票的 `teamIdentifier` 改成 `com.apple.wallet`、`passTypeIdentifier` 改成 `userpass.com.apple.wallet.<uuid>`，把 `signature` / `webServiceURL` / `authenticationToken` 三个跟证书绑死的字段全删，iOS 看到 `com.apple.wallet` 就当"系统自己出的票"放行——签名链这一步直接绕开。

代价也是物理性的：免签用的是 Apple 自己的身份，**你拿不到对应 Pass Type ID 的 APNs 证书**，所以服务器推送这条路永远走不通。通知只能退而求其次走本地触发字段（`relevantDate` / `locations` / `beacons`），这是后文第二节会反复强调的硬约束。

改了包内任何东西（`pass.json` 任何字符、任何一张图），都得重算 `manifest.json` 里对应文件的 SHA-1，否则 Wallet 添加时直接报"凭证无效"拒收。本仓库里 `build_pass.py`、`passkit_rebuilder.py`、前端生成器都内建这一步。

## 哪些能签、哪些不能签

这是整个文档里最重要的一节。免签不是"啥都能填"，下面两张表是硬边界。

### 能动的字段（填了就生效）

| 字段 | 说明 |
|---|---|
| 身份：`formatVersion` / `serialNumber` / `organizationName` / `description` | 必填身份，照常填 |
| 外观：`backgroundColor` / `foregroundColor` / `labelColor` / `logoText` | 控制文字与背景色，不影响图片像素 |
| 票面：`headerFields` / `primaryFields` / `secondaryFields` / `auxiliaryFields` / `backFields` | 票上显示的所有文字区域 |
| 条码：`barcode` / `barcodes` | 二选一，至少留一个 |
| 本地触发：`relevantDate` / `locations` / `maxDistance` / `beacons` / `ignoresTimeZone` | 通知唯一路径 |
| 语义：`semantics` | 让 iOS 把这张票当电影/演出/体育票来对待，开日历/地图/Siri 集成 |
| 杂项：`groupingIdentifier` / `appLaunchURL` / `associatedStoreIdentifiers` / `userInfo` | 分组、跳转、关联 App、调用方可读元数据 |
| 状态：`expirationDate` / `passThatWasSet` / `voided` / `sharingProhibited` | 过期归档、通知防重置、作废、禁分享 |

### 碰了就炸（致命区）

| 字段 | 结论 |
|---|---|
| `webServiceURL` | **死刑**。免签身份 + 这个 = iOS 添加阶段直接打不开，跟 HTTP/HTTPS 没关系——壳实验做了 12 轮，其中 5 轮用的是正经 HTTPS 地址（apple.com、meituan 域名），照样失败。根因有二：(1) 免签身份 + webServiceURL 这个组合在添加时被 iOS 硬拒；(2) 服务器推送要 APNs 证书，而免签用的 `com.apple.wallet` 是 Apple 自己的，你拿不到对应 Pass Type ID 的证书。所以免签 pass 永远不要碰这个字段 |
| `signature` | 免签没有，包完整性靠 `manifest.json` 的 SHA-1 就够了 |
| `authenticationToken` | 签名链的一环，免签下无意义，去掉 |
| `storeCard` 样式 | 免签渲染器拒收，要做余额卡得换成 `eventTicket`（或 `generic`） |
| `background.png` / `strip.png` | 免签渲染器直接丢弃，填了也白填 |
| `nfc` | 只支持 `boardingPass` / `storeCard`，`eventTicket` 用不了 |
| `transitType` | `boardingPass` 专用 |

记住一句话就够了：**身份三键按免签规则改写、所有"显示类"和"本地触发类"字段照常填、凡是依赖开发者证书或服务器的全删**。剩下的就是自由区。

## pass.json 字段全解

下面对所有常见字段逐一过。每个字段给出类型、是否必填、含义、在免签下的状态。状态分三档：**可用** / **可用但可选** / **移除**（见上一节致命区表）。

### 身份字段（缺一个都加不进去）

- `formatVersion` — 整数，必填。写死 `1`，目前只有这一个值。
- `teamIdentifier` — 字符串，必填。免签固定 `com.apple.wallet`。这是借壳的关键，改回真实 Team ID iOS 直接不认。
- `passTypeIdentifier` — 字符串，必填。格式 `userpass.com.apple.wallet.<uuid>`。每次生成换 uuid，避免和已有 pass 冲突（同一个 PTI 下 serialNumber 不能重复）。
- `serialNumber` — 字符串，必填。同一 `passTypeIdentifier` 下唯一。要发新版覆盖旧版就保持 serialNumber 不变，否则每次随机；猫眼原版用 `t.` 前缀如 `t.23325946120`，纯属风格，无功能含义。
- `organizationName` — 字符串，必填。锁屏通知和列表里显示的组织名（"来自 XXX 的票券"）。
- `description` — 字符串，必填。VoiceOver 朗读用，也出现在列表的辅助文字。Apple 建议格式 `{类型}：{标题} - {地点} {时间}`，比如 `电影票：星海 - 示例国际影城 2月12日`。

### 外观

- `backgroundColor` / `foregroundColor` / `labelColor` — `rgb(r,g,b)` 字符串，可选。分别控制整体背景、文字、字段标签颜色。**只影响画在图片之外的文字，不动图片像素**。颜色想覆盖到 icon/logo/thumbnail？那是图片本身的活，这三个字段管不到。
- `logoText` — 字符串，可选。logo 图片旁的替代文字；不设就只显示 logo 图片。

### 条码

- `barcode`（单对象）和 `barcodes`（数组，iOS 9+ 多格式降级）二选一，至少留一个，否则添加时会警告。`format` 支持 `PKBarcodeFormatQR` / `Aztec` / `Code128` / `PDF417`，电影票基本都是 QR。`message` 是扫码得到的内容，`messageEncoding` 固定 `"UTF-8"`，`altText` 可选（扫码区下方的小字、无障碍朗读用）。

有个真坑要提：票面显示的验证码和二维码内容**可以是两个字符串**。猫眼原版里取票码超过 8 位时，二维码只取末 8 位（票面 `4107420189672635`、二维码 `89672635`），不超过 8 位才取完整。照原版填就会发现这俩对不上号，不是 bug。生成时统一按下面处理：

```python
raw = re.sub(r"[\s-]", "", code)
message = raw[-8:] if len(raw) > 8 else raw
```

### 票面内容：`eventTicket`

所有可见文字挂在 `eventTicket` 这个对象下，按区域分五个 section，Wallet 自动排版：

| section | 角色 | 数量 | 干啥用 |
|---|---|---|---|
| `headerFields` | 堆叠时可见 | ≤3 | 多张票叠一起时**只有这块露出来**，强烈建议填 |
| `primaryFields` | 主标题 | 1~2 | 最大字号，通常放片名 |
| `secondaryFields` | 次要 | 1~2 | 略小，放验证码 |
| `auxiliaryFields` | 辅助 | ≤5 | 小字三连，放影院/座位/场次 |
| `backFields` | 背面 | 不限 | 点 ⓘ 翻面，放地址/电话/说明 |

每个字段统一结构：`{ "key": "唯一键", "label": "标签", "value": "显示内容" }`。`key` 给自己定位用，`label` 才是用户看到的小字标题。

区域排版见 [assets/field-layout.svg](assets/field-layout.svg)。

两个常栽的坑：

**字体缩放**——Wallet 按字段内容长度自动缩字号。同一张模板，座位写 `7排6座` 和写 `4厅激光厅 7排6座、7排7座、7排8座`，后者会被压小一截。这不是 bug，是渲染策略。想字大就缩短文字，代价是信息量缩水。

**背面跳地图不需要 `locations`**——在 `backFields` 里写一段真实地址文字（如 `地址：示例市示例路1号`），iOS 的 Data Detectors 会自动把它变成蓝色可点链接，跳 Apple 地图。电话、网址同理。完全不用坐标，也不影响列表城市反查——后者只认 `locations` 和 `semantics.venue.location`。

### 本地触发（免签下通知的唯一路径）

- `relevantDate` — W3C 时间字符串，可选。**最重要**——到点附近锁屏弹通知。
- `locations` — `[{latitude, longitude, relevantText}]`，可选。进入坐标范围弹通知，同时**会让列表/归档反查出城市名**（如"新乡市，河南省"）。不想显城市就别加。
- `maxDistance` — 整数（米），`locations` 的触发半径。
- `beacons` — iBeacon 触发，需要现场硬件，一般用不上。
- `ignoresTimeZone` — 布尔。固定场次建议 `true`，否则跨时区显示会自动换算，用户会懵。

### 语义集成：`semantics`

`semantics` 让 iOS 知道"这是张电影票"而不是一张图，自动获得日历建事件、地图建议、Siri 提醒。结构：

```json
{
  "eventTicket": {
    "eventStartDate": "2024-02-12T20:42:00Z",
    "eventEndDate":   "2024-02-12T22:30:00Z",
    "eventType": "movie",
    "venue": {
      "name": "示例国际影城",
      "location": {"latitude": 35.1, "longitude": 114.2}
    }
  }
}
```

`eventType` 预定义值有 `movie` / `concert` / `sport` / `generic` 等。**嵌套在 `eventTicket` 下是安全的**——之前误把整个 `semantics` 塞顶层会触发字段级防火墙导致 pass 打不开，壳实验跑过两次确认这个位置 OK。

`venue.location` 同样会触发列表城市反查，介意就去掉 `location`（日历与类型集成不依赖坐标，只看 `venue.name`）。这跟 `locations` 是两套独立机制，不要混。

### 过期与状态

- `expirationDate` — W3C 时间。过了点 Wallet 自动归档变灰。电影票一般设成"场次结束 + 影片时长"，大约 +2h。**别写死到 2027 年**，免签不像真签名票那样有外部系统帮你作废，过期了还在列表里晃很碍眼。
- `passThatWasSet` — W3C 时间字符串，**必须是字符串不能用对象**。设成过去时间（生成时刻 −24h），避免 iOS 认为"刚更新"而重置通知设置。早期版本试过 `{datetime, timestamp}` 对象格式，实测无效。
- `voided` — 布尔。`true` 时票面打灰水印、通知禁发，标记已使用。

### 隐私与分享

- `sharingProhibited` — 布尔。`true` 禁用分享按钮，防止含个人取票码的票被随手转出去。
- `userInfo` — 任意 JSON，不显示在票面，给调用方读取。订单号、用户 ID、生成时间戳都可以往里塞。
- `appLaunchURL` — 点票跳转的 URL。**必须有 `https://` 头**，否则拒收——脚本里要写自动检测。
- `groupingIdentifier` — 相同值自动分组。**不能含空格**，否则拒收。
- `associatedStoreIdentifiers` — 关联 App Store 应用 ID。装了对应 App 就在票上显示打开按钮，纯展示，跟推送无关。

## 项目架构：两层体系

仓库刻意分两层，二次开发前先认清边界：

| 层 | 产物 | 职责 |
|---|---|---|
| 知识层 | `开发/参数储备库.md` + `templates/fingerprints.json` | 全量记录各品牌原版指纹（顶层键、样式、字段结构、图片尺寸、颜色、行为字段），永远不直接用于生成 |
| 执行层 | `reskin.py`（严格模式）以及各 `*_to_wallet.py` / `build_pass.py` | 只输出该品牌原版有的字段，一个不多一个不少 |

规则几条要记牢：

- `extract_fingerprint.py` 自动扫原版模板生成指纹库。
- `reskin.py --verify` 跑一遍会逐项比对生成品和原版指纹，唯一允许的差异是身份三键改写 + `webServiceURL` / `signature` 删除。
- **图片尺寸运行时读取，绝不硬编码**——同品牌不同票 thumbnail 实测有 68×95 和 67×90 两种，写死必错。
- icon/logo 保留原版品牌图，只换 thumbnail 海报位（3:4 居中裁切）。

这么设计的好处是：探索出来的参数全部沉淀在知识层，生成时严格照原版，不会因为"顺手多填点东西"而破坏免签结构。

## 二次开发指南

### 脚本布局一览

根目录下几个核心脚本，按使用频率排序：

| 脚本 | 用途 |
|---|---|
| `build_pass.py` | 模板驱动统一生成器，`-t maoyan\|wanda\|xiecheng\|itunes\|taopiaopiao`。只改 `field.value`，注入免签身份 + 本地触发 + `semantics`，重算 manifest |
| `reskin.py` | 严格模式换壳，`EXTRAS` 默认全关；`--verify` 比对指纹 |
| `extract_fingerprint.py` | 扫原版模板生成 `templates/fingerprints.json` |
| `passkit_rebuilder.py` | 通用工具：重算 manifest、重打包任意 `.pkpass` |
| `*_to_wallet.py`（maoyan/wanda/xiecheng/itunes） | 各品牌具体生成脚本，可作二次开发样本 |
| `gen_maoyan_tickets.py` | 批量生成历史票 + `.pkpasses` 一键包 |
| `build_web.py` | 生成纯前端 `开发/maoyan_generator.html`（可选，与核心机制无关） |

知识层：`开发/参数储备库.md` + `templates/fingerprints.json`；前端骨架：`开发/maoyan_web_template.json`。

### 新增一个品牌模板的流程

要把工具套到一个新品牌的票根（比如某个景区、某个体育馆）上，照下面走：

1. 拿到该品牌一张原版 `.pkpass`，放进项目（比如 `foo.pkpass`）。
2. 跑 `extract_fingerprint.py` 生成指纹，确认顶层键、样式、字段结构、图片尺寸都对。
3. 在 `build_pass.py` 的 `-t` 分支里加一个 case：照指纹只改 `field.value`，写入免签身份三键，剥离 `webServiceURL` / `signature` / `authenticationToken`，按需注入本地触发字段与 `semantics`。不要新增原版没有的字段——免签对额外字段容忍度不高。
4. 生成后用 `passkit_rebuilder.py` 或 `reskin.py --verify` 校验 manifest 自洽、指纹匹配。
5. 真机 AirDrop 验证：能不能加、颜色文案对不对、`relevantDate` 附近弹不弹通知、ⓘ 里通知开关存不存在。

### manifest 重算原理

改完内容后，对包内每个文件（`pass.json` 和所有 png）算一次 SHA-1，写进 `manifest.json` 对应键，再整体重打包成 zip（不生成 `signature`）。任何只改 `pass.json` 不重算 manifest 的产物都会被 Wallet 拒收。这一步是底线，没有捷径。

## 真机验证清单

把 `.pkpass` 用 AirDrop / 邮件 / 文件 App 传到 iPhone，点开就能加进 Wallet。下机时按这几条逐项确认：

- 能否正常添加（不报错就是过了）
- 颜色、文案、二维码是否正常
- 锁屏是否在 `relevantDate` 附近弹通知（详情页 ⓘ 里看通知开关存不存在）
- 点 ⓘ 背面信息是否完整
- 列表是否如预期显示/不显示城市（取决于 `locations` 有没有）
- 过期时间到点后是否自动归档

前三条任意一条挂了，回去检查 `manifest.json` 的 SHA-1 和本地触发字段的格式。

## 踩坑实录

`.pkpasses` 一键包的内部结构、`webServiceURL` 为什么死刑、字体缩放、`locations` 反查与 Data Detectors 的区别、`barcode` 末 8 位、`passThatWasSet` 格式、图片尺寸不硬编码、免签硬限制——这些反复栽过的地方单独写在 [docs/pitfalls.md](docs/pitfalls.md)，每条都有当时的实验数据。

## 免责声明

文中截图与示意图（包括图 1 实际效果图）来源于真机实测渲染结果，**仅作为字段效果与呈现形式的参考**。实际添加至 Wallet 后的显示效果可能因以下因素存在差异：

- iOS / Wallet 版本差异（不同 iOS 版本对字段渲染规则、字体缩放、通知触发策略可能不一致）
- 设备差异（屏幕尺寸、缩放设置、可访问性选项）
- 票面字段内容差异（字段长度、字符集直接影响字体缩放与排版）
- 模板与字段组合差异（同一字段在不同布局策略下表现可能不同）
- 网络与时区差异（影响 `locations` 反查、`relevantDate` 触发时间等）

本项目及文档中涉及的票面样式、字段取值均**用于技术研究与字段效果演示**，不涉及任何商业票务平台的实际运营。文末展示的猫眼票面示例仅作为免签壳机制下的渲染效果参考，与对应品牌的实际产品、运营策略无关。如用于商业用途，请自行评估合规风险。

## License

MIT。