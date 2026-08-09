<img src="assets/icon.png" width="96" align="right">

# Apple 免签 `.pkpass` 工具集

不加开发者签名、也没有 Pass Type ID 和推送服务器，一张 `.pkpass` 照样能塞进 iPhone 的 Wallet。本项目是一套把任意票根 / 卡券重打包成这种"免签壳"的工具，并沉淀了 40 次真机验证得出的机制结论。

文档目的：把**这套免签机制本身的底层逻辑**讲清楚——为什么能不加签名、哪些字段能动哪些不能动、每个字段到底代表什么——让拿到的人能直接二次开发，而不是只会跑现成脚本。

> 随附示例模板不含任何第三方品牌标识（icon/logo 均为占位图），仅用于演示字段效果。

---

## 一、核心原理：免签壳为什么能不加签名进 Wallet

`.pkpass` 说到底是个 zip 包：

```
xxx.pkpass/
├── pass.json          # 核心数据（身份、字段、样式）
├── manifest.json      # 包内每个文件的 SHA-1 清单
├── icon.png / logo.png / thumbnail.png ...
└── signature          # 开发者证书对 manifest 的签名（免签没有）
```

正常流程里，开发者用证书对 `manifest.json` 签名生成 `signature`，Wallet 校验这条签名链来决定收不收。

免签的思路是**借身份，不借证书**。iOS 自带一个 "Create a Pass" 功能，它用自己的系统身份 `com.apple.wallet` 出 pass。我们把一张 pass 的 `teamIdentifier` 改成 `com.apple.wallet`、`passTypeIdentifier` 改成 `userpass.com.apple.wallet.<uuid>`，再剥掉 `signature` / `webServiceURL` / `authenticationToken`，iOS 看到 `com.apple.wallet` 就把它当成"系统自己出的票"放行——签名链这条校验直接被绕开。

代价很明确：没有开发者账号，就**拿不到 APNs 证书**，服务器推送不可能工作。所以免签 pass 的通知只能走本地触发字段（`relevantDate` / `locations` / `beacons`）。

改了包内任何内容（pass.json 或图片），都必须重算 `manifest.json` 里对应文件的 SHA-1，否则 Wallet 添加时报"凭证无效"拒收。本项目里 `build_pass.py`、`passkit_rebuilder.py`、前端生成器都内置了这一步。

---

## 二、哪些能签、哪些不能签（最关键的一节）

免签不是"啥都能填"。下面两张表是硬边界，踩错直接打不开或显示残缺。

### 可用（填了就生效）

| 字段 | 说明 |
|---|---|
| 身份：`formatVersion` / `serialNumber` / `organizationName` / `description` | 必填身份，正常填 |
| 外观：`backgroundColor` / `foregroundColor` / `labelColor` / `logoText` | 控制文字与背景色，不影响图片像素 |
| 票面：`headerFields` / `primaryFields` / `secondaryFields` / `auxiliaryFields` / `backFields` | 票上显示的全部文字区域 |
| 条码：`barcode` / `barcodes` | 至少留一个，否则添加告警 |
| 本地触发：`relevantDate` / `locations` / `maxDistance` / `beacons` / `ignoresTimeZone` | 免签下通知的唯一路径 |
| 语义：`semantics` | 告诉 iOS"这是张电影票"，开通日历/地图/Siri 集成 |
| 杂项：`groupingIdentifier` / `appLaunchURL` / `associatedStoreIdentifiers` / `userInfo` | 分组、跳转、关联 App、自定义元数据 |
| 状态：`expirationDate` / `passThatWasSet` / `voided` / `sharingProhibited` | 过期归档、通知防重置、作废、禁分享 |

### 不可用 / 致命（碰了就出问题）

| 字段 | 结论 |
|---|---|
| `webServiceURL` | **死刑**。免签身份 + 这个 = iOS 添加阶段直接打不开，与 HTTP/HTTPS 无关（12 轮壳实验含 5 个 HTTPS 变体全部失败）。根因：服务器推送要 APNs 证书，证书绑定 `passTypeIdentifier` 所属开发者账号，免签用 Apple 自己的 `com.apple.wallet` 拿不到。别加。 |
| `signature` | 免签没有。包完整性靠 `manifest.json` 里的 SHA-1，不需要也不存在签名文件。 |
| `authenticationToken` | 签名链的一环，免签下无意义，去掉。 |
| `storeCard` 样式 | 免签渲染器拒收，需换壳成 `eventTicket`（或 `generic`）。 |
| `background.png` / `strip.png` | 免签渲染器直接丢弃，填了也不显示。 |
| `nfc` | 仅 `boardingPass` / `storeCard` 支持，`eventTicket` 用不了。 |
| `transitType` | `boardingPass` 专用。 |

一句话：身份三键按免签规则改写、所有"显示类"和"本地触发类"字段照常填、凡是依赖开发者证书或服务器的全删。剩下的就是自由区。

---

## 三、pass.json 字段全解

每个字段给出：类型、是否必填、含义、在免签下的状态。状态分三档：**可用** / **可用但可选** / **移除**（见上表）。

### 3.1 身份字段（缺一个都加不进去）

- `formatVersion` — `integer`，必填。写死 `1`，目前只有这一个值。
- `teamIdentifier` — `string`，必填。免签固定 `com.apple.wallet`。物理限制，不能改回真实 Team ID。
- `passTypeIdentifier` — `string`，必填。`userpass.com.apple.wallet.<uuid>`。每次生成换 uuid，避免和已有 pass 冲突。
- `serialNumber` — `string`，必填。同一 `passTypeIdentifier` 下不能重复。想让新票覆盖旧票就保持 serialNumber 不变，否则每次随机。
- `organizationName` — `string`，必填。锁屏通知和列表里显示的组织名（"来自 XXX 的票券"）。
- `description` — `string`，必填。VoiceOver 朗读用，也出现在列表辅助文字。Apple 建议格式 `{类型}：{标题} - {地点} {时间}`。

### 3.2 外观

- `backgroundColor` / `foregroundColor` / `labelColor` — `rgb(r,g,b)` 字符串，可选。分别决定整体背景、文字、字段标签的颜色。**只影响画在图片之外的文字，不动图片像素**。
- `logoText` — `string`，可选。logo 图片旁的替代文字；不设时只显示 logo 图片。

### 3.3 条码

- `barcode`（单对象）与 `barcodes`（数组，iOS 9+ 多格式降级）二选一，至少留一个。`format` 支持 `PKBarcodeFormatQR` / `Aztec` / `Code128` / `PDF417`；`message` 是扫码得到的内容；`messageEncoding` 固定 `"UTF-8"`；`altText` 可选，扫码区下方小字、无障碍朗读用。
- 注意：票面显示的验证码和二维码内容可以是**两个字符串**（见踩坑第 5 条）。

### 3.4 票面内容：`eventTicket`

所有可见文字都挂在 `eventTicket` 对象下，按区域分五个 section，Wallet 自动排布：

| section | 角色 | 数量 | 说明 |
|---|---|---|---|
| `headerFields` | 堆叠时可见 | ≤3 | 多张票叠一起时只有这块露出来，强烈建议填 |
| `primaryFields` | 主标题 | 1~2 | 最大字号，通常放片名 |
| `secondaryFields` | 次要 | 1~2 | 略小，放验证码 |
| `auxiliaryFields` | 辅助 | ≤5 | 小字，放影院/座位/场次 |
| `backFields` | 背面 | 不限 | 点 ⓘ 翻面，放地址/电话/说明 |

每个字段统一结构：`{ "key": "唯一键", "label": "标签", "value": "显示内容" }`。`key` 给自己定位用，`label` 才是用户看到的小字标题。

区域布局见 [assets/field-layout.svg](assets/field-layout.svg)。

两个容易栽的点：

- **字体缩放**：Wallet 按字段内容长度自动缩放字号。同一模板，座位写 `7排6座` 和写 `4厅激光厅 7排6座、7排7座、7排8座`，后者被压小一截。这不是 bug，是渲染策略。
- **背面跳地图不用 `locations`**：在 `backFields` 里写一段真实地址文字，iOS 的 Data Detectors 会自动把它变成蓝色可点链接跳地图。完全不需要坐标，也不影响列表。

### 3.5 本地触发（通知唯一路径）

- `relevantDate` — W3C 时间字符串，可选。最重要，到点附近弹锁屏通知。
- `locations` — `[{latitude, longitude, relevantText}]`，可选。进入坐标范围弹通知；同时会让列表/归档反查出城市名（如"新乡市，河南省"）。不想显城市就别加。
- `maxDistance` — 整数（米），`locations` 的触发半径。
- `beacons` — iBeacon 触发，需现场硬件，一般用不上。
- `ignoresTimeZone` — `boolean`。固定场次建议 `true`，否则跨时区显示自动换算，用户会懵。

### 3.6 语义集成：`semantics`

`semantics` 告诉 iOS"这是张电影票"而非一张图，自动获得日历建事件、地图建议、Siri 提醒。结构：

```json
{
  "eventTicket": {
    "eventStartDate": "2024-02-12T20:42:00Z",
    "eventEndDate": "2024-02-12T22:30:00Z",
    "eventType": "movie",
    "venue": { "name": "示例国际影城", "location": {"latitude": 35.1, "longitude": 114.2} }
  }
}
```

`eventType` 预定义值有 `movie` / `concert` / `sport` / `generic` 等。`venue.location` 同样会触发列表城市反查，介意就去掉 `location`（日历与类型集成不依赖坐标）。嵌套在 `eventTicket` 下是安全的。

### 3.7 过期与状态

- `expirationDate` — W3C 时间。过了点 Wallet 自动归档变灰。电影票一般设"场次结束 + 时长（约 +2h）"。
- `passThatWasSet` — W3C 时间字符串（**不是对象**）。设成过去时间（生成时刻 −24h），避免 iOS 认为"刚更新"而重置通知设置。
- `voided` — `boolean`。`true` 时票面打灰水印、通知禁发，标记已使用。

### 3.8 隐私与分享

- `sharingProhibited` — `boolean`。`true` 禁用分享按钮。
- `userInfo` — 任意 JSON，不在票面显示，给调用方读取。
- `appLaunchURL` — 点票跳转的 URL，必须有 `https://` 头，否则拒收。
- `groupingIdentifier` — 相同值自动分组，**不能含空格**，否则拒收。
- `associatedStoreIdentifiers` — 关联 App Store 应用 ID，装了对应 App 就在票上显示打开按钮，纯展示。

---

## 四、架构：两层体系

项目刻意分成两层，二次开发时先认清边界：

| 层 | 产物 | 职责 |
|---|---|---|
| 知识层 | `开发/参数储备库.md` + `templates/fingerprints.json` | 全量记录各品牌原版指纹（顶层键、样式、字段结构、图片尺寸、颜色、行为字段），永不直接用于生成 |
| 执行层 | `reskin.py`（严格模式）及各 `*_to_wallet.py` / `build_pass.py` | 只输出该品牌原版有的字段，一个不多一个不少 |

- `extract_fingerprint.py`：扫描原版 `.pkpass` 自动生成指纹库。
- `reskin.py --verify`：生成品 vs 原版指纹逐项比对，唯一允许的差异是身份三键改写 + `webServiceURL`/`signature` 删除。
- 图片尺寸**运行时读取、绝不硬编码**（同品牌不同票 thumbnail 实测有 68×95 与 67×90 两种）。
- icon/logo 保留原版品牌图，只换 thumbnail 海报位（3:4 居中裁切）。

这套约束保证：探索出的参数全留知识层，生成时严格照原版，不会因为"多填了点东西"而破坏免签结构。

---

## 五、二次开发指南

### 项目布局（根目录脚本一览）

| 脚本 | 职责 |
|---|---|
| `build_pass.py` | 模板驱动统一生成器，`-t maoyan\|wanda\|xiecheng\|itunes\|taopiaopiao`。只改 `field.value`，注入免签身份 + 本地触发 + `semantics`，重算 manifest |
| `reskin.py` | 严格模式换壳，`EXTRAS` 默认全关；`--verify` 比对指纹 |
| `extract_fingerprint.py` | 扫描原版模板生成 `templates/fingerprints.json` |
| `passkit_rebuilder.py` | 通用工具：重算 manifest、重打包任意 `.pkpass` |
| `*_to_wallet.py`（maoyan/wanda/xiecheng/itunes） | 各品牌具体生成脚本，可作参考样本 |
| `gen_maoyan_tickets.py` | 批量生成历史票 + `.pkpasses` 一键包 |
| `build_web.py` | 生成纯前端 `开发/maoyan_generator.html`（可选，与核心机制无关，拿来即用） |

知识层：`开发/参数储备库.md`、`templates/fingerprints.json`；前端骨架：`开发/maoyan_web_template.json`。

### 新增一个品牌模板

1. 把该品牌原版 `.pkpass` 放进项目（如 `foo.pkpass`）。
2. 跑 `extract_fingerprint.py` 生成它的指纹，确认顶层键、样式、字段结构、图片尺寸。
3. 在 `build_pass.py` 的 `-t` 分支里加一个 case：照指纹只改 `field.value`，写入免签身份三键，剥离 `webServiceURL`/`signature`/`authenticationToken`，按需注入本地触发字段与 `semantics`。
4. 生成后用 `passkit_rebuilder.py` 或 `reskin.py --verify` 校验 manifest 自洽、指纹匹配。
5. 真机 AirDrop 验证能否添加（见第六节清单）。

### manifest 重算原理

改完内容后，对包内每个文件（pass.json、各 png）计算 SHA-1，写入 `manifest.json` 对应键，再整体重打包成 zip（不生成 `signature`）。任何只改 pass.json 不重算 manifest 的产物都会被 Wallet 拒收。

---

## 六、动手：构建与验证

`examples/` 下有一份去品牌的 `demo-template.pkpass`：

- `make_demo.py`：从真实电影票骨架抽取字段结构，换成占位图和中性的示例数据重新生成。
- `build_pass.py`：改完 `pass.json` 或图片后，用它重算 manifest。

```bash
cd examples
python make_demo.py                       # 生成 demo-template.pkpass
# 手动改 pass.json 里的 value ...
python build_pass.py demo-template.pkpass # 重算 manifest
```

把 `.pkpass` 用 AirDrop / 邮件 / 文件 App 传到 iPhone，点开即可加进 Wallet。

真机验证清单：

- 能否正常添加（不报错）
- 颜色、文案、二维码是否正常
- 锁屏是否在 `relevantDate` 附近弹通知（详情页 ⓘ 里看通知开关）
- 点 ⓘ 背面信息是否完整
- 列表是否如预期显示/不显示城市（取决于 `locations`）

---

## 七、踩坑实录

`.pkpasses` 一键包的内部结构、`webServiceURL` 为什么死刑、字体缩放、`locations` 反查与 Data Detectors 的区别、`barcode` 末 8 位、`passThatWasSet` 格式、图片尺寸不硬编码、免签硬限制——实战里反复栽过的地方，单独写在 [docs/pitfalls.md](docs/pitfalls.md)。

## License

MIT。示例模板不含任何第三方品牌资产。
