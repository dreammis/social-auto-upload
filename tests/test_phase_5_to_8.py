#!/usr/bin/env python3
"""测试 Phase 5-8 实现的所有模块"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def test_phase_5_account_manager():
    """测试账号管理"""
    print("\n" + "=" * 60)
    print("Phase 5: 测试账号管理")
    print("=" * 60)

    from uploader.account_manager import AccountManager, Account

    # 创建管理器
    manager = AccountManager("accounts.yaml")

    # 添加测试账号
    if not manager.accounts:
        account = Account(
            name="test_account",
            display_name="测试账号",
            platform="taobao_guanghe",
            cookie_file="cookies/taobao_guanghe_uploader/test_account.json",
            enabled=True,
            group="test",
            priority=5,
        )
        manager.add_account(account)
        print("✅ 添加测试账号")

    # 列出所有账号
    print(f"\n📋 账号列表 (共 {len(manager.accounts)} 个):")
    for name, acc in manager.accounts.items():
        status = "✅" if acc.is_available() else "❌"
        print(f"  {status} {acc.display_name} ({name}) - {acc.status}")

    # 选择账号
    account = manager.select_account(strategy="priority")
    if account:
        print(f"\n🎯 选中账号: {account.display_name}")

    print("\n✅ Phase 5 测试完成")


async def test_phase_6_cookie_manager():
    """测试 Cookie 管理"""
    print("\n" + "=" * 60)
    print("Phase 6: 测试 Cookie 管理")
    print("=" * 60)

    from uploader.cookie_manager import CookieManager

    # 创建管理器
    cookie_mgr = CookieManager()

    # 测试 Cookie 文件
    cookie_file = Path("cookies/taobao_guanghe_uploader/test_account.json")

    if cookie_file.exists():
        # 获取 Cookie 信息
        info = cookie_mgr.get_cookie_info(cookie_file)
        print(f"\n📄 Cookie 信息:")
        print(f"  文件: {info['path']}")
        print(f"  大小: {info.get('size', 0)} bytes")
        print(f"  Cookie 数量: {info.get('cookie_count', 0)}")

        # 验证 Cookie
        print(f"\n🔍 验证 Cookie（仅格式检查）...")
        is_valid, message = await cookie_mgr.validate_cookie(cookie_file, skip_online_check=True)
        print(f"  结果: {message}")

        # 备份 Cookie
        if is_valid:
            backup = cookie_mgr.backup_cookie(cookie_file)
            print(f"  备份: {backup}")
    else:
        print(f"⚠️  Cookie 文件不存在: {cookie_file}")

    print("\n✅ Phase 6 测试完成")


async def test_phase_7_material_manager():
    """测试素材管理"""
    print("\n" + "=" * 60)
    print("Phase 7: 测试素材管理")
    print("=" * 60)

    from materials import MaterialManager, MaterialType

    # 创建管理器
    material_mgr = MaterialManager()

    print(f"\n📦 素材库统计:")
    print(f"  总数: {len(material_mgr.materials)}")

    # 按类型统计
    videos = material_mgr.find_materials(material_type=MaterialType.VIDEO)
    covers = material_mgr.find_materials(material_type=MaterialType.COVER)
    print(f"  视频: {len(videos)}")
    print(f"  封面: {len(covers)}")

    # 如果有素材，显示详情
    if material_mgr.materials:
        print(f"\n📋 素材列表:")
        for material_id, material in list(material_mgr.materials.items())[:5]:
            print(f"  - {material.file_name}")
            print(f"    类型: {material.type.value}")
            print(f"    标题: {material.metadata.title}")

    print("\n✅ Phase 7 测试完成")


async def test_phase_8_ai_manager():
    """测试 AI 模块"""
    print("\n" + "=" * 60)
    print("Phase 8: 测试 AI 模块")
    print("=" * 60)

    from ai import AIManager

    # 创建管理器
    ai_config = Path("ai_config.yaml")

    if not ai_config.exists():
        print(f"⚠️  AI 配置文件不存在: {ai_config}")
        print("   请复制 ai_config.example.yaml 并配置 API Key")
        print("\n✅ Phase 8 测试跳过")
        return

    ai_mgr = AIManager(ai_config)

    print(f"\n🤖 已配置的 AI 提供商:")
    for name in ai_mgr.providers.keys():
        print(f"  - {name}")

    if not ai_mgr.providers:
        print("  ⚠️  没有可用的 AI 提供商")
        print("\n✅ Phase 8 测试跳过")
        return

    # 测试生成（需要有效的 API Key）
    try:
        print(f"\n📝 测试生成标题...")
        title = await ai_mgr.generate_title(
            filename="测试视频.mp4",
            description="这是一个测试视频",
            keywords="测试,演示"
        )
        print(f"  生成的标题: {title}")

        print(f"\n📝 测试生成描述...")
        description = await ai_mgr.generate_description(
            title=title,
            keywords="测试,演示"
        )
        print(f"  生成的描述: {description[:50]}...")

        print(f"\n🏷️  测试生成标签...")
        tags = await ai_mgr.generate_tags(
            title=title,
            description=description
        )
        print(f"  生成的标签: {', '.join(tags)}")

    except Exception as e:
        print(f"  ⚠️  AI 生成失败: {str(e)}")
        print("  请检查 API Key 是否正确配置")

    print("\n✅ Phase 8 测试完成")


async def main():
    """主测试函数"""
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 10 + "Phase 5-8 模块测试" + " " * 30 + "║")
    print("╚" + "═" * 58 + "╝")

    try:
        await test_phase_5_account_manager()
        await test_phase_6_cookie_manager()
        await test_phase_7_material_manager()
        await test_phase_8_ai_manager()

        print("\n" + "=" * 60)
        print("🎉 所有测试完成！")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户取消测试")
        sys.exit(1)
