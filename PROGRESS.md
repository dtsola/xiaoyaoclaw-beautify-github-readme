---
type: project
slug: xiaoyaoclaw-beautify-github-readme
status: active
progress: 60
created: 2026-09-07
updated: 2026-09-17
docs:
  - path: docs/upgrade-plan.md
    desc: 升级改进点清单（交付状态 + 验收标准）
  - path: docs/security-status-2026-09-17.md
    desc: ClawHub LLM REVIEW 安全检查状态核查（v1.0.9 被新引擎判 suspicious）
  - path: docs/evidence/security-v1.0.9-2026-09-16.json
    desc: 原始证据（aig SARIF + skillspector 全量 issue）
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
- 2026-09-07：v1.0.0→v1.0.9 连续迭代（安全发布战），v1.0.8 四扫描器全绿，ClawHub latest = v1.0.9（MIT-0）
- **2026-09-17 09:57（指挥官指令：查 ClawHub LLM REVIEW 状态）**：⚠️ **未通过** —— `clawhub skill verify` 返回 `ok:false / decision:fail / reasons:[security.status_not_clean]`，security.status = **suspicious（confidence high）**，扫于 2026-09-16 11:33 UTC（引擎 **v2.4.26**，v1.0.9）
  - **关键分歧**：moderation.verdict = **clean**（8 秒前，同引擎）vs security 证据层 **suspicious** → 页面信任标识与 verify 结论不一致
  - 11 条命中：aig（腾讯）2 条 T09 = ① `visual_verify.py` 回环 SSRF（`EXCLUDE 127.0.0.1` 放行整个回环 + `DANGEROUS_REF` 不拦 CSS `url()`/`@import`）② `render_motion_gif.py` 无静态闸门直喂 rsvg-convert/sips（无 timeout）；skillspector 9 条 = TP4 能力描述不符（切片误判）/ OH1 输出未校验 / LP1 `env` 能力未声明 / AST4×4 subprocess（参数列表、非 shell）/ SQP-3×2 语言地区中立性
  - **定性**：4 条真问题（SSRF 豁免 / GIF 路径缺闸门 / CSS 引用 / env 声明）+ 3 类噪音；总修复成本约 2h → 建议 v1.0.10 重扫
  - 产出：`docs/security-status-2026-09-17.md` + 原始证据 `docs/evidence/security-v1.0.9-2026-09-16.json`（90 KB）
  - 状态：**待指挥官决策**（是否修 → 发 v1.0.10 → 复扫 / 或走人工复核通道）
- **2026-09-17 10:1x 指挥官批「全修」→ 11 条全部落实（提交 477caac，本地待推）**
  - 新增 `scripts/svg_safety.py`（唯一信任边界）→ 三个脚本共用；CSS `url()`/`@import` 在属性与样式正文两处扫描
  - `visual_verify.py` 渲染沙箱重做：**单 URL 端点兼唯一代理** + `--proxy-bypass-list=<-loopback>`（取消 loopback 隐式绕过）→ 回环 SSRF 结构性关闭；DNS 全封作第二层
  - `render_motion_gif.py`：入口+每层双重闸门、全部 `shell=False`、硬超时、帧目录/输出路径校验
  - SKILL.md：补 `Env` 能力声明 + 脚本分工说明 + 信任边界章节 + 语言中立；`svg-production.md` CJK 字体改条件式
  - **实测**：8 类构造样本全拒 / 2 类良性样本放行 / **回环金丝雀 0 命中** / 真实渲染回归有内容（曾因 `MAP * ~NOTFOUND` 连代理自身一起封导致"空白假通过"，已修正并把冒烟测试升级为必须渲染出非白像素）
  - ⚠️ 本机无 rsvg-convert → GIF 全流程未真跑；渐变对比度误报列为遗留
  - 下一步待批：发 **v1.0.10** → ClawHub 发布 → `clawhub skill verify` 复扫（另需代理恢复后推 GitHub）

## 文档索引

| 文档 | 说明 |
|------|------|
| docs/upgrade-plan.md | 改进点明细 + 交付状态 + 验收标准 |
