"""
设备数据库操作模块

该模块提供多设备登录系统的所有数据库操作功能。
封装了设备注册、管理、验证等核心数据库操作。

主要功能：
1. 设备注册和更新
2. 设备列表查询
3. 设备踢下线操作
4. 设备数量限制管理
5. 设备活跃状态管理

技术特性：
- 使用SQLAlchemy ORM进行数据库操作
- 自动会话管理和事务处理
- 完善的错误处理和日志记录
- 支持数据模型转换

"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

from config import MAX_DEVICES_PER_USER
from db.db import SessionLocal, Device
from utils.log_kit import get_logger

# 初始化日志记录器
logger = get_logger()


def register_or_update_device(
    device_id: str,
    user_id: int,
    device_type: str,
    browser_info: str,
    ip_address: str,
    token: str
) -> bool:
    """
    注册或更新设备
    
    如果设备已存在则更新信息，否则创建新设备记录。
    自动处理设备数量限制，超过限制时清理最久未活跃的设备。
    
    :param device_id: 设备唯一标识符
    :type device_id: str
    :param user_id: 用户ID
    :type user_id: int
    :param device_type: 设备类型
    :type device_type: str
    :param browser_info: 浏览器信息
    :type browser_info: str
    :param ip_address: IP地址
    :type ip_address: str
    :param token: 设备token
    :type token: str
    :return: 操作成功返回True，失败返回False
    :rtype: bool
    """
    logger.info(f"注册/更新设备: 设备ID={device_id}, 用户ID={user_id}, 类型={device_type}")
    
    try:
        with SessionLocal() as db:
            # 查找现有设备
            existing_device = db.query(Device).filter_by(id=device_id).first()
            
            if existing_device:
                # 更新现有设备
                existing_device.device_type = device_type
                existing_device.browser_info = browser_info
                existing_device.ip_address = ip_address
                existing_device.last_active_time = datetime.now()
                existing_device.token = token
                existing_device.is_active = 1  # 确保设备活跃
                
                logger.info(f"更新现有设备: {device_id}")
            else:
                # 检查设备数量限制
                if not _check_and_manage_device_limit(db, user_id):
                    logger.error(f"设备数量超过限制，无法注册新设备: {device_id}")
                    return False
                
                # 创建新设备
                new_device = Device(
                    id=device_id,
                    user_id=user_id,
                    device_type=device_type,
                    browser_info=browser_info,
                    ip_address=ip_address,
                    last_active_time=datetime.now(),
                    created_time=datetime.now(),
                    token=token,
                    is_active=1
                )
                db.add(new_device)
                logger.info(f"创建新设备: {device_id}")
            
            db.commit()
            logger.info(f"设备注册/更新成功: {device_id}")
            return True
            
    except Exception as e:
        logger.error(f"注册/更新设备失败: {e}")
        return False


def get_user_devices(user_id: int) -> List[Dict[str, Any]]:
    """
    获取用户的所有设备列表
    
    返回用户所有活跃设备的详细信息。
    
    :param user_id: 用户ID
    :type user_id: int
    :return: 设备信息列表
    :rtype: List[Dict[str, Any]]
    
    返回格式::
    
        [
            {
                "id": "device_id",
                "device_type": "pc",
                "browser_info": "Chrome 126.0.0.0",
                "ip_address": "192.168.1.1",
                "last_active_time": "2024-01-01 12:00:00",
                "created_time": "2024-01-01 10:00:00",
                "is_current": True  # 是否为当前设备
            }
        ]
    """
    logger.info(f"获取用户设备列表: 用户ID={user_id}")
    
    try:
        with SessionLocal() as db:
            devices = db.query(Device).filter_by(
                user_id=user_id,
                is_active=1
            ).order_by(Device.last_active_time.desc()).all()
            
            device_list = []
            for device in devices:
                device_info = {
                    "id": device.id,
                    "device_type": device.device_type,
                    "browser_info": device.browser_info,
                    "ip_address": device.ip_address,
                    "last_active_time": device.last_active_time.strftime('%Y-%m-%d %H:%M:%S') if device.last_active_time else '',
                    "created_time": device.created_time.strftime('%Y-%m-%d %H:%M:%S') if device.created_time else '',
                    "is_current": False  # 默认为False，需要在调用处设置
                }
                device_list.append(device_info)
            
            logger.info(f"成功获取设备列表，共{len(device_list)}个设备")
            return device_list
            
    except Exception as e:
        logger.error(f"获取用户设备列表失败: {e}")
        return []


def kick_device(device_id: str, user_id: int) -> bool:
    """
    踢设备下线
    
    将指定设备设置为非活跃状态，使其token失效。
    
    :param device_id: 设备ID
    :type device_id: str
    :param user_id: 用户ID（用于安全验证）
    :type user_id: int
    :return: 操作成功返回True，失败返回False
    :rtype: bool
    """
    logger.info(f"踢设备下线: 设备ID={device_id}, 用户ID={user_id}")
    
    try:
        with SessionLocal() as db:
            device = db.query(Device).filter_by(
                id=device_id,
                user_id=user_id
            ).first()
            
            if not device:
                logger.error(f"设备不存在或不属于当前用户: {device_id}")
                return False
            
            # 设置为非活跃状态
            device.is_active = 0
            db.commit()
            
            logger.info(f"设备已踢下线: {device_id}")
            return True
            
    except Exception as e:
        logger.error(f"踢设备下线失败: {e}")
        return False


def kick_multiple_devices(device_ids: List[str], user_id: int) -> Tuple[int, int]:
    """
    批量踢设备下线
    
    :param device_ids: 设备ID列表
    :type device_ids: List[str]
    :param user_id: 用户ID
    :type user_id: int
    :return: (成功数量, 失败数量)
    :rtype: Tuple[int, int]
    """
    logger.info(f"批量踢设备下线: 设备数量={len(device_ids)}, 用户ID={user_id}")
    
    success_count = 0
    fail_count = 0
    
    for device_id in device_ids:
        if kick_device(device_id, user_id):
            success_count += 1
        else:
            fail_count += 1
    
    logger.info(f"批量踢设备完成: 成功={success_count}, 失败={fail_count}")
    return success_count, fail_count


def verify_device_active(device_id: str) -> bool:
    """
    验证设备是否活跃
    
    :param device_id: 设备ID
    :type device_id: str
    :return: 设备活跃返回True，否则返回False
    :rtype: bool
    """
    try:
        with SessionLocal() as db:
            device = db.query(Device).filter_by(
                id=device_id,
                is_active=1
            ).first()
            
            return device is not None
            
    except Exception as e:
        logger.error(f"验证设备活跃状态失败: {e}")
        return False


def update_device_activity(device_id: str) -> bool:
    """
    更新设备活跃时间
    
    :param device_id: 设备ID
    :type device_id: str
    :return: 更新成功返回True，失败返回False
    :rtype: bool
    """
    try:
        with SessionLocal() as db:
            device = db.query(Device).filter_by(
                id=device_id,
                is_active=1
            ).first()
            
            if device:
                device.last_active_time = datetime.now()
                db.commit()
                return True
            
            return False
            
    except Exception as e:
        logger.error(f"更新设备活跃时间失败: {e}")
        return False


def get_device_by_id(device_id: str) -> Optional[Device]:
    """
    根据设备ID获取设备信息
    
    :param device_id: 设备ID
    :type device_id: str
    :return: 设备对象，不存在返回None
    :rtype: Optional[Device]
    """
    try:
        with SessionLocal() as db:
            device = db.query(Device).filter_by(id=device_id).first()
            return device
            
    except Exception as e:
        logger.error(f"获取设备信息失败: {e}")
        return None


def cleanup_inactive_devices(user_id: int, keep_count: int = MAX_DEVICES_PER_USER) -> int:
    """
    清理非活跃设备
    
    保留最近活跃的设备，删除多余的设备记录。
    
    :param user_id: 用户ID
    :type user_id: int
    :param keep_count: 保留的设备数量
    :type keep_count: int
    :return: 清理的设备数量
    :rtype: int
    """
    logger.info(f"清理非活跃设备: 用户ID={user_id}, 保留数量={keep_count}")
    
    try:
        with SessionLocal() as db:
            # 获取所有活跃设备，按最后活跃时间降序排列
            devices = db.query(Device).filter_by(
                user_id=user_id,
                is_active=1
            ).order_by(Device.last_active_time.desc()).all()
            
            if len(devices) <= keep_count:
                logger.info("设备数量未超过限制，无需清理")
                return 0
            
            # 需要删除的设备
            devices_to_remove = devices[keep_count:]
            removed_count = 0
            
            for device in devices_to_remove:
                device.is_active = 0
                removed_count += 1
                logger.info(f"清理设备: {device.id}")
            
            db.commit()
            logger.info(f"清理完成，共清理{removed_count}个设备")
            return removed_count
            
    except Exception as e:
        logger.error(f"清理非活跃设备失败: {e}")
        return 0


def _check_and_manage_device_limit(db, user_id: int) -> bool:
    """
    检查并管理设备数量限制
    
    内部函数，用于在注册新设备前检查数量限制。
    如果超过限制，自动清理最久未活跃的设备。
    
    :param db: 数据库会话
    :param user_id: 用户ID
    :type user_id: int
    :return: 可以注册新设备返回True，否则返回False
    :rtype: bool
    """
    # 统计当前活跃设备数量
    active_device_count = db.query(Device).filter_by(
        user_id=user_id,
        is_active=1
    ).count()
    
    logger.info(f"当前活跃设备数量: {active_device_count}/{MAX_DEVICES_PER_USER}")
    
    if active_device_count < MAX_DEVICES_PER_USER:
        return True
    
    # 超过限制，清理最久未活跃的设备
    logger.warning(f"设备数量达到上限，开始清理最久未活跃的设备")
    
    # 获取最久未活跃的设备
    oldest_device = db.query(Device).filter_by(
        user_id=user_id,
        is_active=1
    ).order_by(Device.last_active_time.asc()).first()
    
    if oldest_device:
        oldest_device.is_active = 0
        logger.info(f"自动清理最久未活跃设备: {oldest_device.id}")
        return True
    
    return False


def get_device_count(user_id: int) -> int:
    """
    获取用户活跃设备数量
    
    :param user_id: 用户ID
    :type user_id: int
    :return: 活跃设备数量
    :rtype: int
    """
    try:
        with SessionLocal() as db:
            count = db.query(Device).filter_by(
                user_id=user_id,
                is_active=1
            ).count()
            
            return count
            
    except Exception as e:
        logger.error(f"获取设备数量失败: {e}")
        return 0
