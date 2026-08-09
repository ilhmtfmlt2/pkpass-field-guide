<!-- 内部回归备忘：非对外文档，不进 README 导航，不面向读者。仅维护者大改后自测用。 -->

# iOS 27 真机验证清单（每次大改后必跑）

> 本清单是 AnyWallet 的回归测试基准，也是给用户的承诺：每次改动后，下面这些用例必须逐项在真机跑通。
> 验证环境：**iOS 27 beta 4**（后续正式版 / iOS 28+ 需重新填环境并重跑）。

## 环境

- iOS 版本：___（例：27.0 beta 4 / 27.1）
- iPhone 机型：___
- Wallet 版本：___
- 验证日期：___

## 测试用例

- [ ] 1. 基础 eventTicket 能正常添加（不报错即过）
- [ ] 2. `relevantDate` 触发锁屏通知（详情页 ⓘ 里通知开关在不在、是否弹）
- [ ] 3. `locations` 地理围栏触发（进入坐标后是否弹；列表是否显示城市）
- [ ] 4. `barcodes` QR 码扫描正常（用扫码 App 验证 message 内容）
- [ ] 5. 背面 `backFields` 完整显示（地址换行、电话可点）
- [ ] 6. 过期后自动归档（把 `expirationDate` 设过去，重装后确认归档）
- [ ] 7. 删除 pass 后重新添加无残留（通知设置、列表不重复）
- [ ] 8. `webServiceURL` 存在时确实被拒（阴性对照，确认死刑仍在）
- [ ] 9. `signature` 文件存在时确实被拒（阴性对照）
- [ ] 10. 改任意字段后 manifest 重算通过（添加不报「凭证无效」）

## 已知 iOS 27 限制

- 苹果原生 Create a Pass 已覆盖简单二维码场景（轻量包装）
- 本方案优势：**完整字段布局 + 本地触发 + 批量生成 + 接 CI/CD**
- `transferURL` / `changeSeatURL` / `auxiliaryStoreIdentifiers` 仅 poster event ticket 生效，普通 eventTicket 填了无效（非 bug）
- `storeCard` 免签拒收；`nfc` / `transitType` eventTicket 不支持

## 回归结论记录

| 日期 | iOS 版本 | 结果 | 备注 |
|---|---|---|---|
| ___ | ___ | 通过 / 失败 | ___ |
