"""账号管理器"""

from pathlib import Path
from typing import Literal
import yaml
import random

from uploader.account_manager.models import Account
from utils.log import taobao_guanghe_logger


class AccountManager:
    """账号管理器"""

    def __init__(self, config_file: str | Path = "accounts.yaml"):
        self.config_file = Path(config_file)
        self.accounts: dict[str, Account] = {}

        if self.config_file.exists():
            self.load_config()

    def load_config(self):
        """从配置文件加载账号"""
        with open(self.config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        for acc_data in config.get('accounts', []):
            account = Account(**acc_data)
            self.accounts[account.name] = account

        taobao_guanghe_logger.info(f"✅ 加载 {len(self.accounts)} 个账号")

    def save_config(self):
        """保存配置到文件"""
        config = {
            'accounts': [
                {
                    'name': acc.name,
                    'display_name': acc.display_name,
                    'platform': acc.platform,
                    'cookie_file': str(acc.cookie_file),
                    'enabled': acc.enabled,
                    'group': acc.group,
                    'priority': acc.priority,
                    'max_daily_uploads': acc.max_daily_uploads,
                    'proxy': acc.proxy,
                    'remark': acc.remark,
                }
                for acc in self.accounts.values()
            ]
        }

        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True)

    def get_account(self, name: str) -> Account | None:
        """获取指定账号"""
        return self.accounts.get(name)

    def get_available_accounts(
        self,
        group: str | None = None,
        platform: str | None = None
    ) -> list[Account]:
        """获取可用账号列表"""
        accounts = list(self.accounts.values())

        if group:
            accounts = [acc for acc in accounts if acc.group == group]
        if platform:
            accounts = [acc for acc in accounts if acc.platform == platform]

        return [acc for acc in accounts if acc.is_available()]

    def select_account(
        self,
        strategy: Literal["priority", "round_robin", "random", "load_balance"] = "priority",
        group: str | None = None,
    ) -> Account | None:
        """选择一个账号"""
        available = self.get_available_accounts(group=group)

        if not available:
            taobao_guanghe_logger.warning("⚠️ 没有可用账号")
            return None

        if strategy == "priority":
            return max(available, key=lambda acc: acc.priority)

        elif strategy == "round_robin":
            return min(available, key=lambda acc: acc.current_daily_uploads)

        elif strategy == "random":
            return random.choice(available)

        elif strategy == "load_balance":
            return max(
                available,
                key=lambda acc: acc.priority / (acc.current_daily_uploads + 1)
            )

        return available[0]

    def add_account(self, account: Account):
        """添加账号"""
        self.accounts[account.name] = account
        self.save_config()

    def disable_account(self, name: str):
        """禁用账号"""
        if name in self.accounts:
            self.accounts[name].enabled = False
            self.save_config()

    def enable_account(self, name: str):
        """启用账号"""
        if name in self.accounts:
            self.accounts[name].enabled = True
            self.save_config()
