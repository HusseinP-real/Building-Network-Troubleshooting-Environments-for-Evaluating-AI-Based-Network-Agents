# Campus80：完整拓扑与 OSPF 故障注入

此包保留 campus80_fixed.zip 的 80 节点拓扑和启动配置，新增可复现的 healthy → fault → recovery 流程。Python 3 标准库即可运行；宿主机需有 Docker、Kathará，镜像内需有 FRR、ip、ping、pgrep、pkill。

## 两个拓扑能否使用同一种 fault？

可以。采用 Enterprise80_Final_v2 相同的 `routing_daemon_down`：先停止 watchfrr，防止自动拉起，再停止网关的 ospfd。接口、地址、zebra 和容器保持运行。

| 项目 | Enterprise80 v2 | Campus80 |
|---|---|---|
| 故障设备 | sydr1 | r01 |
| 故障组件 | ospfd | ospfd |
| 受影响 LAN | 10.10.10.0/24 | 10.10.1.0/24 |
| 受影响终端 | sydpc1–sydpc9 | pc01–pc05 |
| 本地网关 | 10.10.10.1 | 10.10.1.1 |
| 远端探针 | web1 | srv01，10.10.3.100 |

这是“一种故障类型、两个拓扑上的两个实例”。设备与 IP 参数不同，不能原样运行 Enterprise 的硬编码脚本。相同故障类型适合比较跨拓扑诊断表现，但不能据此声称覆盖多种故障，或两个拓扑具有相同难度。r01 同时承担转发任务，其停止参与 OSPF 后其他路径会重收敛。

## 网络是否完成？

文件包含 12 路由器、60 PC、8 服务器、20 条 /30 链路、12 个 /24 LAN、主机默认路由和 OSPF area 0 配置。静态一致性检查已通过。网络基线是否工作，以本机 `verify_healthy.sh` 的运行结果为准。HTTP 是可选启动服务，当前验收覆盖 IPv4/ICMP 和 OSPF，不验证 HTTP 应用；未实现外网、DNS、DHCP 等额外服务。

## 使用已有的 Campus80

解压后进入本文件所在目录。如果当前已运行同一份 Campus80，无需重新启动，直接：

```bash
bash scripts/verify_healthy.sh
bash scripts/inject_fault.sh
bash scripts/verify_fault.sh
# 在故障状态进行诊断、记录结果；完成后恢复：
bash scripts/recover.sh
```

注入脚本会先完整验证健康状态，失败则不注入。注入成功后保持故障状态，直到恢复。若注入过程中报错，可能已停止部分进程，请运行恢复脚本。不要把再次注入当成恢复方法。

## 从新目录启动

仅在没有运行 Campus80 时：

```bash
kathara lstart -d . --noterminals
# 等待启动脚本完成、OSPF 收敛；繁忙机器可能需要更多时间。
sleep 90
bash scripts/verify_healthy.sh
bash scripts/inject_fault.sh
bash scripts/verify_fault.sh
bash scripts/recover.sh
```

若旧目录的 Campus80 正在运行，继续使用已有实例，或自行从旧目录停止旧实例后再启动新目录。不要混用两份实例。Enterprise 和其他实验可以同时运行，脚本只匹配选中的 Campus 容器。

## 一键实验（要求实验已启动）

```bash
bash scripts/run_demo.sh
```

该命令检查健康基线、注入并验证故障，然后恢复并重新验证基线。进入注入阶段后使用 finally 尝试恢复，包含注入验证失败的情况；宿主机崩溃、强制杀进程等仍需手动恢复。不会启动或清理任何实验。

## 容器选择与日志

脚本要求恰好一个运行中的 Kathará `r01`，并用其完整前缀和实验后缀匹配所有 80 台设备；不会选择第一个模糊匹配的容器。执行前检查 r01 地址与 manifest 一致。

多份 Campus 同时运行时，先查看 `docker ps --format '{{.Names}}'`，再设置准确的名称：

```bash
export CAMPUS_ANCHOR='填入目标实验的完整r01容器名'
bash scripts/verify_healthy.sh
```

所有运行命令、输出、退出码与 UTC 时间保存在 `logs/`。错误不会被当作“故障注入成功”：ping 要解析收到的报文数，Docker 失败、命令不存在、无法解析输出均报错。

## 验收内容

- 健康：80 台设备的接口及 IP、12 台路由器的 ospfd/zebra 与转发开关、所有预期 FULL 邻居、68 个终端的跨 LAN 探针。
- 故障：r01 全部接口和地址保留、ospfd/watchfrr 不运行、zebra 仍运行；其余路由器的预期邻居与 LAN01 路由撤销；5 台受影响 PC 能访问网关但不能访问 srv01；同 LAN 通信正常；反向探针失败；其他 11 个 LAN 的代表 PC 能访问 srv01。
- 恢复：重启 r01 FRR，从持久化 frr.conf 重新加载配置，健康检查全部通过，watchfrr 恢复。

故障/恢复阶段重复检测实际状态，最多等待约 180 秒加上单轮检查耗时；不是只睡固定秒数便宣告成功。端点探针不是全网任意两点的全组合测试。

## 文件

- `fault.py`：完整实现；`python3 fault.py static` 可离线检查。
- `scripts/*.sh`：与 Enterprise 接近的命令入口。
- `lab.conf`、`*.startup`、`rXX/etc/frr/frr.conf`：完整网络。
- `ground_truth.json`：正确答案与预期现象。
- `dataset/campus80_Q/base/`：场景描述。
- `VALIDATION.md`：交付时的测试范围与结果。

评估诊断 Agent 时只提供场景的 PROMPT 和观察权限，不应把 ground truth、注入源码和修复答案同时提供给它。本包没有自动集成 NIKA/SADE/FaulT-Bench runner。
