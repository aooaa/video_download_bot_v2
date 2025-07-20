import asyncio

from f2.apps.tiktok.dl import TiktokDownloader
from f2.apps.tiktok.handler import TiktokHandler
from f2.apps.tiktok.utils import DeviceIdManager

# from f2.log.logger import logger

# set logger level to DEBUG
# logger.setLevel("DEBUG")


async def print_device_id():
    # if not device_id, generate one, not every request need to generate device_id
    device_id = await DeviceIdManager.gen_device_id(full_cookie=True)
    # print device_id and fill in the cookie field in kwargs, fill device_id field in conf.yaml
    print(device_id)


async def main():

    kwargs = {
        "headers": {
            # UA is very important, you should keep it up to date from conf.yaml
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Referer": "https://www.tiktok.com/",
        },
        "timeout": 1000,
        "interval": "all",
        # Here you should fill in the cookie you got from the web page, or the cookie returned by binding with device_id
        "cookie": "",
    }

    video = await TiktokHandler(kwargs).fetch_one_video("7421889378101808404")
    await TiktokDownloader(kwargs).create_download_tasks(
        # You should full kwargs in here
        kwargs,
        aweme_datas=video._to_dict(),
        user_path=r"C:\Users\herry\Desktop",
    )


if __name__ == "__main__":
    # first step, you should run print_device_id to set up
    # asyncio.run(print_device_id())
    # second step, after you set up device_id, you can run main
    asyncio.run(main())