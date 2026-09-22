# 共用账号下的桌面端接入

## 关键区别

CODEX_HOME 隔开状态，个人启动入口隔开进程环境。不同 SSH 别名仍可能连接同一个 UID、同一个登录 Shell；别名本身不隔离任何数据。`codex --profile` 也不等于独立凭据目录。

桌面端会从远程登录 Shell 启动 Codex。只在手动 SSH 会话中 export，不能证明桌面端会继承。

## 接入决策

1. 如果当前桌面端确实提供每个远程连接的自定义启动命令或环境设置，用它指向个人包装器。先通过实际版本的界面/官方资料确认，不能假设该选项存在。
2. 否则，可考虑 SSH 连接专属的非敏感标记，例如本地专用 Host 的 `SetEnv SVEN_CODEX_SESSION=1`，远程 Shell 仅在该标记出现时将 `$HOME/.sven/bin` 放入 PATH。此方式需要服务器精确接受该标记；`SetEnv` 本身不保证服务器接受。避免宽泛开放 `AcceptEnv *` 或允许客户端任意设置 PATH/LD_PRELOAD。更改共享 sshd 配置前，说明具体改动和影响，按当前授权处理；验证配置有效性，保留已连接会话，避免使他人失联。
3. 如果不能提供可验证的连接级启动方式，建议独立 Linux 用户。不要为方便而退回无条件修改共享 Shell 配置，也不要声称完全隔离已经实现。

条件启动片段的设计目标是：只有带个人标记的连接增加个人 PATH；普通连接保持原样。检查 bash 非交互提前 return、登录文件和 zsh 的实际读取顺序。Shell 文件变更要保留原内容并提供精准撤销方式。

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
