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
5. 进入建库和事实确认前，完整阅读 [交互工作流](references/interaction-workflow.md) 与 [资料和溯源](references/profile-and-provenance.md)。

## Grounding and research

- 正式简历只能使用 `user_verified` 或可向用户清楚展示来源并获确认的事实；`unverified`、`conflicted`、`do_not_disclose` 不得进入输出。
- 有完整 JD 时优先使用该官方页面。没有完整 JD 时搜索目标公司官方招聘页；只有岗位方向时综合三至五个当前代表性官方 JD。
- 调研、ATS 映射、经历选择或润色前，完整阅读 [岗位调研与改写](references/research-and-rewrite.md)。
- 缺乏事实支持的 ATS 关键词进入 gap 报告，不能写入简历。

## Planning and approval gates

- 已处于 Plan 模式时使用原生 Plan 对话；否则执行同等严格的内部计划阶段，并告诉用户可以手动切换 Plan 模式。Skill 本身不能改变系统协作模式。
- 先确认结构化个人事实，再确认岗位画像和改写策略。
- PDF 前必须展示完整 Markdown、区块顺序、公开联系方式、ATS 覆盖、关键改写对照和专业蓝 HTML 视觉预览。
- 只有用户明确确认模板、主题、内容、重点标记和生成 PDF 后，才能创建批准文件并执行正式渲染。
- 任何内容、主题或模板变化都会使批准哈希失效，必须重新确认。

## Render and verify

- 最终模板固定为 `lapiscv-professional-blue-one-page`：LapisCV 单页 A4 结构，加专业蓝 `#1a56db`、Noto Sans CJK SC 和显式重点标记。
- 区块是动态数组。没有项目、实习、技能、语言或奖项时省略该区块，不留下空标题。
- 预览使用 `scripts/render_lapiscv.py --input <resume.json> --profile <profile.json> --ats-map <ats-map.json> --output-dir <dir> --preview-only`；确认后使用同一组输入和批准文件运行正式 PDF。
- 正式渲染和验收前，完整阅读 [渲染与 QA](references/render-and-qa.md)。
- 用 `scripts/validate_resume.py` 检查一页、A4、文本、字体和批准内容，并渲染 PNG。必须人工查看 PNG 后用 `--visual-approved` 完成最终 QA。
- 用 `scripts/snapshot_run.py` 保存准确的模板、主题、渲染器、批准信息、哈希和重建命令。

## Stop conditions

在以下任一情况停止，不声称完成：缺少最低资料；事实冲突未解决；用户未确认；官方岗位信息不足以支持确定结论；浏览器或中英文字体缺失；PDF 超过一页；文本、字体或视觉 QA 失败。不得自行上传、填写、保存在线草稿或提交申请。
