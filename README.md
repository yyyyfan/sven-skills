# Sven Skills

个人 Codex 技能集合。

## sven-remote-codex

为无法直接联网的 Linux 服务器配置 Codex 桌面端 SSH 项目，通过本地代理联网，并使用独立的 `~/.sven/.codex`。包含完整运行时安装、共享账号配置隔离、后台隧道维护，以及认证与代理排障。

模型调用仍然需要通过代理访问网络；本技能不提供完全离线的模型运行环境。

### 安装

在有此私有仓库访问权限的 Codex 中输入：

> 使用 skill-installer 从 https://github.com/yyyyfan/sven-skills 安装 skills/sven-remote-codex。

安装后重新打开 Codex，使用：

> 使用 $sven-remote-codex 配置我的远程 Linux 服务器，通过本地 7897 代理联网，CODEX_HOME 使用 ~/.sven/.codex。

提供目标服务器、SSH 用户和密钥位置；已有连接可直接指定 SSH 别名。

### 同步

GitHub 保存技能文件版本。本地技能修改需要提交和推送；其他设备需要安装或更新，仓库不会自动同步 Codex 登录状态或代理进程。

仓库只包含技能及说明，不包含真实服务器连接配置、私钥、登录令牌和运行日志。

## shellrs-ssh-import

将本地 OpenSSH/tssh 主机配置导入 Windows ShellRS。支持官方 CLI 和离线 SQLite 写入，包含一致性备份、主机去重、私钥凭据关联、Windows 密码存储格式及导入后核验。无法等价映射的 SSH 选项会明确说明。

### 安装与使用

> 使用 skill-installer 从 https://github.com/yyyyfan/sven-skills 安装 skills/shellrs-ssh-import。

安装后重新打开 Codex，使用：

> 使用 $shellrs-ssh-import 将本地 SSH 配置直接写入 ShellRS 的 SQLite，保留已有配置，先备份并核验导入结果。

离线方式需要 ShellRS 完全退出，不需要启用外部 CLI。数据库结构和凭据格式按本机版本核对；配置导入成功与实际连接成功分别验证。

## grok（Grok Bot 专属技能）

`skills/grok/` 下存放 Grok Bot 使用的技能。

### hf-to-obs-transfer

从 Hugging Face 下载数据集或模型并转存到华为云 OBS。内置实测最优参数：下载 8 并发（约 600 MB/s），`obsutil` 上传 16 线程、16MB 分片（单进程约 34 MB/s），3 个上传进程并行、边下边传（合计约 60–74 MB/s，每 100GB 约 26 分钟）。仓库不包含 AK/SK，需在本机 `~/.obsutilconfig` 自行配置。
