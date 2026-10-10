# Windows 离线 SQLite 导入

以下是 ShellRS `user_version=14` 的实测布局，属于版本化参考。写入前用 `PRAGMA user_version` 和 `sqlite_master` 检查本机结构；不同版本按实际约束调整，不运行 schema 升级来适配导入。

官方源码：[ShellRS](https://github.com/since2006/shell-rs)，重点检查 `src/host/database.rs`、`src/host/model.rs`、`src/host/credential.rs`、`src/secrets/mod.rs` 和 Cargo.lock。本机安装版本与仓库最新代码可能不同。

## 停止、备份与写入

ShellRS 的主机数据会缓存在内存中，应用可能把缓存重新写回数据库。离线导入期间确保应用进程完全退出；只关闭窗口未必退出进程。

先查看进程和连接状态，尝试正常退出。存在活动连接且退出影响不明确时，先解决中断范围。无窗口或 `CloseMainWindow()` 失败不等于可以终止用户进程；只有明确属于本次任务启动的空闲进程才可在确认归属后终止。其他情况请求用户正常退出，或改用已授权的 CLI。

应用退出后，用 SQLite backup API 创建有时间戳的独立数据库。`shellrs.db` 在 WAL 模式下可能依赖 `-wal`；复制单个 db 文件不保证包含最新记录。可运行：

```powershell
python scripts/backup_sqlite.py --db "$env:APPDATA\shellrs\shellrs.db" --destination "D:\backups\shellrs.before-import.db"
```

helper 会拒绝覆盖已有备份，核验备份完整性和外键。回滚时同样退出应用，用备份恢复完整数据库状态，并处理旧 WAL/SHM，避免将旧事务重新应用；凭据管理器中的新增或修改条目需独立恢复。避免在使用中的数据库上替换文件。

写入连接启用 `PRAGMA foreign_keys=ON`，在 `BEGIN IMMEDIATE` 事务中参数化执行 insert/update。只改变计划中的记录，不整库重建。提交前检查 `PRAGMA foreign_key_check` 和 `PRAGMA integrity_check`。异常时回滚事务；提交后逐项读回核验。数据库与 Windows 凭据库没有跨存储事务，记录新建条目及原条目的可恢复状态，失败时按已完成阶段恢复；秘密不写进普通日志或明文备份。

## v14 的关键约束

| 表/字段 | 写入含义 |
| --- | --- |
| `hosts.id` | 内部整数 ID，保留现有值；新记录由 SQLite 分配 |
| `hosts.public_id` | 对外 ID；新建为唯一的 16 位字母数字串，更新保留 |
| `hosts.address`, `port` | 非空地址，端口 1–65535 |
| `hosts.auth` | `password`、`no-password`、`credential`；与 CLI 的 `no_password` 拼写不同 |
| credential 登录 | `credential_id` 非空，`username` 必须 NULL；有效用户名来自凭据 |
| 非 credential 登录 | `credential_id` NULL，用户名存入 `hosts.username` |
| `credentials.kind` | `password`、`key`、`agent` |
| key 凭据 | `key_path` 非空，用户名存入 `credentials.username`；其他种类 key_path 必须 NULL |
| `credentials.keychain_id` | 唯一的 16 位字母数字串，现有值保留 |
| `hosts.route` | `direct`、`jump`、`proxy`；proxy 有额外一致性约束 |
| `host_jumps` | `(host_id, position, jump_id)`；position 从 0 开始，不能指向自身 |

根分组通常为 `group_id=NULL`。分组、凭据和主机排序按所在集合追加。已有凭据按用户和规范化 key_path 复用；不要仅凭显示名复用。Windows 路径比较考虑大小写和分隔符，保留确实存在的私钥路径。新 ID 检查唯一性并在冲突时重新生成。

v14 不提供 OpenSSH 保活或主机密钥校验的逐主机字段。备注只是参考，不会实现 `StrictHostKeyChecking no` 或 `UserKnownHostsFile NUL`。

## Windows 密码格式

先确认目标二进制对应的 keyring 后端配置。以下来自 `keyring 4` + `windows-native-keyring-store 1.1.0` 默认实现，不能当成任意版本的固定格式。源码可通过 [crates.io 版本页](https://crates.io/crates/windows-native-keyring-store/1.1.0) 核验。

- ShellRS 的 service 为 `shellrs`。
- 主机密码 account 为 `password:<user>@<host>:<port>`。
- 密码凭据 account 为 `credential:<keychain_id>`。
- 私钥口令 account 为 `passphrase:<key_path>`，使用应用保存的路径表示。
- 此后端默认 Windows target 为 `<account>.shellrs`；`CREDENTIALW.Type=1`（GENERIC），blob 是无终止符的 UTF-16LE 密码字节。默认持久化值从对应后端版本确认，当前离线导入使用 `Persist=2`（LOCAL_MACHINE，当前用户持久存储）。

使用 `CredWriteW`/`CredReadW` 时声明准确的 ctypes 结构和参数类型，注意 64 位指针对齐；缓冲区在 API 调用期间保持存活。保存后读回比较字节，只打印成功状态，最后 `CredFree` 并清除临时缓冲区。保留已有条目的属性；空密码、加密私钥口令和其他凭据种类按本次来源处理，不能猜测。

结束后重新启动应用。后台启动遵循本机隐藏窗口约定；启动进程成功不代表已检查 UI。读回 SQLite 检查主机和凭据计数及关键字段；若外部 CLI 已启用，可再读 `hosts show` 验证应用内存中的配置。
