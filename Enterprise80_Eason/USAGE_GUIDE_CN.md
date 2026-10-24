# Enterprise80 v2 — 中文使用指南

## 重要说明
此版本加入**显式配置脚本**：不依赖 Kathará 是否自动执行 `.startup`，而是逐台进入同一 lab 的 Docker 容器执行配置并检查错误。已做静态检查，**没有在你的 Mac / Docker / Kathará 环境实机运行**，因此不能承诺零兼容性问题。

在 `Enterprise80_Eason` 根目录运行（不要在旧版目录运行）：

```bash
chmod +x scripts/*.sh
kathara lclean -d topology_kathara/Enterprise80
kathara lstart --noterminals -d topology_kathara/Enterprise80
./scripts/provision.sh
sleep 35
./scripts/verify_healthy.sh
```

`lclean` 只清理 Enterprise80，不会清除其他 labs。`--noterminals` 不会弹出 80 个窗口。若验证 PASS，再运行：

```bash
./scripts/inject_fault.sh
./scripts/verify_fault.sh
./scripts/recover.sh
```

结束：

```bash
kathara lclean -d topology_kathara/Enterprise80
```

检查单台设备：

```bash
./scripts/device.sh sydr1 ip -br addr
./scripts/device.sh sydr1 vtysh -c 'show ip ospf neighbor'
```

`kathara connect sydr1` 若遇到同名 lab 冲突，请使用 `scripts/device.sh`。如果 provisioning 出错，脚本会停在出错设备，贴出**第一处 ERROR 和前后日志**，不要继续注入故障。
