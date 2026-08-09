<img src="assets/icon.png" width="72" align="right">

# AnyWallet

> 脚本化、字段级可控、可批量的免签名 `.pkpass` 生成器。

借 iOS 27 原生 `com.apple.wallet` 系统壳，把任意 `.pkpass` 改写成免签、仍能被 Wallet 直接添加的票——**事件票、会员卡、优惠券都行，字段完全由你掌控**。

> **验证状态**：免签机制已在 **iOS 27 beta 4** 真机 40+ 次验证通过。

---

| | |
|---|---|
| 一张票每个字段怎么填、填错会怎样、iOS 27 下哪些能签哪些不能签——全在子文档里，主页不重复。 | <img src="assets/preview.jpg" width="220" alt="Wallet 预览"><br><sub>图 1 · 真机预览（iOS 27 beta 4）</sub> |

---

## 为什么是 AnyWallet（iOS 27 时代）

iOS 27 起，Wallet 内置原生 Create a Pass，能把二维码直接包成 pass。但它只做轻量二维码包装：

| 能力 | 原生 Create a Pass | AnyWallet |
|---|---|---|
| 二维码包装 | ✅ | ✅ |
| eventTicket / generic 完整字段布局 | ❌ | ✅ |
| `relevantDate` 本地触发 · `locations` 地理围栏 | ❌ | ✅ |
| 字段级定制、批量生成、接 CI/CD | ❌ | ✅ |
| 服务器推送 | ❌ | ❌（同原生，免签均无） |

**原生能力 < AnyWallet 的能力。** 苹果替你省掉开发者账号，没替你省掉字段和批量——那是 AnyWallet 的活。

---

## 文档导航

| 文档 | 讲什么 |
|---|---|
| [**docs/algorithm.md**](docs/algorithm.md) | 参数全解：身份三键、票面五区、条码、本地触发、状态、语义；iOS 27 兼容性矩阵；SHA-256 风险；新字段限制 |
| [**docs/pitfalls.md**](docs/pitfalls.md) | 8 条实战踩坑，每条带实验数据 |
| [**IOS27_TEST_CHECKLIST.md**](IOS27_TEST_CHECKLIST.md) | 每次大改后必跑的真机回归清单 |

---

## 快速开始（可选示例）

仓库自带一份去品牌演示票，对照文档看效果用；**不是主线**——照着 `docs/algorithm.md` 手写一张也完全可行。

```bash
python examples/make_demo.py      # 生成 demo-template.pkpass
# 用 AirDrop / 邮件传到 iPhone，点开加进 Wallet
```

---

## 仓库结构

```
AnyWallet/
├── docs/
│   ├── algorithm.md          # 参数全解（核心文档）
│   └── pitfalls.md           # 踩坑实录
├── examples/
│   ├── pass_template.json    # 去品牌 eventTicket 骨架
│   ├── make_demo.py          # 演示票生成器
│   ├── build_pass.py         # rebuild()：改完字段重算 manifest
│   └── demo-template.pkpass  # 现成样例
├── IOS27_TEST_CHECKLIST.md   # 真机回归清单
├── assets/                   # 图标、预览图、票面区域图
└── README.md                 # 本文件（落地页）
```

---

## 免责声明

票面样式与字段取值仅用于技术研究、字段效果演示，与任何商业平台的实际运营无关；如用于商业用途请自行评估合规风险。iOS 27 之后版本（iOS 28+）苹果可能调整 Wallet 校验逻辑，本项目不保证向前兼容，需重新真机验证。详见 [`docs/algorithm.md`](docs/algorithm.md) 第 0、10 节。

---

## License

MIT。
