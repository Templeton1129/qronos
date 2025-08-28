"""
数据库模型定义模块

该模块定义了量化交易框架管理系统的所有数据库模型和配置。
使用SQLAlchemy ORM框架，支持SQLite数据库。

主要功能：
1. 数据库连接和会话管理
2. 用户认证信息存储
3. 框架状态跟踪
4. 框架配置管理

数据库表结构：
- user: 用户认证和凭据信息
- framework_status: 框架下载和运行状态
- framework_config: 框架配置参数

"""

from sqlalchemy import create_engine, Column, Integer, String, DateTime, text
from sqlalchemy.orm import declarative_base, sessionmaker
from utils.constant import DB_PATH
from utils.log_kit import get_logger

# 初始化日志记录器
logger = get_logger()

# 创建数据库引擎
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, future=True)

# 创建会话工厂
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

# 创建声明式基类
Base = declarative_base()


class User(Base):
    """
    用户表模型
    
    存储用户的认证信息和API凭据。
    支持Google Authenticator 2FA认证和XBX API集成。
    
    :ivar id: 用户主键ID
    :vartype id: int
    :ivar uuid: XBX系统用户UUID，用于API调用
    :vartype uuid: str
    :ivar apikey: XBX系统API密钥，用于获取访问token
    :vartype apikey: str
    :ivar xbx_token: XBX系统访问token，用于API认证
    :vartype xbx_token: str
    :ivar token: 本系统JWT token，用于Web认证
    :vartype token: str
    :ivar secret: Google Authenticator密钥，用于2FA验证
    :vartype secret: str
    
    Note:
        - uuid和apikey来自XBX系统，用于第三方API调用
        - xbx_token是临时访问令牌，会定期刷新
        - token是本系统的JWT令牌，用于Web界面认证
        - secret是Google Authenticator的密钥，用于双因子认证
    """
    __tablename__ = 'user'
    
    id = Column(Integer, primary_key=True, index=True, comment="用户主键ID")
    uuid = Column(String(64), unique=True, comment="XBX系统用户UUID")
    apikey = Column(String(128), comment="XBX系统API密钥")
    xbx_token = Column(String(256), comment="XBX系统访问token")
    xbx_token_expiry_time = Column(String(32), comment="XBX系统访问token有效期")
    token = Column(String(256), comment="本系统JWT token")
    secret = Column(String(64), unique=True, comment="Google Authenticator密钥")


class Device(Base):
    """
    设备表模型
    
    存储用户设备的详细信息和认证状态。
    支持多设备登录系统，每个设备拥有独立的token。
    
    :ivar id: 设备唯一标识符（SHA256哈希）
    :vartype id: str
    :ivar user_id: 关联的用户ID
    :vartype user_id: int
    :ivar device_type: 设备类型（pc/mobile/tablet）
    :vartype device_type: str
    :ivar browser_info: 浏览器信息
    :vartype browser_info: str
    :ivar ip_address: IP地址
    :vartype ip_address: str
    :ivar last_active_time: 最后活跃时间
    :vartype last_active_time: DateTime
    :ivar created_time: 设备首次注册时间
    :vartype created_time: DateTime
    :ivar token: 设备专属JWT token
    :vartype token: str
    :ivar is_active: 设备状态（1=活跃，0=已踢下线）
    :vartype is_active: bool
    
    Note:
        - id使用SHA256哈希确保设备唯一性
        - user_id手动维护关联关系，避免外键约束
        - is_active用于实现踢设备下线功能
    """
    __tablename__ = 'device'
    
    id = Column(String(64), primary_key=True, index=True, comment="设备唯一标识符")
    user_id = Column(Integer, comment="关联的用户ID")
    device_type = Column(String(20), comment="设备类型：pc/mobile/tablet")
    browser_info = Column(String(200), comment="浏览器信息")
    ip_address = Column(String(45), comment="IP地址")
    last_active_time = Column(DateTime, comment="最后活跃时间")
    created_time = Column(DateTime, comment="设备首次注册时间")
    token = Column(String(256), comment="设备专属JWT token")
    is_active = Column(Integer, default=1, comment="设备状态：1=活跃，0=已踢下线")


class FrameworkStatus(Base):
    """
    框架状态表模型
    
    跟踪所有框架的下载状态、运行状态和基本信息。
    用于监控框架的生命周期管理。
    
    :ivar id: 状态记录主键ID
    :vartype id: int
    :ivar framework_id: 框架唯一标识符
    :vartype framework_id: str
    :ivar framework_name: 框架显示名称
    :vartype framework_name: str
    :ivar status: 框架当前状态（下载中/已完成/失败等）
    :vartype status: str
    :ivar type: 框架类型（数据中心/策略框架等）
    :vartype type: str
    :ivar time: 框架版本时间戳
    :vartype time: str
    :ivar path: 框架在本地磁盘的存储路径
    :vartype path: str
    
    状态枚举值：
        - not_downloaded: 未下载
        - downloading: 下载中
        - finished: 下载完成
        - failed: 下载失败
        
    框架类型：
        - data_center: 数据中心框架
        - strategy: 策略框架
    """
    __tablename__ = 'framework_status'
    
    id = Column(Integer, primary_key=True, index=True, comment="状态记录主键ID")
    framework_id = Column(String(64), nullable=False, comment="框架唯一标识符")
    framework_name = Column(String(64), nullable=False, comment="框架显示名称")
    status = Column(String(32), nullable=False, comment="框架当前状态")
    type = Column(String(32), nullable=False, comment="框架类型")
    time = Column(String(32), nullable=False, comment="框架版本时间戳")
    path = Column(String(256), comment="框架本地存储路径")


def init_db():
    """
    初始化数据库表结构
    
    创建所有定义的数据库表。如果表已存在则跳过创建。
    该函数通常在应用启动时调用一次。
    
    Process:
        1. 检查数据库连接
        2. 根据模型定义创建表结构
        3. 执行数据库迁移（添加缺失的列）
        4. 记录初始化结果
        
    Note:
        - 使用create_all方法，只创建不存在的表
        - 不会删除或修改已存在的表结构
        - 如需修改表结构，建议使用数据库迁移工具
    """
    try:
        logger.info("开始初始化数据库表结构...")
        Base.metadata.create_all(bind=engine)
        logger.info("数据库表结构初始化完成")
        
        # 执行数据库迁移
        _migrate_database()
        
        # 记录创建的表信息
        table_names = [table.name for table in Base.metadata.tables.values()]
        logger.info(f"已创建/验证的数据库表: {', '.join(table_names)}")
        
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise


def _migrate_database():
    """
    数据库迁移函数
    
    检查并添加缺失的列，确保数据库表结构与模型定义一致。
    """
    try:
        logger.info("开始检查数据库迁移...")
        
        # 检查user表是否需要迁移
        _migrate_user_table()
        
        # 检查device表是否需要创建
        _migrate_device_table()
        
        logger.info("数据库迁移检查完成")
        
    except Exception as e:
        logger.error(f"数据库迁移失败: {e}")
        raise


def _migrate_user_table():
    """
    迁移user表结构
    
    检查user表是否缺少xbx_token_expiry_time列，如果缺少则添加。
    """
    try:
        with engine.connect() as conn:
            # 检查xbx_token_expiry_time列是否存在
            result = conn.execute(text("PRAGMA table_info(user)"))
            columns = [row[1] for row in result.fetchall()]
            
            if 'xbx_token_expiry_time' not in columns:
                logger.info("检测到user表缺少xbx_token_expiry_time列，开始添加...")
                
                # 添加xbx_token_expiry_time列
                conn.execute(text("ALTER TABLE user ADD COLUMN xbx_token_expiry_time VARCHAR(32)"))
                conn.commit()
                
                logger.info("成功添加xbx_token_expiry_time列到user表")
            else:
                logger.info("user表结构已是最新，无需迁移")
                
    except Exception as e:
        logger.error(f"迁移user表失败: {e}")
        raise


def _migrate_device_table():
    """
    迁移device表结构
    
    检查device表是否存在，如果不存在则创建新的device表。
    """
    try:
        with engine.connect() as conn:
            # 检查device表是否存在
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='device'"))
            table_exists = result.fetchone() is not None
            
            if not table_exists:
                logger.info("检测到device表不存在，开始创建...")
                
                # 创建device表
                create_device_table_sql = """
                CREATE TABLE device (
                    id VARCHAR(64) PRIMARY KEY,
                    user_id INTEGER,
                    device_type VARCHAR(20),
                    browser_info VARCHAR(200),
                    ip_address VARCHAR(45),
                    last_active_time DATETIME,
                    created_time DATETIME,
                    token VARCHAR(256),
                    is_active INTEGER DEFAULT 1
                )
                """
                conn.execute(text(create_device_table_sql))
                conn.commit()
                
                logger.info("成功创建device表")
            else:
                logger.info("device表已存在，无需创建")
                
    except Exception as e:
        logger.error(f"迁移device表失败: {e}")
        raise
