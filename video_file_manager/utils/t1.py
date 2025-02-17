import asyncio
import time
from image_text_detector import detector

# 待处理的图片URL列表
image_urls = [
    "https://finder.video.qq.com/251/20304/stodownload?encfilekey=rjD5jyTuFrIpZ2ibE8T7Ym3K77SEULgkia1FnbTHE3r1VZic5icWRSrQsJrqLF51L0yF0w6GQLnbzws0Kksz7GeRicqlMKW6x360siazAqJ3UBmich8IiaMpISydsQ&token=o3K9JoTic9IjjCEWI9eqVYutCnic9Vicyv6EOjgqokibHH8nJeMVgpPLsHrPg2gcALYCLvxdNKEicjqTlPkeBnl4RcJCtj2QCiahexwsBJ3SnNplemTcUlZIUC7uMicGQfutkibh4Jf6UxNEnot8AR9TCXQrgjOnicul3Qib7KeicYtVqyYa59MJyNXkkzKJw&idx=1&hy=SZ&m=&scene=2&uzid=2",
    "https://finder.video.qq.com/251/20304/stodownload?encfilekey=rjD5jyTuFrIpZ2ibE8T7Ym3K77SEULgkiaTYSYnPjAH4KPOXjbdQc6AsNuUllx8XlM3uuNvrJLsEuASXzdx2Tmicgo3ibNazHThgNHVwjeyRPU4lEDR5YAZVXg&token=Cvvj5Ix3eexZiajDdmtxmMH0leeRT01p1MGfQAsibwhlbOwVzzwxyrntImicjSYoHxTyZk5ZqfedumJNXmCia4eIeEje0y5WU9Elk58r0qiaiaZVtX4GsxOEnYeQW5FOfvSyboVpX0pRLL1LPwesibSbvoYGoiaaHr4sfU09mW4exjMibAkNY0TO8WgzS9kOgibDRQich0r&idx=1&hy=SZ&m=&scene=2&uzid=2",
    "https://finder.video.qq.com/251/20304/stodownload?encfilekey=rjD5jyTuFrIpZ2ibE8T7Ym3K77SEULgkiaoCo8lL58OmloAN31zWRTClrlX0xHLGdZWuPgG5wuM78P4WTECa8VAeSiacE8gyFF9CyyrzgibyvQiawjiaPKp0h7qQ&token=Cvvj5Ix3eexZiajDdmtxmMH0leeRT01p1buiaW9rw9hFqMbHLWJ9M0vCJN4vJuEnFMDjQB8piaYsvedRwI1MkVo2Vv5ibmGvonSib1Wp0PM8icxM9Vqa9YMYUndKBCeJiakern4WYJ3aLt9libib71fZ4QaKtr2o9M3U6nBHxYvgnR98RfSMIykQX9tbIwFxF1ndNmvdh&idx=1&hy=SZ&m=&scene=2&uzid=2"
]

async def process_single_image(url: str, index: int) -> dict:
    """处理单个图片并记录时间"""
    start_time = time.time()
    try:
        text = await detector.detect_text(url)
        end_time = time.time()
        return {
            "index": index,
            "url": url,
            "text": text,
            "error": None,
            "time_taken": end_time - start_time
        }
    except Exception as e:
        end_time = time.time()
        return {
            "index": index,
            "url": url,
            "text": None,
            "error": str(e),
            "time_taken": end_time - start_time
        }

async def main():
    print(f"开始处理 {len(image_urls)} 张图片...")
    total_start_time = time.time()
    
    # 创建任务列表
    tasks = [process_single_image(url, i) for i, url in enumerate(image_urls, 1)]
    
    # 并发执行所有任务
    results = await asyncio.gather(*tasks)
    
    # 计算总耗时
    total_time = time.time() - total_start_time
    
    # 输出详细结果
    print("\n处理结果:")
    print("-" * 50)
    
    success_count = 0
    error_count = 0
    
    for result in sorted(results, key=lambda x: x["index"]):
        print(f"\n图片 {result['index']}:")
        if result["error"]:
            print(f"  状态: 失败")
            print(f"  错误: {result['error']}")
            error_count += 1
        else:
            print(f"  状态: 成功")
            print(f"  识别结果: {result['text']}")
            success_count += 1
        print(f"  处理时间: {result['time_taken']:.2f}秒")
    
    # 输出统计信息
    print("\n统计信息:")
    print("-" * 50)
    print(f"总处理时间: {total_time:.2f}秒")
    print(f"平均每张耗时: {total_time/len(image_urls):.2f}秒")
    print(f"成功数量: {success_count}")
    print(f"失败数量: {error_count}")
    print(f"成功率: {(success_count/len(image_urls))*100:.1f}%")

# 运行示例
asyncio.run(main())