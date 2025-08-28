"""
设备信息解析模块

该模块提供设备信息解析和设备ID生成功能。
从HTTP请求头中解析设备类型、浏览器信息等。

主要功能：
1. 解析User-Agent获取设备类型和浏览器信息
2. 生成设备唯一标识符
3. 提取IP地址信息

"""

import hashlib
import re
from typing import Dict
from fastapi import Request
from utils.log_kit import get_logger

logger = get_logger()


def parse_device_info(request: Request) -> Dict[str, str]:
    """
    解析设备信息
    
    从HTTP请求中解析设备类型、浏览器信息等。
    
    :param request: FastAPI请求对象
    :type request: Request
    :return: 设备信息字典
    :rtype: Dict[str, str]
    
    Returns:
        Dict containing:
            - device_type: pc/mobile/tablet
            - browser_info: 浏览器名称和版本
            - ip_address: IP地址
            - device_id: 设备唯一标识符
    """
    user_agent = request.headers.get("User-Agent", "")
    ip_address = _get_client_ip(request)
    
    # 调试日志记录
    logger.debug(f"原始User-Agent: {user_agent}")
    
    device_type = _parse_device_type(user_agent)
    browser_info = _parse_browser_info(user_agent)
    device_id = _generate_device_id(user_agent, ip_address)
    
    logger.info(f"解析设备信息: 类型={device_type}, 浏览器={browser_info}, IP={ip_address}")
    logger.debug(f"生成设备ID: {device_id}")
    
    return {
        "device_type": device_type,
        "browser_info": browser_info,
        "ip_address": ip_address,
        "device_id": device_id
    }


def _get_client_ip(request: Request) -> str:
    """
    获取客户端真实IP地址
    
    优先级：X-Forwarded-For > X-Real-IP > client.host
    
    :param request: FastAPI请求对象
    :type request: Request
    :return: IP地址
    :rtype: str
    """
    # 检查代理头
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For可能包含多个IP，取第一个
        ip = forwarded_for.split(",")[0].strip()
        logger.debug(f"IP获取路径: X-Forwarded-For, 值: {forwarded_for}, 解析IP: {ip}")
        return ip
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        ip = real_ip.strip()
        logger.debug(f"IP获取路径: X-Real-IP, 值: {ip}")
        return ip
    
    # 回退到直连IP
    if hasattr(request, "client") and request.client:
        ip = request.client.host
        logger.debug(f"IP获取路径: 直连client.host, 值: {ip}")
        return ip
    
    logger.debug("IP获取路径: 无法获取，返回unknown")
    return "unknown"


def _parse_device_type(user_agent: str) -> str:
    """
    解析设备类型
    
    :param user_agent: User-Agent字符串
    :type user_agent: str
    :return: 设备类型：pc/mobile/tablet
    :rtype: str
    """
    ua_lower = user_agent.lower()
    
    # 移动设备检测
    mobile_patterns = [
        r'mobile', r'android', r'iphone', r'ipod', 
        r'blackberry', r'windows phone', r'opera mini'
    ]
    
    # 平板设备检测
    tablet_patterns = [
        r'tablet', r'ipad', r'android(?!.*mobile)'
    ]
    
    # 检测平板
    for pattern in tablet_patterns:
        if re.search(pattern, ua_lower):
            return "tablet"
    
    # 检测手机
    for pattern in mobile_patterns:
        if re.search(pattern, ua_lower):
            return "mobile"
    
    # 默认为PC
    return "pc"


def _parse_browser_info(user_agent: str) -> str:
    """
    解析浏览器信息
    
    支持iOS专用浏览器检测，正确识别Chrome、Firefox、Edge等在iOS上的版本。
    检测优先级：iOS专用标识 > 桌面/Android标识 > Safari标识
    
    :param user_agent: User-Agent字符串
    :type user_agent: str
    :return: 浏览器名称和版本，如 "chrome 126.0.0.0"
    :rtype: str
    """
    # 浏览器解析规则（按优先级排序）
    browser_patterns = [
        # iOS专用浏览器检测（必须优先于通用检测）
        (r'CriOS/(\d+\.?\d*\.?\d*\.?\d*)', 'chrome'),     # iOS Chrome
        (r'FxiOS/(\d+\.?\d*\.?\d*\.?\d*)', 'firefox'),    # iOS Firefox  
        (r'EdgiOS/(\d+\.?\d*\.?\d*\.?\d*)', 'edge'),      # iOS Edge
        
        # 桌面和Android浏览器检测
        (r'Edg/(\d+\.?\d*\.?\d*\.?\d*)', 'edge'),        # Chromium Edge（新增，优先于Chrome）
        (r'Firefox/(\d+\.?\d*)', 'firefox'),
        (r'Chrome/(\d+\.?\d*\.?\d*\.?\d*)', 'chrome'),
        (r'Edge/(\d+\.?\d*)', 'edge'),                   # Legacy Edge
        (r'Opera/(\d+\.?\d*)', 'opera'),
        
        # Safari检测（必须在最后，因为其他iOS浏览器也包含Safari标识）
        (r'Version/(\d+\.?\d*) Mobile/.*Safari', 'safari'),  # 移动Safari
        (r'Version/(\d+\.?\d*) Safari/(\d+\.?\d*)', 'safari'),  # 桌面Safari
    ]
    
    for pattern, browser_name in browser_patterns:
        match = re.search(pattern, user_agent, re.IGNORECASE)
        if match:
            version = match.group(1)
            return f"{browser_name} {version}"
    
    # 未知浏览器
    return "unknown browser"


def _generate_device_id(user_agent: str, ip_address: str) -> str:
    """
    生成设备唯一标识符
    
    基于User-Agent和IP地址生成稳定的设备ID。
    使用SHA256哈希确保ID的唯一性和一致性。
    
    :param user_agent: User-Agent字符串
    :type user_agent: str
    :param ip_address: IP地址
    :type ip_address: str
    :return: 设备ID（64位十六进制字符串）
    :rtype: str
    """
    # 构造设备指纹
    device_fingerprint = f"{user_agent}:{ip_address}"
    
    # 生成SHA256哈希
    hash_object = hashlib.sha256(device_fingerprint.encode('utf-8'))
    device_id = hash_object.hexdigest()
    
    return device_id


def validate_device_id(device_id: str) -> bool:
    """
    验证设备ID格式
    
    :param device_id: 设备ID
    :type device_id: str
    :return: 验证结果
    :rtype: bool
    """
    if not device_id:
        return False
    
    # 检查长度（SHA256 = 64位十六进制）
    if len(device_id) != 64:
        return False
    
    # 检查是否为有效的十六进制字符串
    try:
        int(device_id, 16)
        return True
    except ValueError:
        return False
