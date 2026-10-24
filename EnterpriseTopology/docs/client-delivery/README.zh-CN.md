# 客户交付报告与需求记录

记录日期：2026-10-23（Australia/Sydney）。本目录服务于最终交付与验收，不新增功能范围，也不重新运行模型 benchmark。

## 先看什么

- `report/main.tex`：英文客户报告，可在 Codex LaTeX 编辑器中编译和查看 PDF。
- `user-stories.md`：可阅读的需求与验收标准。
- `user-stories.json`：相同需求的结构化原始记录。
- `feedback-response.md`：客户反馈、对应 user story、处理情况及剩余限制。
- `test-results.md` / `test-results.json`：由实际保存的测试证据汇总的结果。
- `../../results/delivery/`：原始 XML、浏览器 TAP、真实网络 JSON 与控制台日志。

US01–US04 来自团队在 10 月 23 日转述的客户反馈：网页选择 topology、选择故障、进行 benchmark，以及 agent 诊断正确率约 50%–70%。没有声称已核验上周会议纪要。US05–US12 是这次补充的团队建议，尚未获得客户验收，不能写成客户之前已经同意的要求。

目前自动 SADE benchmark 只接通 `enterprise-75`。能浏览多种 topology 不等于这些 topology 全部能够自动运行 benchmark。这一点在报告和 US03 中保留为限制。

## 测试通过率不必人为达到 100%

给定 rubric 没有规定测试通过率必须为 100%，也没有给出代码覆盖率阈值。应该报告范围、数量、结果、缺陷影响和剩余限制。

- **执行后通过率** = Passed / (Passed + Failed + Error)。分母为 0 时写 N/A。
- **执行比例** = (Passed + Failed + Error) / (Passed + Failed + Error + Skipped + Not run)。不适用项应另列，不能暗中删除。
- **Agent 诊断正确率**是另一项指标，不能与软件测试通过率混用。
- 重复的断言、pytest subtest 和浏览器父级容器不额外计成独立测试，以免夸大数量。

100% 只表示明确范围内本轮已执行的测试全部通过，不代表全产品无缺陷、客户已验收或所有需求均已实现。已有缺陷修复后的最终回归可以是 100%；不需要故意保留失败来让数字“真实”。若测试未通过，应保留失败证据并说明影响。核心运行流程、评分正确性、故障恢复失败应优先修复；不能仅用总体通过率高来掩盖这些问题。

## 测试边界

- 离线测试：解析、独立评分例子、错误分母、配置隔离、故障目录、并发和恢复失败路径。
- HTTP 集成：真实临时回环服务器；模型/网络执行边界使用替代实现，不声称真实 agent 成功。
- 浏览器测试：真实 Chrome 和网页，页面明确标记 MOCK executor；验证选择、提交、结果显示、失败恢复、健康控制、键盘及小屏布局。
- 真实网络：显式 opt-in，使用原有 Kathara 网络及同一环境锁。只注入可逆的本拓扑故障，验证业务与对照路径，恢复后检查完整基线；不调用模型。
- 本次不重新测量模型正确率、付费 API 成本，不声称完成客户环境的独立安装、完整跨浏览器或无障碍审计。

## 复现与更新记录

在 `EnterpriseTopology/` 目录执行离线测试（需要允许临时回环端口）：

```sh
python -m pytest tests -q --junitxml=results/delivery/offline-tests.xml
```

浏览器测试需要安装 Playwright 和 Chromium/Chrome；可通过 `NODE_PATH`、`BROWSER_EXECUTABLE`、`NIKA_TEST_PYTHON` 指定本机依赖：

```sh
node --test tests/dashboard_delivery.cjs
```

真实网络测试默认跳过。只有需要重做系统验证时，才在确认 baseline 和环境所有权后显式运行；它不是重新运行模型 benchmark：

```sh
RUN_LIVE_DELIVERY=1 python -m unittest discover -s tests -p test_live_delivery.py -v
```

只读取已有证据并刷新报告，不运行任何测试或模型：

```sh
python tools/record_delivery_results.py
```

## 交付前仍需确认

正式项目名称、收件人和最终 scope；客户是否认可新增验收标准；诊断正确率以 exact RCA 还是 full correctness 为主；客户目标部署环境、代码/文档访问权限、独立安装和 UAT 结果。50%–70% 是难度目标，实际结果应照实呈现，不能调整评分规则把分数强行放入该区间。
