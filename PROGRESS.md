---
type: project
slug: xiaoyaoclaw-beautify-github-readme
status: active
progress: 60
created: 2026-09-07
updated: 2026-09-07
docs:
  - path: docs/upgrade-plan.md
    desc: 升级改进点清单（交付状态 + 验收标准）
---

# xiaoyaoclaw-beautify-github-readme（README 美化技能 · OpenClaw 升级版）

> README 标题：**OpenClaw Beautify Github Readme**
> 定位：基于上游 oil-oil/beautify-github-readme（MIT，1723★）本地升级改进版，非 fork
> 上游基线：commit `55bdb1c`（feat: add hybrid README composition workflow #17），main

## 目标

1. 保留上游全部能力（README 重设计 / asset-only / 纯 SVG / hybrid SVG / GIF / 归因门控）
2. 补强上游短板：验证自动化、Windows/中文适配、双主题安全
3. README 中明确声明「基于 oil-oil/beautify-github-readme 升级」
4. 发布 GitHub 公开仓 + ClawHub（走全流程确认制）

## 改进点清单（立项时评估，详见 docs/upgrade-plan.md）

1. **验证自动化**（最大短板）：audit_readme.py 只查 XML/viewBox/title/危险标签/图片存在；补 `visual_verify.py` = Chrome headless 截图 + 溢出/字号检查 + 双主题对比，沉淀十件套实战三重验证法
2. **Windows/中文适配**：字体栈补 Microsoft YaHei（现只有 PingFang SC/macOS）；预览工具跨平台说明（sips 仅 macOS，Windows 用 Chrome headless）；中英混排字宽/断行实操指导
3. **双主题安全决策树**：SVG 不吃 prefers-color-scheme → 深色容器 vs 透明底硬规则 + 对比度矩阵
4. **OpenClaw 生态适配**：门控问答精简模式（为 Claude Code 无 GUI 设计，OpenClaw 对话流冗余）
5. **归因/链接指向本项目**：attribution/showcase 上游链接替换；README 声明基于上游版本

## 发布计划

- 仓库：dtsola/xiaoyaoclaw-beautify-github-readme（新建独立仓，不点 fork；本地保留上游历史 + upstream remote 可 merge，参照 xiaoyaonotepaper 模式）
- 远端结构：origin=上游 oil-oil（fetch）/ xiaoyao=dtsola（push）
- ClawHub：显示名 OpenClaw Beautify Github Readme，提交后 pending-publication 待指挥官公开

## 进度日志

- 2026-09-07 09:2x：指挥官拍板立项（非 fork，本地 clone 上游改进，README 声明基于上游版）；clone 上游完成（55bdb1c，历史完整，工作区干净）；PROGRESS.md 落位
- 2026-09-07 09:3x：rebrand commit b3f8427（改名/中英双语/上游声明/新 hero/清旧 branding）；指挥官确认 hero 方向 OK
- 2026-09-07 09:4x：改进 ①②③ 开发完成——visual_verify.py（渲染+对比度+贴边，自测全量通过，抓到上游素材真实问题）；svg-production.md 补 YaHei/中英混排/双主题安全；SKILL.md §8 接入新脚本；docs/upgrade-plan.md 落位。待指挥官确认后 GitHub 建仓发布

## 文档索引

| 文档 | 说明 |
|------|------|
| docs/upgrade-plan.md | 改进点明细 + 交付状态 + 验收标准 |
