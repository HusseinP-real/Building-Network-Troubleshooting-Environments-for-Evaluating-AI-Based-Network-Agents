# haosenpeng 的组合故障：错误网关 + ICMP 丢包

场景：[`kath3-laptop0-wrong-gateway-and-icmp-drop`](../dataset/kath3_Q/custom/kath3-laptop0-wrong-gateway-and-icmp-drop.txt)。

## 谁写命令，谁负责排查？

场景作者同时写工单 `[PROMPT-TO-AGENT]` 和确定性的注入命令 `[INJECTION]`。
执行器运行注入命令；排障 agent 只收到工单和拓扑概览，然后自己调用诊断工具。
agent 不负责把作者的故障想法翻译成注入命令，也不会收到标准答案。
`[GROUND-TRUTH]`、`[FIX]`、`[SCORING-AXES]` 是诊断评分依据。

## 这个新故障组合了什么？

1. 将 Kath3 的 Laptop0 默认网关从 `172.16.20.1` 改成未分配的 `172.16.20.99`。
2. 在同一主机的 iptables `OUTPUT` 链加入针对 `192.168.100.1` 的 ICMP DROP 规则。

第一项来自现有 `kath3-laptop0-wrong-gateway`；第二项借鉴现有
`simple-bgp-router2-iptables-icmp-drop` 的过滤机制，但改为主机 `OUTPUT`，
并限制到一个目的地址。它不是原 BGP 路由器的 `FORWARD` 规则。
两个故障放在同一设备，因此可以直接使用当前单设备的场景注入格式。

| 阶段 | Laptop0 → 网关 .1 | Laptop0 → PC4 | Laptop0 → 192.168.100.1 | PC4 → 192.168.100.1 |
|---|---|---|---|---|
| 正常 | 通 | 通 | 通 | 通 |
| 双故障 | 通 | 不通 | 不通 | 通 |
| 只修网关 | 通 | 通 | 不通 | 通 |
| 只删过滤规则 | 通 | 不通 | 不通 | 通 |
| 两个都修复 | 通 | 通 | 通 | 通 |

“只修网关”阶段，过滤规则的包计数应增加。这证明第二个故障实际在丢包，
而不是仅仅在配置里出现。工单没有泄露根因；评分要求找出两个问题。

## 一条命令运行网络实测

先启动 Docker，安装 Python 3.12+ 和 Kathara CLI。以下命令从 `FaulT-Bench/` 执行：

```bash
python3 tools/validate_haosenpeng_fault.py --check-only
python3 tools/validate_haosenpeng_fault.py
```

不需要 SADE、Python Kathara API 或 LLM API key。第二条命令：

1. 复制完整 Kath3 到唯一临时目录，并启动隔离实验；不挂载 hosthome/shared。
2. 等待健康基线的配置与连通性检查通过；基线不通过则不注入。
3. 使用 repo 的 `parse_scenario` 读取并执行场景命令及六条注入后检查。
4. 再注入一次，确认标记规则没有重复添加。
5. 验证两种单项修复、DROP 计数和两种完整恢复顺序。
6. 无论成功或失败，都尝试只清理本次临时实验，并输出 JSON 证据。

默认输出：`faultbench/runs/haosenpeng-validation.json`（gitignored）。
可用 `--output /path/to/report.json` 自选位置。部署失败时报告保留错误，
临时拓扑配置会留在报告里的 `temporary_lab` 路径以便排查。
若清理失败，可对该**具体临时目录**执行 `kathara lclean -d /path/to/temporary/Kath3`。

这是一项真实容器网络实验，不是 mock，也不是一次 LLM agent benchmark；
不会生成 agent 分数。严格验证器要求真实设备退出码和 ping 丢包率，
对无输出、超时和未知检查条件不会自动判通过。

## 手工注入和排查

若要一步一步做，先在 `topology_kathara/Kath3/` 执行
`kathara lstart --noterminals`，确认没有其他人正在使用这一目录对应的实验，
再执行以下命令。每次注入前先验证上表正常行。

```bash
kathara exec laptop0 -- ip route show default
kathara exec laptop0 -- ping -W2 -c2 172.16.20.1
kathara exec laptop0 -- ping -W2 -c2 172.16.10.4
kathara exec laptop0 -- ping -W2 -c2 192.168.100.1
kathara exec pc4 -- ping -W2 -c2 192.168.100.1
```

运行 `kathara connect laptop0`，将场景 `[INJECTION]` 的 `cmd` 内容粘贴到设备 shell。
通过 `exit` 返回宿主机终端。

```bash
kathara exec laptop0 -- ip route show default
kathara exec laptop0 -- ip neigh show
kathara exec laptop0 -- iptables -S OUTPUT
kathara exec laptop0 -- iptables -L OUTPUT -n -v -x
```

先修网关，再重复两条远端 ping，观察一个恢复、另一个仍失败：

```bash
kathara exec laptop0 -- ip route replace default via 172.16.20.1
kathara exec laptop0 -- ping -W2 -c2 172.16.10.4
kathara exec laptop0 -- ping -W2 -c2 192.168.100.1
kathara exec laptop0 -- iptables -L OUTPUT -n -v -x
```

精确删除实验规则，然后复测。不要清空整张防火墙：

```bash
kathara exec laptop0 -- iptables -D OUTPUT -d 192.168.100.1/32 -p icmp -m comment --comment haosenpeng-compound-icmp -j DROP
kathara exec laptop0 -- ping -W2 -c2 172.16.10.4
kathara exec laptop0 -- ping -W2 -c2 192.168.100.1
kathara lclean
```

## 接入 agent benchmark

自定义场景放在 `dataset/kath3_Q/custom/`，独立于论文原始 560 个场景，
避免改变 `base80.csv` 的实验定义。当前 `resolve_scenario` 会搜索这个目录，
但 `list --scope base` 和 `sweep --scope base` 不包含它；请使用场景 ID 或专属 manifest。

安装主 README 中的 SADE 环境和 API key 后，从 `faultbench/` 执行：

```bash
./fb.sh bench --manifest benchmarks/haosenpeng.csv --agents cc-baseline --dry-run
./fb.sh bench --manifest benchmarks/haosenpeng.csv --agents cc-baseline --runs-root runs/haosenpeng_p1
```

自动 benchmark 会自行部署、注入、检查、运行 agent、评分和清理。
它使用 Python API 注册实验名，和本教程手工 CLI 启动的临时实验不同。
运行自动 benchmark 前先结束手工实验；现有 harness 的容器计数/清理辅助逻辑
按一次一张网络设计。完整 benchmark 需要外部 agent 环境；网络实测脚本不需要。

## 本次验证证据

[`validation/haosenpeng-compound-fault.json`](validation/haosenpeng-compound-fault.json)
记录场景/拓扑 SHA-256、软件版本、各阶段原始命令输出、设备退出码、判定、
规则计数和清理结果。`kind` 明确标记为 `live-network-validation-without-llm`。

本机复跑时也观察到一次**注入前**的 Kath3 基线失败：router1 的 `ripd` 进程
存在，但 `show ip rip` 返回 `RIP instance not found`，导致 router0 没有远端
路由。验证器在基线超时后拒绝注入并清理了该实验；失败记录留在本地
`faultbench/runs/haosenpeng-baseline-rejected.json`。这类部署/初始化失败不能
记成故障注入成功。若遇到相同问题，先检查 RIP 进程、running-config 和路由，
清理对应临时实验后重新运行；不要跳过基线门槛。
