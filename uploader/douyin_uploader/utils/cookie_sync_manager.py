"""
Cookie同步管理器
负责管理user_data_dir和cookie文件之间的同步
"""

from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright, Browser, BrowserContext
import json

# 使用绝对导入
from utils.log import douyin_logger

class CookieSyncManager:
    """Cookie同步管理器类"""
    
    def __init__(self):
        """初始化同步管理器"""
        self.last_sync_time: Dict[str, datetime] = {}  # 记录每个账号最后同步时间
        self._sync_interval = 300  # 同步间隔(秒)
        
    async def sync_from_profile_to_file(
        self, 
        user_data_dir: Path, 
        cookie_file: Path,
        account_id: str
    ) -> bool:
        """
        从user_data_dir同步到cookie文件
        Args:
            user_data_dir: 用户数据目录
            cookie_file: cookie文件路径
            account_id: 账号ID
        Returns:
            bool: 是否同步成功
        """
        try:
            # 获取当前时间
            current_time = datetime.now()
            
            # 检查是否需要同步(5分钟内不重复同步)
            if account_id in self.last_sync_time:
                time_diff = (current_time - self.last_sync_time[account_id]).total_seconds()
                if time_diff < self._sync_interval:
                    douyin_logger.debug(f"账号 {account_id} 最近已同步,跳过")
                    return True
                    
            # 确保目录存在
            cookie_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 如果cookie文件存在且不为空，跳过同步
            if cookie_file.exists():
                try:
                    with open(cookie_file, 'r', encoding='utf-8') as f:
                        state = json.load(f)
                        if state.get('cookies') or state.get('origins'):
                            douyin_logger.info(f"账号 {account_id} cookie文件有效，跳过同步")
                            return True
                except Exception as e:
                    douyin_logger.warning(f"读取cookie文件失败: {str(e)}")
            
            # 创建临时上下文并同步
            async with async_playwright() as playwright:
                # 使用launch_persistent_context读取现有数据
                context = await playwright.chromium.launch_persistent_context(
                    user_data_dir=str(user_data_dir),
                    headless=True
                )
                try:
                    # 获取当前状态
                    state = await context.storage_state()
                    if state.get('cookies') or state.get('origins'):
                        # 只有当有有效的cookie时才保存
                        await context.storage_state(path=str(cookie_file))
                        self.last_sync_time[account_id] = current_time
                        douyin_logger.info(f"账号 {account_id} 同步到文件成功")
                        return True
                    else:
                        douyin_logger.warning(f"账号 {account_id} 没有有效的cookie，跳过同步")
                        return False
                finally:
                    await context.close()
                    
        except Exception as e:
            douyin_logger.error(f"同步cookie到文件失败 [{account_id}]: {str(e)}")
            return False
            
    async def restore_from_file_to_profile(
        self, 
        cookie_file: Path,
        user_data_dir: Path,
        account_id: str
    ) -> bool:
        """
        从cookie文件恢复到user_data_dir(仅在必要时使用)
        Args:
            cookie_file: cookie文件路径
            user_data_dir: 用户数据目录
            account_id: 账号ID
        Returns:
            bool: 是否恢复成功
        """
        try:
            # 检查cookie文件是否存在
            if not cookie_file.exists():
                douyin_logger.error(f"Cookie文件不存在: {cookie_file}")
                return False
                
            # 确保目录存在
            user_data_dir.mkdir(parents=True, exist_ok=True)
            
            # 创建临时上下文并恢复
            async with async_playwright() as playwright:
                # 先创建临时上下文加载cookie文件
                browser = await playwright.chromium.launch(headless=True)
                context = await browser.new_context()
                try:
                    # 加载cookie文件
                    await context.storage_state(path=str(cookie_file))
                    
                    # 保存到user_data_dir
                    persistent_context = await playwright.chromium.launch_persistent_context(
                        user_data_dir=str(user_data_dir),
                        headless=True
                    )
                    try:
                        # 获取cookie并应用到持久化上下文
                        state = await context.storage_state()
                        await persistent_context.add_cookies(state['cookies'])
                        douyin_logger.info(f"账号 {account_id} 从文件恢复成功")
                        return True
                    finally:
                        await persistent_context.close()
                finally:
                    await context.close()
                    await browser.close()
                    
        except Exception as e:
            douyin_logger.error(f"从文件恢复cookie失败 [{account_id}]: {str(e)}")
            return False
            
    async def ensure_consistency(
        self,
        user_data_dir: Path,
        cookie_file: Path,
        account_id: str
    ) -> bool:
        """
        确保两种存储方式的数据一致性
        Args:
            user_data_dir: 用户数据目录
            cookie_file: cookie文件路径
            account_id: 账号ID
        Returns:
            bool: 是否一致
        """
        try:
            # 如果cookie文件不存在,直接同步
            if not cookie_file.exists():
                return await self.sync_from_profile_to_file(
                    user_data_dir,
                    cookie_file,
                    account_id
                )
                
            # 获取两边的storage state进行比较
            async with async_playwright() as playwright:
                # 获取profile中的状态
                profile_context = await playwright.chromium.launch_persistent_context(
                    user_data_dir=str(user_data_dir),
                    headless=True
                )
                try:
                    profile_state = await profile_context.storage_state()
                finally:
                    await profile_context.close()
                    
                # 获取文件中的状态
                browser = await playwright.chromium.launch(headless=True)
                context = await browser.new_context()
                try:
                    await context.storage_state(path=str(cookie_file))
                    file_state = await context.storage_state()
                finally:
                    await context.close()
                    await browser.close()
                    
            # 比较cookies
            if self._states_are_different(profile_state, file_state):
                douyin_logger.info(f"账号 {account_id} 数据不一致,执行同步")
                return await self.sync_from_profile_to_file(
                    user_data_dir,
                    cookie_file,
                    account_id
                )
                
            douyin_logger.debug(f"账号 {account_id} 数据一致")
            return True
            
        except Exception as e:
            douyin_logger.error(f"检查一致性失败 [{account_id}]: {str(e)}")
            return False
            
    def _states_are_different(self, state1: Dict, state2: Dict) -> bool:
        """
        比较两个storage state是否有实质性差异
        
        比较规则:
        1. 必需cookie: sessionid, passport_csrf_token 等登录相关cookie
        2. 值比较: 检查cookie的值是否相同
        3. 过期时间: 检查cookie是否已过期或即将过期
        4. 域名范围: .douyin.com 等关键域名的cookie
        """
        try:
            cookies1 = {c['name']: c for c in state1['cookies']}
            cookies2 = {c['name']: c for c in state2['cookies']}
            
            # 关键cookie列表
            critical_cookies = {
                'sessionid',
                'passport_csrf_token',
                'ttwid',
                'passport_auth_status',
                'sid_guard',
                'uid_tt',
                'sid_tt',
                'd_ticket'
            }
            
            # 关键域名列表
            critical_domains = {
                '.douyin.com',
                'creator.douyin.com',
                '.bytedance.com'
            }
            
            # 1. 检查关键cookie是否都存在
            for name in critical_cookies:
                if name not in cookies1 or name not in cookies2:
                    douyin_logger.debug(f"关键cookie {name} 不一致")
                    return True
                    
                cookie1 = cookies1[name]
                cookie2 = cookies2[name]
                
                # 2. 检查值是否相同
                if cookie1['value'] != cookie2['value']:
                    douyin_logger.debug(f"Cookie {name} 值不一致")
                    return True
                    
                # 3. 检查是否过期
                current_time = datetime.now().timestamp()
                # 如果任一cookie已过期或将在1小时内过期
                if ('expires' in cookie1 and cookie1['expires'] < current_time + 3600) or \
                   ('expires' in cookie2 and cookie2['expires'] < current_time + 3600):
                    douyin_logger.debug(f"Cookie {name} 已过期或即将过期")
                    return True
            
            # 4. 检查关键域名的cookie
            for domain in critical_domains:
                domain_cookies1 = {c['name']: c for c in state1['cookies'] if c['domain'] == domain}
                domain_cookies2 = {c['name']: c for c in state2['cookies'] if c['domain'] == domain}
                
                if len(domain_cookies1) != len(domain_cookies2):
                    douyin_logger.debug(f"域名 {domain} 的cookie数量不一致")
                    return True
                    
                # 比较该域名下所有cookie的值
                for name, cookie1 in domain_cookies1.items():
                    if name not in domain_cookies2:
                        douyin_logger.debug(f"域名 {domain} 下的cookie {name} 不存在")
                        return True
                    cookie2 = domain_cookies2[name]
                    if cookie1['value'] != cookie2['value']:
                        douyin_logger.debug(f"域名 {domain} 下的cookie {name} 值不一致")
                        return True
            
            return False
            
        except Exception as e:
            douyin_logger.error(f"比较状态失败: {str(e)}")
            return True  # 出错时认为不一致,触发同步 