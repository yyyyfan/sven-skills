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
