# === 配置 ===
SECRET_KEY = "JWT-TOKEN-SECRET-KEY"  # 🔐 请替换成自己的密钥
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # 30分钟有效期
TOKEN_REFRESH_THRESHOLD_MINUTES = 10  # Token刷新阈值（分钟），当token剩余时间少于此值时才刷新
MAX_DEVICES_PER_USER = 5  # 设备数量限制，最多允许 5 台设备登录系统