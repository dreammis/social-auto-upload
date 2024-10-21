import asyncio
from pathlib import Path
from conf import BASE_DIR
from uploader.douyin_uploader.main import douyin_setup
from uploader.ks_uploader.main import ks_setup
from uploader.tencent_uploader.main import weixin_setup
from uploader.tk_uploader.main_chrome import tiktok_setup
from utils.base_social_media import SOCIAL_MEDIA_DOUYIN, SOCIAL_MEDIA_TENCENT, SOCIAL_MEDIA_TIKTOK, SOCIAL_MEDIA_KUAISHOU


async def login(platform, account_name):
    account_file = Path(BASE_DIR / "cookies" / f"{platform}_{account_name}.json")
    account_file.parent.mkdir(exist_ok=True)

    print(f"Logging in with account {account_name} on platform {platform}")
    if platform == SOCIAL_MEDIA_DOUYIN:
        await douyin_setup(str(account_file), handle=True)
    elif platform == SOCIAL_MEDIA_TIKTOK:
        await tiktok_setup(str(account_file), handle=True)
    elif platform == SOCIAL_MEDIA_TENCENT:
        await weixin_setup(str(account_file), handle=True)
    elif platform == SOCIAL_MEDIA_KUAISHOU:
        await ks_setup(str(account_file), handle=True)
    else:
        print("Wrong platform, please check your input")
        exit()

if __name__ == "__main__":
    # Example usage
    asyncio.run(login("douyin", "333"))
