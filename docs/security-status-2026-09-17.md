# ClawHub 安全检查状态核查（2026-09-17）

> 执行人：天桐｜指令：检查「OpenClaw Beautify Github Readme」在 ClawHub 的 LLM REVIEW 安全检查状态
> 命令：`clawhub skill verify xiaoyaoclaw-beautify-github-readme` + `clawhub inspect ... --json`

---

## 1. 结论（一句话）

**未通过（fail）** —— 平台侧 LLM 复核 + 两套扫描器给出的综合安全结论是 **`suspicious`（可疑 / 置信度 high）**，`skill verify` 的决策为 `fail`，原因码 `security.status_not_clean`。

⚠️ 注意一个关键分歧：**平台「处置层」（moderation）判 clean，但「证据层」（security）判 suspicious**。页面上的信任标识看 moderation，`verify` 校验看 security，两者当前不一致。

---

## 2. 现状事实

| 项 | 值 | 来源 |
|---|---|---|
| Skill | `xiaoyaoclaw-beautify-github-readme`（OpenClaw Beautify Github Readme） | inspect |
| 最新版本 | **v1.0.9**（2026-09-07 发布；MIT-0） | inspect |
| 扫描版本 | v1.0.9（resolvedFrom=latest） | verify |
| **security.status** | **`suspicious`** ｜ passed = **false** ｜ verdict = suspicious ｜ confidence = **high** | verify |
| `verify` 决策 | `ok: false` / `decision: "fail"` / reasons = `["security.status_not_clean"]` | verify |
| security.summary（LLM 判词） | "The skill's README beautification purpose is coherent, but its bundled visual renderers can process untrusted SVGs with incomplete containment, so it needs review before installation." | verify |
| 证据扫描时间 | 2026-09-16 11:33:52 UTC（引擎 v2.4.26） | verify |
| 扫描器 | `aig`（腾讯 AI-Infra-Guard，v0.2.1）2 条告警 · `skillspector`（v2.11.2，LLM 由 gpt-5.4 驱动）9 条 issue | verify |
| **moderation.verdict** | **`clean`**（isSuspicious=false / isMalwareBlocked=false）｜ reasonCodes=`["review.llm_review"]` ｜ 引擎 v2.4.26 ｜ 2026-09-16 11:33:44 UTC | inspect |
| 签名 | `unsigned` | verify |
| 溯源 | `source: unavailable`（未记录服务端 GitHub 导入溯源） | verify |

**核心落差**：skillspector 风险分 **100 / severity CRITICAL / recommendation `DO_NOT_INSTALL`**（max_issue_severity = HIGH）；而 moderation 层在 8 秒后仍给 clean。说明 **平台升级了扫描引擎（v2.4.26）后重扫 1.0.9，新证据没能在处置层生效**（或处置为人工/规则判定为 clean，但 `verify` 只认 security 证据）。

> 对比记忆：v1.0.8 时代的「四扫描器全绿」是**旧引擎**下的结论；本次是引擎升级后的**重扫结果**，等于把 09-07 的安全战成果部分推翻。

---

## 3. 扫出来的问题（11 条：aig 2 + skillspector 9）

### 3.1 AIG（腾讯 AI-Infra-Guard）· 2 条 T09 warning（"不安全编码实践"）

| # | 位置 | 问题 | 风险 |
|---|---|---|---|
| 1 | `scripts/visual_verify.py:49-53`（+261-295、395-418） | **SVG 资源校验不完整 → 回环 SSRF**：`DANGEROUS_REF` 只拦 `href/src` 里的直写 URL，**不拦 CSS `url(...)` / `@import`**；Chromium 的 `--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1` 把**整个 127.0.0.1 放行**（而非只放行本次随机端口）→ 构造的 SVG 可让 headless Chromium 请求本机任意端口的服务（探测本地服务 / 打无鉴权的本地管理接口） | Medium |
| 2 | `scripts/render_motion_gif.py:172-184`（+543-557） | **未净化的 SVG 直接喂给原生渲染器**（`rsvg-convert` / `sips`）：该脚本**没有** visual_verify 那套静态闸门（不拒 `<script>`/`foreignObject`/远程字体/`file:`/绝对路径/CSS url/`@import`），`ET.parse` 通过即渲染；且 **无 timeout、无资源限额**（可 DoS）→ 若渲染器有解析漏洞，理论上可到代码执行（本次未取证到具体 CVE） | Medium |

### 3.2 SkillSpector（v2.11.2）· 9 条

| 严重度 | ID | 类别 | 位置 | 要点 |
|---|---|---|---|---|
| HIGH 0.95 | TP4 | MCP Tool Poisoning | SKILL.md:1 | **「声明的能力与实际代码不符」**：扫描器只看单个脚本切片时认为 `audit_readme.py` 只做轻量审计，不具备声明的渲染/对比度/贴边/双主题能力 → 判为「功能与描述不匹配」 |
| HIGH 0.95 | OH1 | Output Handling | `render_motion_gif.py:511` | 输出未校验即注入下游上下文（ffmpeg 调用） |
| HIGH 0.75 | LP1 | MCP Least Privilege | `scripts/visual_verify.py:1` | 用了 **`env` 能力但未在 `allowed-tools` 声明**（本机 Windows 还实测到依赖 `LOCALAPPDATA` 等环境变量，进一步坐实） |
| MEDIUM 0.7 | AST4 ×4 | Dangerous Code Execution | `render_motion_gif.py:184/495/511`、`visual_verify.py:295` | `subprocess` 调用（均为参数列表、**非 shell=True**，实际注入面很窄，属规则级命中） |
| LOW 0.84 | SQP-3 ×2 | 语言/地区中立性 | `SKILL.md:48`、`references/svg-production.md:83` | 中文文档未声明「语言可选」；字体栈写死 PingFang SC / Microsoft YaHei 被读成地区默认策略 |

**注**：全部 issue 都带 `llm-unconfirmed` 标签 → 这些是**规则命中的候选**，LLM 复核后没有把它们全部确认；最终综合判词（见 2 节 summary）只落在「SVG 处理容器不完整」这一条主线上。

---

## 4. 我方评估（诚实版）

**真问题（值得修，攻击面真实存在）**

1. **回环 SSRF 豁免过宽** —— `EXCLUDE 127.0.0.1` 应改为只豁免本次预览端口。这条是实打实的逻辑缺陷，修起来成本极低（把端口写进 resolver 规则，或改用非回环的临时 host 映射）。
2. **`render_motion_gif.py` 缺静态闸门** —— 与 `visual_verify.py` 的门控不对齐。修法：把 `is_safe_to_render()` 抽成共用模块，两条渲染路径都过闸；再补 `subprocess` timeout / 资源限额。
3. **CSS `url(...)` / `@import` 未拦** —— `DANGEROUS_REF` 补两条正则即可。
4. **`env` 能力未声明** —— `allowed-tools` 里补声明（或改成不依赖环境变量）。

**噪音（可解释，不必按字面改）**

5. **TP4「能力与代码不符」是切片误判**：扫描器按单文件喂给 LLM，`audit_readme.py` 只负责"审计"这一环，渲染/对比度能力在 `visual_verify.py`。属**扫描器粒度问题**，但描述措辞可微调以降低误解（说明"由多个脚本分工实现"）。
6. **AST4 四条 subprocess**：全部是参数列表调用、无 shell，规则性命中，实际不可注入。可在代码注释里说明以降低误报。
7. **SQP-3 两条语言/地区**：中文优先是**本产品有意为之**（目标受众含中文用户），可加一句"语言可选/英文版在 GitHub"化解。

---

## 5. 影响面

- `verify` fail 的**直接后果**：依赖该证据的信任标识/安装前校验会失败；skillspector 建议 `DO_NOT_INSTALL`。
- moderation 仍为 `clean` → **当前未必已下架或隐藏**（inspect 显示未被标记 suspicious / malware），但**页面 trust 标识与 verify 结论不一致**这件事本身就是风险：平台随时可能按新引擎重扫结果收紧处置。
- 签名 `unsigned` + 溯源 `unavailable` → 在新引擎下这两项也是加分项缺失。

---

## 6. 建议动作（待指挥官决策，不由我擅自执行）

| 优先级 | 动作 | 成本 |
|---|---|---|
| P0 | 修 visual_verify.py 回环豁免（只放行本次端口）+ `DANGEROUS_REF` 补 CSS 形态 | ~0.5h |
| P0 | `render_motion_gif.py` 接入同一静态闸门 + subprocess timeout | ~1h |
| P1 | `allowed-tools` 补 `env` 能力声明 | ~5min |
| P1 | 描述里补一句"能力由多脚本分工"，`svg-production.md` 字体段改为条件式表述 | ~15min |
| P2 | 发 v1.0.10 → 重扫 → 观察 security.status 是否回到 clean | — |
| P2 | 若 moderation/security 长期不一致 → 走 ClawHub 申诉/人工复核通道 | 待查 |

---

## 7. 复现命令

```powershell
clawhub skill verify xiaoyaoclaw-beautify-github-readme      # → ok:false / suspicious
clawhub inspect xiaoyaoclaw-beautify-github-readme --json    # → moderation.verdict=clean（分歧点）
clawhub scan --slug xiaoyaoclaw-beautify-github-readme --json # 完整扫描报告（可选）
```

页面：<https://clawhub.ai/dtsola/skills/xiaoyaoclaw-beautify-github-readme>

---

## 8. 修复记录（2026-09-17，指挥官批「全修」）

提交 `477caac`（本地，待推送）。

| 命中项 | 修复 |
|---|---|
| aig T09 ①（回环 SSRF） | **改架构而非改正则**：preview 端点只服务**一个 URL**，并同时充当 Chrome 的**唯一代理**；加 `--proxy-bypass-list=<-loopback>` 取消 Chrome 对 loopback 的隐式代理绕过 → 所有请求（含字面 `127.0.0.1` 与任意 loopback 端口）都必须过这道过滤器，非白名单一律 403。DNS 全域名封锁作为第二层 |
| aig T09 ①（CSS `url()` / `@import` 未拦） | 新增 `scripts/svg_safety.py`：`url(...)` 目标在**属性与样式正文**两处扫描，非 `#fragment` / `data:` 一律拒；`@import` 直接拒 |
| aig T09 ②（GIF 路径无闸门） | `render_motion_gif.py` 入口先 `assert_safe_to_render`，**每个派生图层渲染前再验一次**；`rsvg-convert`/`sips`/`ffmpeg` 全部 `shell=False` + 硬超时（120s / 300s），补帧目录与输出路径校验 |
| skillspector OH1（输出未校验） | `encode_gif` 加输入/输出路径校验 + 注释说明所有进入 ffmpeg 参数的值均由本地派生（fps 1-60、colors 2-256、dither 白名单） |
| skillspector LP1（`env` 未声明） | SKILL.md `allowed-tools` 补 `Env`，并在信任边界章节写明：仅用于定位 Chrome/Edge 二进制（`PROGRAMFILES` / `PROGRAMFILES(X86)` / `LOCALAPPDATA` / `PATH`） |
| skillspector AST4 ×4 | `subprocess` 全部显式 `shell=False` + 参数列表 + 超时；代码注释说明非 shell 调用（属规则性命中） |
| skillspector TP4（能力与描述不符） | 描述与 §8 补「能力由 scripts 分工实现」说明：`svg_safety.py` = 信任边界、`visual_verify.py` = 渲染级验证、`render_motion_gif.py` = GIF、`audit_readme.py` = 静态审计 |
| skillspector SQP-3 ×2 | SKILL.md 抬头补「语言可选 + 同仓英文说明」；`svg-production.md` 的 CJK 字体指导改为**条件式**（仅当 SVG 含 CJK 文本时才加 PingFang SC / Microsoft YaHei，其余场景按受众选本地化回退） |

**本地验证（真跑，非纸面）**

1. 8 个构造样本（CSS `url()` 回环 / `@import` / 远程字体 / `<script>` / `foreignObject` / 远程 `image` / `file://` / `../` 遍历）→ **全部被静态闸门拒绝并给出理由**
2. 良性样本（渐变 `url(#id)`、`data:` 图片）→ 正常放行
3. **回环金丝雀测试**：构造 SVG 引用 `http://127.0.0.1:<canary>/canary`（绕过静态闸门直调渲染）→ 金丝雀**收到 0 次请求**（403 拦截），渲染仍成功
4. 真实渲染回归：README 模式渲染出**有内容的 PNG**（30+ KB、采样像素确认为 SVG 背景色）→ 加固没有把渲染弄坏
   （过程中确实先坏过一次：`MAP * ~NOTFOUND` 连代理自身地址也阻断，Chrome 根本没发请求 → 表现为"空白截图但脚本报成功"的**假通过**；已改为 `MAP * ~NOTFOUND, EXCLUDE 127.0.0.1`，并把冒烟测试升级为"必须渲染出非白像素"以防再犯）
5. 端到端：`audit_readme.py` 报出恶意资产；`visual_verify.py` 对恶意资产 `SKIPPED`、对良性资产渲染成功

**仍待验证**：本机无 `rsvg-convert`/`sips` → GIF 全流程未真跑（静态闸门已单独验证）
**已知遗留（非本次命中，未擅自改）**：渐变填充（`fill="url(#g)"`）在对比度检查里会被判"找不到背景矩形"→ 良性渐变 hero 会误报，建议后续单独修

---

## 附：原始证据落盘

- `tmp/verify_security.json`（skills-cli `skill verify` 的完整 security 段，含 aig SARIF + skillspector 全量 issue）
- 采集脚本（一次性，已删）：`scripts/clawhub_verify_security.py` 等
