import pyotp


def google_code(secret_key=''):
    # 创建TOTP对象
    totp = pyotp.TOTP(secret_key)
    return totp.now()


def verify_google_code(secret_key, code):
    totp = pyotp.TOTP(secret_key)
    return totp.verify(code)


if __name__ == '__main__':
    print(google_code(secret_key='XZIA4NAHUQJGVUWY'))
