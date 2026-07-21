# 方案：为 douyin-downloader 添加 "我的喜欢" 模式

**作者**：Nick + Hermes
**日期**：2026-07-21
**状态**：✅ **已实施并测试通过**（commit `d1096f3`，2026-07-21）
**关联 SKILL**：`/root/.hermes/skills/creative/douyin-download/references/login-with-vnc-and-playwright.md`

---

## 一、背景与动机

`jiji262/douyin-downloader` v2.0 当前支持的 mode：

| mode | 含义 | 是否支持"自己" |
|------|------|----------------|
| `post` | 用户主页作品 | ❌（必须传别人 sec_uid） |
| `like` | 用户主页的"喜欢"列表 | ❌（同上） |
| `mix` / `music` | 合集/音乐 | ❌ |
| `collect` / `collectmix` | 当前登录账号的**收藏夹** | ✅ `/user/self?showTab=favorite_collection` |

**缺失能力**：下载**当前登录账号自己的"喜欢"列表**（双击❤ 收藏的那些视频/图文）。

抖音网站本身有 `/user/self?showTab=like` 页面（仅登录可见），但工具没有对应的 mode。

---

## 二、可行性分析

### 2.1 API 已就绪

`core/api_client.py:442` 已有 `get_user_like(sec_uid, ...)`：

```python
async def get_user_like(self, sec_uid, max_cursor=0, count=20):
    params = await self._build_user_page_params(sec_uid, max_cursor, count)
    raw = await self._request_json("/aweme/v1/web/aweme/favorite/", params)
    return self._normalize_paged_response(raw, item_keys=["aweme_list"])
```

endpoint `/aweme/v1/web/aweme/favorite/` 是抖音"喜欢"接口（注意：抖音 API 命名 `favorite` 就是"喜欢"❤，`collect` 才是"收藏夹"⭐）。

### 2.2 URL parser 已能解析 `/user/self`

- `_extract_user_id`（url_parser.py:81）正则 `/user/([A-Za-z0-9_-]+)` ✅ 匹配 `self`
- `parse_url_type`（validators.py:128）`/user/` in path → `"user"` ✅

### 2.3 唯一缺：注册新 mode + 走 self 路径

`like_strategy.py` 现成（5 行代码）。只需要：
1. 新增 `my_like_strategy.py`，传 `sec_uid="self"`
2. 在 `user_mode_registry.py` 注册
3. 在 `user_downloader.py` 把 `my_like` 加入 `SELF_COLLECT_MODES`（或新建 `SELF_LIKE_MODES`）

---

## 三、当前前提（写于 2026-07-21 测试完成后）

### 3.1 已就绪

| 前提 | 状态 | 路径 |
|------|------|------|
| 仓库已 clone 到本地 | ✅ | `/root/workspace/douyin-downloader/` |
| Python venv | ✅ | `/root/workspace/douyin-downloader/.venv/` |
| 依赖已装 | ✅ | `pip install -r requirements.txt` 完成 |
| Playwright + Chromium | ✅ | `pip install playwright && python -m playwright install chromium` |
| noVNC 服务 | ✅ | `websockify --web=/usr/share/novnc 0.0.0.0:6080 localhost:5902` PID 4012267 |
| DISPLAY :2 健康 | ✅ | Xtightvnc PID 4043026，systemd `xtightvnc.service` |
| VNC 密码 | ✅ | `123321q`（已重置，2026-07-21） |
| 登录态 | ✅ | `config/cookies.json` 50 个 cookie（缺 msToken） |
| cookies 已合并 | ✅ | `test_config.yml` 的 `cookies:` 段 |

### 3.2 当前 cookies 详情

- **总数**：50 个
- **REQUIRED 命中**：ttwid(127)、passport_csrf_token(32)、odin_tt(128)、sessionid(32)、sid_guard(93) ✅
- **REQUIRED 缺失**：msToken（**空字符串**） ⚠️
- **能跑通**：`mode: post` 单链接图文下载（已验证，见 `/root/workspace/douyin-downloader/test_output/`）
- **sessionid 来源**：登录用户在 noVNC 里的 chromium 浏览器手动扫码登录后，由 `simple_cookie_fetcher.py` 抓取

### 3.3 测试样例（已验证）

- 链接：`https://v.douyin.com/MM1kQo3E0oo/`
- 作者：海山动
- 作品：缘分太随便就会错过 太认真就会难过。
- ID：`7664234707094520945`
- 输出：`/root/workspace/douyin-downloader/test_output/海山动/.../1.jpg + 2.jpg + data.json`
- 总大小：1.1MB

### 3.4 飞书发送结果

4 条消息已发到 `oc_215669695255db9a31871a9fd0807695`：

| message_id | 内容 |
|-----------|------|
| `om_x100b6ac62dc528a0c1fc7a843f2921c` | 图 1（564K） |
| `om_x100b6ac62dacb0b8c1b49d5b88cf086` | 图 2（433K） |
| `om_x100b6ac62aa980a4c1c631d7177d9c5` | metadata JSON（36K） |
| `om_x100b6ac62ba524b4c3aaff8e35ca5cd` | markdown 总结 |

### 3.5 启动命令模板

```bash
# 激活 venv
cd /root/workspace/douyin-downloader
source .venv/bin/activate

# 跑图文
python run.py -c test_config.yml -u "<链接>" -t 4 -p ./test_output

# 后台跑 cookie_fetcher（如 cookie 失效需要重抓）
python tools/simple_cookie_fetcher.py
```

### 3.6 已知问题 / 遗留事项

1. **`msToken` 缺失**：抖音 API 部分 endpoint 要求 msToken，当前 cookies 没有。**本测试的图文下载没用到**——证明 `aweme/detail` 这条 path 不强依赖；但 `aweme/favorite/`（我的喜欢 API）**可能需要**。需要先实测。
2. **chromium-headless-shell**：playwright 装的是 headless shell（114MB），非完整 chromium（~300MB）。**手动登录场景**够用，但若需 headful debugging 可能要装完整版。
3. **simple_cookie_fetcher.py** 是临时写的简化版（绕开原版 cookie_fetcher 的 stdin EOF 问题），没提交到原仓。
4. **VNC 重启不影响**：systemd `xtightvnc.service` 自动起，密码 `123321q` 持久化在 `/root/.vnc/passwd`。

---

## 四、实施计划（待确认）

### 4.1 改动清单（预估）

| # | 文件 | 改动 | 行数 |
|---|------|------|------|
| 1 | `core/user_modes/my_like_strategy.py` | **新建**：复制 like_strategy.py，sec_uid 强制为 "self" | +10 |
| 2 | `core/user_modes/__init__.py` | **修改**：加 import + __all__ | +2 |
| 3 | `core/user_mode_registry.py` | **修改**：注册 `"my_like": MyLikeUserModeStrategy` | +2 |
| 4 | `core/user_downloader.py` | **修改**：新建常量 `SELF_LIKE_MODES = {"my_like"}`，在 `_resolve_user_info` 加分支（仿 SELF_COLLECT_MODES） | +10 |
| 5 | `config.example.yml` | **修改**：加 `my_like: 0` 到 number 段 | +1 |
| 6 | `README.md` / `README.zh-CN.md` | **修改**：加 my_like 文档 | +5 |
| 7 | （可选）`tests/` | 加单测 | +30 |

### 4.2 关键技术点

```python
# my_like_strategy.py 伪代码
class MyLikeUserModeStrategy(BaseUserModeStrategy):
    mode_name = "my_like"
    api_method_name = "get_user_like"

    async def collect_items(self, sec_uid, user_info):
        # 强制用自己的 sec_uid（API 接受 "self"）
        async for page in self.downloader.api_client.get_user_like(
            sec_uid="self", max_cursor=0, count=20
        ):
            yield page
```

### 4.3 user_downloader.py 的 _resolve_user_info 分支

现有逻辑：

```python
SELF_COLLECT_MODES = {"collect", "collectmix"}

if sec_uid == "self" and normalized_modes.issubset(self.SELF_COLLECT_MODES):
    return {"uid": "self", "sec_uid": "self", "nickname": "self"}
```

需要新增：

```python
SELF_LIKE_MODES = {"my_like"}

if sec_uid == "self" and normalized_modes.issubset(self.SELF_LIKE_MODES):
    return {"uid": "self", "sec_uid": "self", "nickname": "self"}
```

**注意**：`my_like` 和 `collect` 互斥——`my_like` 应该独立使用（参考 README 对 `collect` 的限制："must be used alone and cannot be combined"）。

### 4.4 测试步骤

```bash
# 1. 改完代码后，先 dry-run（小批量）
mode: [my_like]
number: { my_like: 5 }  # 加这个 key
link:
  - https://www.douyin.com/user/self?showTab=like

python run.py -c test_config.yml -u "https://www.douyin.com/user/self?showTab=like" -t 2 -p ./test_my_like -v --show-warnings

# 2. 检查输出
ls -lh ./test_my_like/self/
cat ./test_my_like/self/*/..._data.json | jq '.aweme_list | length'

# 3. 验证 dump 出的 aweme_id 真是自己"喜欢"过的
# （通过作品的 aweme_id 反查 /aweme/v1/web/aweme/detail/ 看 desc）
```

### 4.5 风险评估

|| 风险 | 等级 | 缓解 | 实际结果 |
||------|------|------|---------|---------|
| 抖音反爬 | 🟡 中 | 启用 `browser_fallback.enabled: true`；限制 `number.my_like: 5` | ✅ API 无拦截 |
| msToken 缺失 | 🟡 中 | 跑一次观察 API 响应 | ✅ 缺 msToken 不影响 /aweme/favorite/ |
| 改动污染主仓 | 🟢 低 | 全部改动可单独 revert；不动 like_strategy.py | ✅ 已验证 |
| 影响现有 mode | 🟢 低 | `my_like` 完全独立分支，零交集 | ✅ 测试 `post` 模式正常 |
| 当前账号被风控 | 🟡 低-中 | 自己看自己的"喜欢"是低风险行为 | ✅ 正常 |

### 4.6 回滚方案

所有改动都是**新增 + 注册**，不动现有逻辑：

```bash
# 改坏了？一行回滚：
cd /root/workspace/douyin-downloader
git checkout core/user_modes/__init__.py core/user_mode_registry.py core/user_downloader.py
rm core/user_modes/my_like_strategy.py
```

---

## 五、交接清单（给接手的人）

### 5.1 一句话总结

> **要做的事**：在 `core/user_modes/` 新增 `my_like_strategy.py`，让 `mode: my_like` 能下载当前登录账号的"喜欢"列表，链接 `/user/self?showTab=like`。API 已有 `get_user_like`，URL parser 已能解析 `/user/self`，只需注册新 mode + 在 `_resolve_user_info` 加 self 分支。

### 5.2 必须看的文件（按顺序）

1. `core/api_client.py:442` —— `get_user_like` 实现（看 endpoint + 参数）
2. `core/user_modes/like_strategy.py` —— 现有 like mode（5 行）
3. `core/user_modes/collect_strategy.py` —— 类似工作流的 self 模式（参考）
4. `core/user_mode_registry.py` —— 注册表
5. `core/user_downloader.py:13` —— `SELF_COLLECT_MODES` 常量（要照抄）
6. `core/user_downloader.py:129-145` —— `_resolve_user_info`（要加分支）
7. `core/url_parser.py:81` —— `_extract_user_id`（不用改，确认能解析 `/user/self`）
8. `utils/validators.py:128` —— `parse_url_type`（不用改，确认 `/user/` 走 user 分支）

### 5.3 实操命令速查

```bash
# 进项目 + venv
cd /root/workspace/douyin-downloader
source .venv/bin/activate

# 看 noVNC 状态（应该 0.0.0.0:6080 listening）
ss -tlnp | grep -E ":(6080|5902)"

# 看 VNC 状态
systemctl status xtightvnc

# 看 cookies 状态
python3 -c "import json; d=json.load(open('config/cookies.json')); print(f'{len(d)} cookies, msToken={\"yes\" if d.get(\"msToken\") else \"NO\"}')"

# 跑当前已验证的图文链接（参考 baseline）
python run.py -c test_config.yml -u "https://v.douyin.com/MM1kQo3E0oo/" -t 4 -p ./test_output

# 改完代码后跑 my_like 模式（小批量）
python run.py -c test_config.yml -u "https://www.douyin.com/user/self?showTab=like" -t 2 -p ./test_my_like -v

# 没 noVNC 时手动抓 cookie
python tools/simple_cookie_fetcher.py
```

### 5.4 联系方式

- Notion Self开发 页同步本方案
- 飞书 ops/dev 频道：oc_bef7bb9 / oc_ee4185c
- 关键人物：Nick

---

## 六、待 Nick 确认

- [ ] 是否在**当前登录账号**上测？（推荐：是）
- [ ] 第一次 `number.my_like: 5` 是否合适？（推荐：5，先小批量）
- [ ] 是否需要 backfill msToken？（推荐：先不，跑一次看 API 响应再决定）
- [ ] 是否同步到 Notion Self开发 页？（推荐：是，本文件已就绪）
- [ ] 是否顺便给 Notion GitHub Links DB 那 4 条未打标条目补关键词？（独立任务）

---

**下一步**：等 Nick 确认本方案 → 实施 → 测试 → 飞书发结果 → Notion 归档。