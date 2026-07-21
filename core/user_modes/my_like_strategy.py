from __future__ import annotations

from typing import Any, Dict, List

from core.user_modes.base_strategy import BaseUserModeStrategy


class MyLikeUserModeStrategy(BaseUserModeStrategy):
    """下载当前登录账号的"喜欢"列表（❤）。

    与 LikeUserModeStrategy 的区别：
    - like       → 需要传入别人的 sec_uid，查该用户的喜欢列表
    - my_like    → 强制使用 sec_uid="self"，查当前登录账号的喜欢列表

    API endpoint 同 like（/aweme/v1/web/aweme/favorite/），只是 context 不同。
    """

    mode_name = "my_like"
    api_method_name = "get_user_like"

    async def collect_items(self, sec_uid: str, user_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        # 强制使用 "self"——API 会返回当前登录账号的喜欢列表
        return await self._collect_paged_entries(
            self.downloader.api_client.get_user_like,
            "self",
        )
