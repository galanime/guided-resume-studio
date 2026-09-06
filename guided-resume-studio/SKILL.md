---
name: guided-resume-studio
description: 通过多轮引导建立或导入个人职业知识库，调研一个目标岗位，基于事实与 ATS 关键词确认内容，并生成可溯源的一页 LapisCV 专业蓝 PDF 简历。用于从零制作或按具体岗位定制简历；不用于自动填表、上传或投递。
metadata:
  short-description: 引导建库、岗位调研与可溯源简历生成
---

# Guided Resume Studio

把一次调用限制为一个目标岗位。先建立事实库，再调研和改写；不要先写通用简历后机械添加关键词。

## Start

1. 说明当前已获得的输入、将读取的文件或链接、不会执行的外部动作，以及完成证据。
2. 每轮只问一至三个相关问题。先取得姓名、至少一种联系方式和求职阶段。
3. 让用户选择填写 [候选人资料模板](assets/candidate-profile-template.md)，或导入 Markdown、TXT、JSON、YAML、PDF、DOCX、目录型知识库或可用的只读知识连接器。
4. 默认用 `scripts/init_workspace.py` 在当前工作区创建 `resume-workspace/<candidate-id>/`。不写全局记忆，不读取凭据，不上传资料。
5. 在建库时明确告诉用户：知识库会完整保存所有已确认资料，包括本次简历没用上的内容；没被选入不等于被删除，之后的岗位可以直接复用。
6. 进入建库和事实确认前，完整阅读 [交互工作流](references/interaction-workflow.md) 与 [资料和溯源](references/profile-and-provenance.md)。

## Grounding and research

- 正式简历只能使用 `user_verified` 或可向用户清楚展示来源并获确认的事实；`unverified`、`conflicted`、`do_not_disclose` 不得进入输出。
- 有完整 JD 时优先使用该官方页面。没有完整 JD 时搜索目标公司官方招聘页；只有岗位方向时综合三至五个当前代表性官方 JD。
- 调研、ATS 映射、经历选择或润色前，完整阅读 [岗位调研与改写](references/research-and-rewrite.md)。
- 在改写前读取 [岗位族叙事策略库](references/narrative-strategy-library.md)，按 JD 信号选择主叙事；不要把所有经历套成同一种“动作动词 + 量化结果”句式。机器可读的岗位族配置见 `assets/narrative-strategies.json`。
- 经历初稿完成后读取 [经历增强与无指标写法](references/experience-enhancement.md)：先升级事实的可读价值，再做 ATS 映射；没有数字不等于没有结果，不得因为缺指标而自动删弱或写成泛泛职责。
- 内容取舍按其中的固定决策规则自主完成（JD must_have 匹配 > 事实强度 > 时间 > 重复度），只把来源冲突、披露边界、事实提升和并列叙事方向交给用户；不要为可以按规则排序的选择反复提问。
- 缺乏事实支持的 ATS 关键词进入 gap 报告，不能写入简历。

## Planning and approval gates

- 已处于 Plan 模式时使用原生 Plan 对话；否则执行同等严格的内部计划阶段，并告诉用户可以手动切换 Plan 模式。Skill 本身不能改变系统协作模式。
- 先确认结构化个人事实，再确认岗位画像和改写策略。
- PDF 前必须展示完整 Markdown、区块顺序、公开联系方式、ATS 覆盖、关键改写对照和专业蓝 HTML 视觉预览。
- 只有用户明确确认模板、主题、内容、重点标记和生成 PDF 后，才能创建批准文件并执行正式渲染。
- 任何内容、主题或模板变化都会使批准哈希失效，按 [交互工作流](references/interaction-workflow.md) 的修订分级处理：M 级（错别字、标点、不改变事实/指标/关键词/重点/顺序/版式的措辞润色）直接修复并重渲染，更新批准哈希并记录 `amendments.jsonl`，不再要求用户重新确认；S 级（其余一切）只展示紧凑 diff 并做一次确认。反馈先批量收集、一轮改完，不得为一两处错字反复「重新生成—重新验收」。
- 字体特性、联系人渲染或任务本地模板变化也属于模板变化。浏览器缩放和预览 URL 查询参数不改变批准哈希。

## Render and verify

- 最终模板固定为 `lapiscv-professional-blue-one-page`：LapisCV 单页 A4 结构，加专业蓝 `#1a56db`、Noto Sans CJK SC 和显式重点标记。
- 默认精修排版以 8.9pt、1.39 行距为压缩下限，联系方式用 `｜` 分隔，并仅突出 `作品集：` 标签。不得继续缩小字号强塞一页。
- 区块是动态数组。没有项目、实习、技能、语言或奖项时省略该区块，不留下空标题。
- 用户指出局部排版问题时，先检查整页和所有同类选择器，再统一修复；不得只修被圈出的条目。正常中文自然断行不算异常；裁切、溢出、标签错位、日期碰撞和孤立标题才是阻断项，详细判定见 [渲染与 QA](references/render-and-qa.md)。
- 任何模板、CSS、字体特性、联系人渲染或正文布局调整后，都必须重新生成整页预览并重新检查全部区块；局部修补不构成新的视觉批准。
- 如需任务本地模板副本，必须复制完整 `assets/lapiscv/`（含 `LICENSE`），不得修改全局资产来完成尚未批准的单份简历；只有用户明确要求升级 Skill 时才把已验证方案合并回全局默认。
- 默认交付恰好一页且填充合理的 A4。生成预览前先运行 `scripts/render_lapiscv.py --fit-check --input <resume.json>` 估算占用；`overflow` 或 `underfilled` 时按 [渲染与 QA](references/render-and-qa.md) 的一页适配阶梯处理（超页：按决策规则从低优先级开始删减、压缩、合并；不满页：从知识库未选用事实池补强），复测到 `fits` 再请求批准，不得把明显超页或不满页的预览或 PDF 交给用户。
- 预览使用 `scripts/render_lapiscv.py --input <resume.json> --profile <profile.json> --ats-map <ats-map.json> --output-dir <dir> --preview-only`；确认后使用同一组输入和批准文件运行正式 PDF。
- 正式渲染和验收前，完整阅读 [渲染与 QA](references/render-and-qa.md)。
- 用 `scripts/validate_resume.py` 检查一页、A4、文本、字体和批准内容，并渲染 PNG。必须人工查看 PNG 后用 `--visual-approved` 完成最终 QA。
- 用 `scripts/snapshot_run.py` 保存准确的模板、主题、渲染器、验证脚本、批准信息、哈希和重建命令；重建结果至少再次通过结构 QA。

## Stop conditions

在以下任一情况停止，不声称完成：缺少最低资料；事实冲突未解决；用户未确认；官方岗位信息不足以支持确定结论；浏览器或中英文字体缺失；PDF 超过一页；文本、字体或视觉 QA 失败。不得自行上传、填写、保存在线草稿或提交申请。
