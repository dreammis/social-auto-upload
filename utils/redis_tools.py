import redis


# 连接到Redis服务器，包含密码认证
redis_client = redis.Redis(
    host='121.43.145.233',
    port=31008,
    db=0,
    password='lingyinqvan456'  # 添加密码参数
)


def set_data_with_expiry(key, value, expiry_seconds):
    """
    将数据写入Redis,并设置过期时间

    :param key: 键
    :param value: 值
    :param expiry_seconds: 过期时间(秒)
    :return: 是否成功设置
    """
    return redis_client.setex(key, expiry_seconds, value)


def get_data(key):
    """
    从Redis读取数据

    :param key: 键
    :return: 值,如果键不存在则返回None
    """
    value = redis_client.get(key)
    return value.decode('utf-8') if value else None


def set_douyin_verification_code(phone_number, code):
    """
    存储抖音登录验证码

    :param phone_number: 手机号码
    :param code: 验证码
    :return: 是否成功设置
    """
    key = f"douyin:verification:{phone_number}"
    return set_data_with_expiry(key, code, 60)  # 60秒有效期


def get_douyin_verification_code(phone_number):
    """
    获取抖音登录验证码

    :param phone_number: 手机号码
    :return: 验证码,如果不存在或已过期则返回None
    """
    key = f"douyin:verification:{phone_number}"
    return get_data(key)


# 使用示例
if __name__ == "__main__":
    try:
        # 测试连接
        sss = redis_client.ping()
        print("成功连接到Redis服务器", sss)

        # # 设置验证码
        phone = "18282513893"
        code = "123456"
        # if set_douyin_verification_code(phone, code):
        #     print(f"验证码已设置: {phone} - {code}")

        # 获取验证码
        stored_code = get_douyin_verification_code(phone)
        if stored_code:
            print(f"获取到的验证码: {stored_code}")
        else:
            print("验证码不存在或已过期")
    except redis.exceptions.AuthenticationError:
        print("Redis认证失败，请检查密码是否正确")
    except redis.exceptions.ConnectionError:
        print("无法连接到Redis服务器，请检查网络设置和服务器状态")
    except Exception as e:
        print(f"发生错误: {str(e)}")
