import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
from hashlib import sha256


class AESEncryptor:
    def __init__(self, key):
        """
        初始化加密器
        :param key: 可以是字符串或字节，自动处理为32字节密钥
        """
        # 将密钥转换为32字节的AES-256密钥
        if isinstance(key, str):
            key = key.encode('utf-8')
        self.key = self._normalize_key(key)

    def _normalize_key(self, key):
        """处理密钥长度不足或过长的情况"""
        # 如果密钥长度不足，使用SHA-256哈希扩展
        if len(key) < 32:
            return sha256(key).digest()
        # 如果密钥过长，截取前32字节
        return key[:32]

    def encrypt(self, plain_text):
        """
        加密字符串
        :param plain_text: 要加密的文本
        :return: Base64编码的加密字符串
        """
        # 将字符串编码为字节
        plain_bytes = plain_text.encode('utf-8')

        # 生成随机初始化向量(IV)
        iv = get_random_bytes(AES.block_size)

        # 创建AES加密器(CBC模式)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)

        # 对数据进行PKCS#7填充并加密
        ciphertext = cipher.encrypt(pad(plain_bytes, AES.block_size))

        # 组合IV和密文，并Base64编码
        encrypted_data = iv + ciphertext
        return base64.b64encode(encrypted_data).decode('utf-8')

    def decrypt(self, encrypted_text):
        """
        解密字符串
        :param encrypted_text: Base64编码的加密字符串
        :return: 解密后的原始字符串
        """
        # Base64解码
        encrypted_data = base64.b64decode(encrypted_text)

        # 分离IV和密文
        iv = encrypted_data[:AES.block_size]
        ciphertext = encrypted_data[AES.block_size:]

        # 创建AES解密器
        cipher = AES.new(self.key, AES.MODE_CBC, iv)

        # 解密并移除填充
        decrypted_bytes = unpad(cipher.decrypt(ciphertext), AES.block_size)

        # 将字节解码为字符串
        return decrypted_bytes.decode('utf-8')


# 示例用法
if __name__ == "__main__":
    # 示例密钥（可以是任意长度）
    user_key = "MySecretKey123"  # 注意：实际应用中应从安全来源获取

    # 创建加密器
    encryptor = AESEncryptor(user_key)

    # 原始消息
    original_message = "这是一条需要加密的秘密消息！🔐"

    # A端加密
    encrypted = encryptor.encrypt(original_message)
    print(f"加密结果: {encrypted}")

    # B端解密
    decrypted = encryptor.decrypt(encrypted)
    print(f"解密结果: {decrypted}")

    # 验证结果
    print(f"原始与解密是否一致: {original_message == decrypted}")
