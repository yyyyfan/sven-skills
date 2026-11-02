---
name: easytier
description: 用 EasyTier 把一台有公网 IP 的服务器、若干无公网 IP 的机器和本机组成虚拟局域网（固定 VIP、systemd/tmux 常驻、密钥 SSH）；适用于新组网、节点搬迁后恢复、以及经虚拟 IP 做 SSH 跳板。
---

# EasyTier 组网

把多台机器用 EasyTier 组成同一虚拟二层/三层网络，让无公网 IP 的节点也能被 SSH 或其它服务访问。用中文报告结果；**不要**把网络密码、私钥或完整 `authorized_keys` 打进聊天或提交进仓库。

## 何时使用

- 新建「公网中继 + 私网节点 + 笔记本」拓扑
- 某台机器重启/换盘后 EasyTier 或虚拟网卡丢失，需要恢复
- 只允许经虚拟 IP 做密钥 SSH，并在 TUN 口上收紧防火墙

不要用本 skill 去改无关业务防火墙，也不要把 EasyTier 监听口暴露到不必要的公网端口。

## 角色与固定约定

| 角色 | 典型要求 | EasyTier 形态 |
|------|----------|----------------|
| 公网中继 | 有公网 IP；云安全组放行 **TCP+UDP 11010**（或你选定的监听口） | `--hostname` 固定；`-l tcp://0.0.0.0:PORT -l udp://0.0.0.0:PORT`；固定 VIP |
| 私网节点 | 无公网或只出站；需要被 SSH | `-p tcp://公网IP:PORT -p udp://公网IP:PORT`；建议 `--no-listener`；固定 VIP |
| 笔记本/工作站 | Windows / macOS / Linux | GUI 或 CLI；填同一网络名与密码；固定 VIP；初始节点指向公网中继 |

所有节点必须共享：

- `--network-name <NAME>`
- `--network-secret <SECRET>`（只放在 `chmod 600` 的本地文件或 systemd `EnvironmentFile`，不要写进 git）
- 规划好的互不冲突的虚拟 IPv4（关掉 DHCP 时自行指定 `-i`）

版本以 [EasyTier Releases](https://github.com/EasyTier/EasyTier/releases) 为准；下文示例以 `v2.6.x` 的 `easytier-core` / `easytier-cli` 为准，架构按目标机选 `linux-x86_64`、`linux-aarch64`、`windows-x86_64`、`macos-aarch64` 等。

## 执行流程

### 1. 确认参数

向用户确认或复用已提供的字段（缺什么问什么，不要沿用历史网络的真实密码）：

- 网络名、网络密码存放路径
- 各节点 hostname、虚拟 IP、体系结构
- 公网中继的公网 IP 与监听端口（默认 11010）
- 私网节点上要暴露的服务（常见仅 SSH 22）
- 目标机能否访问 GitHub；不能则改为本机下载后 `scp` 二进制

### 2. 安装二进制

1. 从官方 Release 下载对应平台 zip，校验后安装 `easytier-core`、`easytier-cli`。
2. 公网服务器若拉取 GitHub 很慢或失败：在能访问的机器上下载，再 `scp` 到服务器并 `install` 到 `/usr/local/bin/`（或用户目录）。
3. **会丢系统盘/会重装的节点**（云电脑迁移、只保留 `$HOME` 等）：把二进制放在 `$HOME/easytier/bin/`，不要只装在 `/opt` 或依赖临时 apt 包。

### 3. 公网中继（systemd 推荐）

1. 云厂商安全组 / 本机防火墙放行监听口的 TCP 与 UDP。
2. 密码文件示例（路径可改，权限必须 600）：

```bash
printf 'ET_NETWORK_SECRET=<SECRET>\n' | sudo tee /etc/easytier.env >/dev/null
sudo chmod 600 /etc/easytier.env
```

3. systemd unit 要点：`EnvironmentFile` 注入 secret；`ExecStart` 使用 `--network-name`、`-i <中继VIP>`、`--hostname <名>`、双协议 `-l`；`Restart=always`。
4. `systemctl enable --now easytier` 后执行 `easytier-cli peer`，应能看到本节点。

中继**不要**把无关业务端口（例如未鉴权的 Docker API）绑到 `0.0.0.0` 还指望 EasyTier「隔离」——虚拟网内其它节点仍可能扫到，见第 5 步防火墙。

### 4. 私网节点 / 笔记本

**CLI 要点：**

```bash
easytier-core \
  --network-name <NAME> \
  --network-secret <SECRET> \
  -i <本机VIP> \
  --dev-name <tun名> \
  --hostname <名> \
  -p tcp://<公网IP>:<PORT> \
  -p udp://<公网IP>:<PORT> \
  --no-listener \
  --multi-thread
```

**GUI：** 网络名、密码、虚拟 IPv4（关 DHCP）、初始节点 `tcp://公网IP:PORT`（可再加 udp）。

**常驻：**

- Linux 服务器：systemd（同中继，但用 `-p` 而非对外 `-l`）
- 易丢进程、不便 systemd 的环境：tmux/supervisor 循环拉起 `easytier-core`，退出后 sleep 再启，并写日志
- Windows：管理员权限；zip 内 `wintun.dll` 与 exe 同目录

### 5. 仅经虚拟网提供 SSH（推荐）

目标：虚拟网卡上**只**放行 SSH 与 ICMP，其它入站丢弃（避免虚拟网内扫到未加固服务）。

1. `sshd` 配置（`sshd_config.d` 片段即可）：
   - `ListenAddress 127.0.0.1`
   - `ListenAddress <本机VIP>`
   - `PasswordAuthentication no`
   - `KbdInteractiveAuthentication no`
   - `PermitRootLogin no`
   - `AllowUsers <ssh用户>`
2. 把客户端公钥写入该用户的 `~/.ssh/authorized_keys`（权限 600/700）。
3. 在 TUN 设备上用 iptables/nftables：允许 established、tcp/22、icmp，其余 INPUT/FORWARD 丢弃。规则用「不存在再添加」的方式，避免重复堆积。
4. EasyTier 起来、VIP 出现后再（重新）启动 `sshd`，确保绑定到 VIP。
5. **会换机/丢 `/etc` 的节点**：把 `sshd` 片段、host keys 备份到 `$HOME/easytier/`，启动脚本里先还原再启 `sshd`，避免每次换机指纹变化或丢密钥登录配置。

登录示例：

```bash
ssh <user>@<节点VIP>
# 或经已在网内的中继跳转
ssh -J <user>@<公网IP或中继VIP> <user>@<节点VIP>
```

### 6. 验证

在任一已加入节点上：

```bash
easytier-cli node          # 本机 VIP / hostname
easytier-cli peer          # 应看到其它节点；关注 cost、lat、loss、tunnel
ip -br addr show           # TUN 上应有规划的 VIP
ss -ltn | grep ':22'       # SSH 是否听在 VIP（若按第 5 步加固）
```

连通性用 `ping <对端VIP>` 或 `ssh`；不要把网络密码打印到输出里。

## 排障清单

| 现象 | 优先检查 |
|------|----------|
| `easytier-cli` Connection refused | `easytier-core` 未运行；看日志 / systemd / tmux |
| peer 里看不到对端 | 网络名/密码是否一致；中继安全组是否放行 TCP+UDP；`-p`/`-l` 端口是否一致 |
| 有 VIP 但 SSH Permission denied (publickey) | 客户端是否用对了密钥；`authorized_keys` 是否含该公钥；`AllowUsers` / 文件权限 |
| 换机后 Host key 变化 | 是否未还原备份的 host keys；客户端 `ssh-keygen -R <VIP>` 后重连 |
| 休眠/暂停后整网失效 | 进程被冻住或杀掉；唤醒后重跑启动脚本；需要保活则用外部定时任务周期性唤醒该环境 |
| 目标机 apt 丢包、无 `sshd`/`iptables` | 启动脚本应能 `apt-get install` 补齐，或镜像预装 |

## 完成标准

- 各规划节点出现在 `easytier-cli peer` 中，VIP 正确
- 笔记本（或管理机）能 `ssh` 到约定 VIP（密钥登录若已要求）
- 网络密码只存在于本地受限文件，未写入公开仓库或聊天记录
- 若做了 TUN 防火墙：虚拟口上非 22/icmp 的入站被拒绝
- 交付：网络名、各 VIP/hostname、监听端口、启动/停止方法、日志位置；**不**交付明文 secret

## 调用示例

“使用 $easytier 在公网机 A 和内网机 B 之间组网，VIP 段 10.144.144.0/24，只开放 SSH。”

“使用 $easytier 恢复重启后丢失的内网节点，二进制放在家目录。”

## 当前资料来源

使用前核对当前官方发布与目标机架构对应的二进制：

- https://github.com/EasyTier/EasyTier
- https://github.com/EasyTier/EasyTier/releases

本 skill 是通用部署模板；具体网络名、密码、IP 以当次用户确认的值为准。
