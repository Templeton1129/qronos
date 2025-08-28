"""
数据库操作模块

该模块提供量化交易框架管理系统的所有数据库操作功能。
封装了用户管理、框架状态管理、配置管理等核心数据库操作。

主要功能：
1. 用户认证信息管理
   - Google Secret Key绑定和验证
   - JWT Token管理
   - XBX API凭据管理

2. 框架状态管理
   - 框架下载状态跟踪
   - 框架路径管理
   - 状态查询和更新

3. 框架配置管理
   - 配置参数持久化
   - 配置版本管理
   - 配置查询和更新

技术特性：
- 使用SQLAlchemy ORM进行数据库操作
- 自动会话管理和事务处理
- 完善的错误处理和日志记录
- 支持数据模型转换

"""
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from db.db import SessionLocal, FrameworkStatus, User
from model.enum_kit import StatusEnum
from utils.log_kit import get_logger

# 初始化日志记录器
logger = get_logger()


def orm_to_dict(obj) -> Optional[Dict[str, Any]]:
    """
    将ORM对象转换为字典格式
    
    将SQLAlchemy ORM模型对象转换为普通字典，便于JSON序列化和API返回。
    
    :param obj: SQLAlchemy ORM模型对象
    :type obj: Base
    :return: 转换后的字典，如果输入为None则返回None
    :rtype: Optional[Dict[str, Any]]
    
    Example:
        user = db.query(User).first()
        user_dict = orm_to_dict(user)
        # 返回: {"id": 1, "uuid": "xxx", "apikey": "xxx", ...}
    """
    if obj is None:
        logger.info("ORM对象为空，返回None")
        return None
    
    try:
        result = {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
        return result
    except Exception as e:
        logger.error(f"ORM对象转换失败: {e}")
        return None


def save_google_secret(secret_key: Optional[str], token: str) -> bool:
    """
    保存Google Secret Key和认证Token
    
    处理用户首次绑定Google Authenticator或后续登录的token更新。
    支持首次绑定验证和重复绑定检测。
    
    :param secret_key: Google Authenticator密钥，首次绑定时必传
    :type secret_key: Optional[str]
    :param token: JWT认证token
    :type token: str
    :return: 操作成功返回True，失败返回False
    :rtype: bool
    
    Process:
        1. 如果提供secret_key，检查是否为首次绑定
        2. 首次绑定：创建新用户记录
        3. 重复绑定：返回失败
        4. 无secret_key：更新现有用户的token
        
    Note:
        - secret_key存在时为首次绑定流程
        - secret_key为空时为登录token更新流程
        - 防止重复绑定同一个Google Secret Key
    """
    logger.info(f"保存Google Secret，是否首次绑定: {bool(secret_key)}")
    
    success = True
    try:
        with SessionLocal() as db:
            if secret_key:
                # 首次绑定流程：检查secret_key是否已存在
                logger.info(f"检查Google Secret是否已存在")
                existing_user = db.query(User).filter_by(secret=secret_key).first()
                
                if existing_user is None:
                    # 创建新用户记录
                    new_user = User(secret=secret_key, token=token)
                    db.add(new_user)
                    logger.info("创建新用户记录，Google Secret绑定成功")
                else:
                    # Secret Key已存在，拒绝重复绑定
                    success = False
                    logger.warning("Google Secret已存在，拒绝重复绑定")
            else:
                # 登录token更新流程：更新现有用户的token
                logger.info("更新现有用户的认证token")
                user = db.query(User).first()
                
                if user is None:
                    success = False
                    logger.error("用户不存在，无法更新token")
                else:
                    user.token = token
                    logger.info("用户认证token更新成功")
            
            # 提交事务
            db.commit()
            logger.info("数据库事务提交成功")
            
    except Exception as e:
        logger.error(f"保存Google Secret失败: {e}")
        success = False
    
    return success


def get_user() -> Optional[User]:
    """
    获取用户信息
    
    从数据库中获取第一个（也是唯一的）用户记录。
    系统设计为单用户模式。
    
    :return: 用户对象，如果不存在则返回None
    :rtype: Optional[User]
    
    Note:
        - 系统采用单用户设计，只返回第一个用户记录
        - 返回完整的User ORM对象，包含所有字段
        - 用于用户认证和凭据获取
    """
    try:
        with SessionLocal() as db:
            user = db.query(User).first()
            if user:
                logger.info(f"成功获取用户信息，UUID: {user.uuid}")
            else:
                logger.info("用户不存在")
            return user
    except Exception as e:
        logger.error(f"获取用户信息失败: {e}")
        return None


def update_user_token(token: str) -> bool:
    """
    更新用户JWT认证Token
    
    更新用户的Web认证token，用于会话管理和token刷新。
    
    :param token: 新的JWT token
    :type token: str
    :return: 更新成功返回True，失败返回False
    :rtype: bool
    
    Note:
        - 仅更新本系统的JWT token
        - 不影响XBX系统的访问token
        - 用于token自动刷新机制
    """
    logger.info("更新用户JWT token")
    
    try:
        with SessionLocal() as db:
            user = db.query(User).first()
            if user:
                user.token = token
                db.commit()
                logger.info("用户JWT token更新成功")
                return True
            else:
                logger.error("用户不存在，无法更新token")
                return False
    except Exception as e:
        logger.error(f"更新用户token失败: {e}")
        return False


def update_user_xbx_token(token: str) -> bool:
    """
    更新用户XBX系统访问Token
    
    更新用户的XBX API访问token，用于第三方API调用认证。
    
    :param token: XBX系统访问token
    :type token: str
    :return: 更新成功返回True，失败返回False
    :rtype: bool
    
    Note:
        - 专门用于XBX第三方API的访问认证
        - token会定期过期，需要重新获取
        - 与本系统JWT token分开管理
    """
    logger.info("更新用户XBX token")
    
    try:
        with SessionLocal() as db:
            user = db.query(User).first()
            if user:
                user.xbx_token = token
                user.xbx_token_expiry_time = (
                        datetime.now().replace(second=0, microsecond=0)
                        + timedelta(hours=7, minutes=random.randint(0,59))
                )
                db.commit()
                logger.info("用户XBX token更新成功")
                return True
            else:
                logger.error("用户不存在，无法更新XBX token")
                return False
    except Exception as e:
        logger.error(f"更新用户XBX token失败: {e}")
        return False


def save_user_credentials(uuid: str, apikey: str) -> bool:
    """
    保存用户XBX系统凭据
    
    保存用户的XBX系统UUID和API密钥，用于后续的API调用认证。
    
    :param uuid: XBX系统用户UUID
    :type uuid: str
    :param apikey: XBX系统API密钥
    :type apikey: str
    :return: 保存成功返回True，失败返回False
    :rtype: bool
    
    Process:
        1. 查找现有用户记录
        2. 更新UUID和API密钥
        3. 提交数据库事务
        
    Note:
        - UUID和API密钥来自XBX系统用户信息
        - 用于XBX API的身份认证
        - 需要先有用户记录才能更新凭据
    """
    logger.info(f"保存用户XBX凭据，UUID: {uuid}")
    
    try:
        with SessionLocal() as db:
            user = db.query(User).first()
            if user:
                user.uuid = uuid
                user.apikey = apikey
                db.commit()
                logger.info("用户XBX凭据保存成功")
                return True
            else:
                logger.error("用户不存在，无法保存凭据")
                return False
    except Exception as e:
        logger.error(f"保存用户凭据失败: {e}")
        return False


def del_user_token() -> bool:
    """
    清除用户认证Token
    
    清空用户的JWT token，用于用户登出操作。
    
    :return: 清除成功返回True，失败返回False
    :rtype: bool
    
    Note:
        - 仅清除本系统的JWT token
        - 不影响XBX系统的访问token
        - 用于用户主动登出
    """
    logger.info("清除用户认证token")
    
    try:
        with SessionLocal() as db:
            user = db.query(User).first()
            if user:
                user.token = ""
                db.commit()
                logger.info("用户认证token已清除")
                return True
            else:
                logger.warning("用户不存在，无需清除token")
                return True  # 用户不存在也算成功
    except Exception as e:
        logger.error(f"清除用户token失败: {e}")
        return False


def save_framework_status(framework_id: str, name: str, status: str, type_: str, time: str) -> bool:
    """
    保存框架状态信息
    
    保存或更新框架的状态信息，用于跟踪框架的下载和运行状态。
    
    :param framework_id: 框架唯一标识符
    :type framework_id: str
    :param name: 框架显示名称
    :type name: str
    :param status: 框架状态（downloading/finished/failed等）
    :type status: str
    :param type_: 框架类型（data_center/strategy等）
    :type type_: str
    :param time: 框架版本时间戳
    :type time: str
    :return: 保存成功返回True，失败返回False
    :rtype: bool
    
    Process:
        1. 查找是否存在相同framework_id的状态记录
        2. 存在则更新状态，不存在则创建新记录
        3. 提交数据库事务
        
    Note:
        - 使用framework_id作为唯一标识
        - 状态更新时只更新status字段
        - 新建记录时保存所有字段信息
    """
    logger.info(f"保存框架状态，框架ID: {framework_id}, 状态: {status}")
    
    try:
        with SessionLocal() as db:
            # 查找现有状态记录
            framework_status = db.query(FrameworkStatus).filter_by(framework_id=framework_id).first()
            
            if framework_status:
                # 更新现有状态
                old_status = framework_status.status
                framework_status.status = status
                logger.info(f"更新框架状态: {old_status} -> {status}")
            else:
                # 创建新状态记录
                new_status = FrameworkStatus(
                    framework_id=framework_id,
                    framework_name=name,
                    status=status,
                    type=type_,
                    time=time
                )
                db.add(new_status)
                logger.info(f"创建新框架状态记录: {name} ({type_})")
            
            db.commit()
            logger.info("框架状态保存成功")
            return True
            
    except Exception as e:
        logger.error(f"保存框架状态失败: {e}")
        return False


def update_framework_status_and_path(framework_id: str, status: str, framework_path: Optional[str]) -> bool:
    """
    更新框架状态和本地路径
    
    同时更新框架的状态和本地存储路径，通常在下载完成后调用。
    
    :param framework_id: 框架唯一标识符
    :type framework_id: str
    :param status: 新的框架状态
    :type status: str
    :param framework_path: 框架本地存储路径
    :type framework_path: Optional[str]
    :return: 更新成功返回True，失败返回False
    :rtype: bool
    
    Process:
        1. 查找框架状态记录
        2. 更新状态和路径字段
        3. 提交数据库事务
        
    Note:
        - 框架必须已存在状态记录
        - 路径可以为None（下载失败时）
        - 通常在下载任务完成时调用
    """
    logger.info(f"更新框架状态和路径，框架ID: {framework_id}, 状态: {status}")
    
    try:
        with SessionLocal() as db:
            framework_status = db.query(FrameworkStatus).filter_by(framework_id=framework_id).first()
            
            if framework_status:
                old_status = framework_status.status
                framework_status.status = status
                framework_status.path = str(framework_path) if framework_path else None
                
                db.commit()
                logger.info(f"框架状态和路径更新成功: {old_status} -> {status}, 路径: {framework_path}")
                return True
            else:
                logger.error(f"框架状态记录不存在: {framework_id}")
                return False
                
    except Exception as e:
        logger.error(f"更新框架状态和路径失败: {e}")
        return False


def get_all_framework_status() -> List[Dict[str, Any]]:
    """
    获取所有框架状态信息
    
    获取数据库中所有框架的状态信息，转换为字典列表格式。
    
    :return: 框架状态字典列表
    :rtype: List[Dict[str, Any]]
    
    返回格式::
    
        [
            {
                "id": 1,
                "framework_id": "xxx",
                "framework_name": "策略框架",
                "status": "finished",
                "type": "strategy",
                "time": "2024-01-01 12:00",
                "path": "/path/to/framework"
            },
            ...
        ]
        
    Note:
        - 返回所有框架的状态信息
        - 使用orm_to_dict转换为字典格式
        - 适用于状态列表展示
    """
    logger.info("获取所有框架状态信息")
    
    try:
        with SessionLocal() as db:
            status_list = db.query(FrameworkStatus).all()
            result = [orm_to_dict(s) for s in status_list]
            logger.info(f"成功获取框架状态信息，共{len(result)}个框架")
            return result
    except Exception as e:
        logger.error(f"获取所有框架状态失败: {e}")
        return []


def get_all_finished_framework_status() -> List[FrameworkStatus]:
    logger.info("获取所有框架状态信息")

    try:
        with SessionLocal() as db:
            status_list = db.query(FrameworkStatus).filter_by(status=StatusEnum.FINISHED).all()
            logger.info(f"成功获取框架状态信息，共{len(status_list)}个框架")
            return status_list
    except Exception as e:
        logger.error(f"获取所有框架状态失败: {e}")
        return []


def get_finished_data_center_status() -> Optional[FrameworkStatus]:
    """
    获取已完成的数据中心状态
    
    查找类型为data_center且状态为finished的框架记录。
    用于检查数据中心是否已成功下载。
    
    :return: 数据中心状态对象，如果不存在则返回None
    :rtype: Optional[FrameworkStatus]
    
    Note:
        - 专门用于数据中心框架的状态检查
        - 只返回已完成下载的数据中心
        - 用于依赖数据中心的功能检查
    """
    logger.info("获取已完成的数据中心状态")
    
    try:
        with SessionLocal() as db:
            status = db.query(FrameworkStatus).filter_by(
                type='data_center', 
                status=StatusEnum.FINISHED
            ).first()
            
            if status:
                logger.info(f"找到已完成的数据中心: {status.framework_name}")
            else:
                logger.info("未找到已完成的数据中心")
            
            return status
    except Exception as e:
        logger.error(f"获取数据中心状态失败: {e}")
        return None


def get_framework_status(framework_id: str) -> Optional[FrameworkStatus]:
    """
    获取指定框架的状态信息
    
    根据框架ID获取特定框架的状态记录。
    
    :param framework_id: 框架唯一标识符
    :type framework_id: str
    :return: 框架状态对象，如果不存在则返回None
    :rtype: Optional[FrameworkStatus]
    
    Note:
        - 返回完整的FrameworkStatus ORM对象
        - 包含状态、路径、类型等所有信息
        - 用于单个框架的状态检查
    """
    logger.info(f"获取框架状态，框架ID: {framework_id}")
    
    try:
        with SessionLocal() as db:
            status = db.query(FrameworkStatus).filter_by(framework_id=framework_id).first()
            
            if status:
                logger.info(f"找到框架状态: {status.framework_name} ({status.status})")
            else:
                logger.info("框架状态不存在")
            
            return status
    except Exception as e:
        logger.error(f"获取框架状态失败: {e}")
        return None


def clean_old_data_center_records() -> int:
    """
    清理旧的数据中心记录
    
    保留最新的数据中心记录，删除其他旧记录。
    确保数据库中只存在一条数据中心记录。
    
    :return: 删除的记录数量
    :rtype: int
    """
    logger.info("开始清理旧的数据中心记录")
    
    try:
        with SessionLocal() as db:
            # 获取所有已完成的数据中心记录，按ID降序排序
            all_data_centers = db.query(FrameworkStatus).filter_by(
                type='data_center', 
                status=StatusEnum.FINISHED
            ).order_by(FrameworkStatus.id.desc()).all()
            
            if len(all_data_centers) <= 1:
                logger.info(f"数据中心记录数量正常: {len(all_data_centers)}条")
                return 0
            
            # 保留第一条（最新的），删除其余的
            latest_record = all_data_centers[0]
            old_records = all_data_centers[1:]
            
            logger.warning(f"发现多条数据中心记录，保留最新记录 (ID: {latest_record.id})，删除 {len(old_records)} 条旧记录")
            
            deleted_count = 0
            for old_record in old_records:
                logger.info(f"删除旧数据中心记录: ID={old_record.id}, 名称={old_record.framework_name}")
                db.delete(old_record)
                deleted_count += 1
            
            db.commit()
            logger.info(f"成功清理 {deleted_count} 条旧数据中心记录")
            return deleted_count
            
    except Exception as e:
        logger.error(f"清理旧数据中心记录失败: {e}")
        return 0


def delete_framework_status(framework_id: str) -> bool:
    """
    删除框架状态记录
    
    从数据库中删除指定框架的状态记录。
    通常在框架被完全删除时调用。
    
    :param framework_id: 要删除的框架ID
    :type framework_id: str
    :return: 删除成功返回True，失败返回False
    :rtype: bool
    
    Process:
        1. 查找并删除框架状态记录
        2. 提交数据库事务
        3. 记录删除结果
        
    Note:
        - 物理删除数据库记录
        - 不可恢复操作，请谨慎使用
        - 通常配合框架文件删除一起执行
    """
    logger.info(f"删除框架状态记录，框架ID: {framework_id}")
    
    try:
        with SessionLocal() as db:
            # 执行删除操作
            deleted_count = db.query(FrameworkStatus).filter_by(framework_id=framework_id).delete()
            db.commit()
            
            if deleted_count > 0:
                logger.info(f"成功删除框架状态记录，删除数量: {deleted_count}")
                return True
            else:
                logger.warning(f"框架状态记录不存在，无需删除: {framework_id}")
                return True  # 记录不存在也算删除成功
                
    except Exception as e:
        logger.error(f"删除框架状态记录失败: {e}")
        return False
