# 共用账号下的桌面端接入

## 关键区别

CODEX_HOME 隔开状态，个人启动入口隔开进程环境。不同 SSH 别名仍可能连接同一个 UID、同一个登录 Shell；别名本身不隔离任何数据。`codex --profile` 也不等于独立凭据目录。

桌面端会从远程登录 Shell 启动 Codex。只在手动 SSH 会话中 export，不能证明桌面端会继承。

## 接入决策

1. 如果当前桌面端确实提供每个远程连接的自定义启动命令或环境设置，用它指向个人包装器。先通过实际版本的界面/官方资料确认，不能假设该选项存在。
2. 否则，使用 SSH 连接专属的非敏感标记。先测试服务器已有的 AcceptEnv 规则是否接受 `LC_SVEN_CODEX_SESSION=sven`：在本次已验证的 SSH 别名上以 `-o SetEnv=LC_SVEN_CODEX_SESSION=sven` 新建会话，仅输出该变量核对。若实际接受，可免 sudo、免改 sshd 配置；不要假定所有服务器都接受 LC_*。个人 Host 写入相同 SetEnv，Shell 仅在值匹配时启用个人环境。若不接受，可按当前授权精确增加一个专用变量的 AcceptEnv 规则。更改共享 sshd 配置前说明影响，备份并验证配置有效性，保留已连接会话。避免宽泛开放 AcceptEnv * 或允许客户端任意设置 PATH/LD_PRELOAD。
3. 如果不能提供可验证的连接级启动方式，建议独立 Linux 用户。不要为方便而退回无条件修改共享 Shell 配置，也不要声称完全隔离已经实现。

条件启动片段的设计目标是：只有带个人标记的连接增加个人 PATH；普通连接保持原样。检查 bash 非交互提前 return、登录文件和 zsh 的实际读取顺序。Shell 文件变更要保留原内容并提供精准撤销方式。

已验证标记被接收后，bash 的条件片段示例：

```sh
if [ "${LC_SVEN_CODEX_SESSION:-}" = "sven" ]; then
  export PATH="$HOME/.sven/bin:$PATH"
  export CODEX_HOME="$HOME/.sven/.codex"
  export CODEX_INSTALL_DIR="$HOME/.sven/bin"
fi
```

CODEX_INSTALL_DIR 用于兼容桌面端启动时在 PATH 前添加安装目录的行为；最终以当前版本的实际启动和入口验证为准。

## 桌面端添加与发现

- 交付时给出确切个人 SSH 别名，避免用户选到缺少标记的原始 IP 或旧别名。
- 打开桌面端设置 → 连接 → SSH → 添加，选本次别名，再添加远程项目目录。别名应是 ~/.ssh/config 中的具体 Host，不能只有通配规则。
- 如果列表未出现，先核对配置文件路径、Host 块语法及 `ssh -G <别名>` 的必要解析字段，再建议重新打开设置或完全重启桌面端以重新读取配置；不承诺重启一定解决。
- 请求代为添加时先检查当前工具是否有受支持的连接管理接口或允许操作该应用的 UI 工具；可用则完成。不可用或明确受限时说明实际限制与最少手动步骤，不修改私有数据库来绕过。工具限制按本次会话核对，不将某版工具禁令固化为产品能力限制。
- 账号设备授权、SSH 连接注册、项目目录添加分别报告状态；缺少项目目录时可继续完成安装和网络验证，再询问用户。

远程进程若持久复用，同 UID 下的 app-server 复用范围也需要实际检查。核对个人状态目录和进程环境，避免连接到既有共享守护进程。CODEX_HOME 的设置不是守护进程隔离已成功的证据。

## 个人包装器示意

下面是安装后的入口逻辑；实际创建时采用本次选定端口、运行时路径。端口变量应受数字范围校验，而不是拼接未经检查的输入。

```sh
#!/bin/sh
export CODEX_HOME="$HOME/.sven/.codex"
export HTTP_PROXY=http://127.0.0.1:17897
export HTTPS_PROXY="$HTTP_PROXY"
export http_proxy="$HTTP_PROXY" https_proxy="$HTTP_PROXY"
export NO_PROXY=localhost,127.0.0.1,::1
export no_proxy="$NO_PROXY"
unset ALL_PROXY all_proxy
exec "$HOME/.sven/opt/codex/current/bin/codex" "$@"
```

在个人 CODEX_HOME 的 config.toml 中设置 `cli_auth_credentials_store = "file"`，用于确保凭据写入个人目录，而不是共用用户的系统钥匙串。登录也运行同一入口。

## 独立隧道

示意命令（主机别名和端口按本次配置）：

```sh
ssh -N -T -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -R 127.0.0.1:17897:127.0.0.1:7897 personal-host
```

该连接由本地维护；本地电脑、代理和隧道关闭后服务器会失去这条出网通道。相同服务器的端口由不同使用者分别分配。回环监听避免暴露公网，但不阻止同机其他用户访问代理端口。确认 sshd 的 GatewayPorts 不会扩大绑定范围。

## 对照验证

分别检查普通 SSH 连接与个人桌面端连接的 `command -v codex`、CODEX_HOME 和选定代理变量。只检查这些字段，不倾倒全部环境变量或凭据。确保退出个人连接后，普通会话的行为不变。
