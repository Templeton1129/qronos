import json
import traceback
from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware

from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, TOKEN_REFRESH_THRESHOLD_MINUTES
from db.db_ops import get_user, update_user_token
from db.device_ops import verify_device_active, update_device_activity, get_device_by_id, register_or_update_device
from service.xbx_api import XbxAPI
from utils.constant import PREFIX
from utils.gcode import verify_google_code
from utils.log_kit import get_logger

logger = get_logger()


oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"/{PREFIX}/login")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None, device_id: str = None, user_id: int = None):
    """
    创建访问token
    
    生成包含用户信息和设备信息的JWT token。
    
    :param data: token数据
    :type data: dict
    :param expires_delta: 过期时间增量
    :type expires_delta: Optional[timedelta]
    :param device_id: 设备ID
    :type device_id: str
    :param user_id: 用户ID
    :type user_id: int
    :return: JWT token字符串
    :rtype: str
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    
    # 添加设备信息到token payload
    if device_id:
        to_encode.update({"device_id": device_id})
    if user_id:
        to_encode.update({"user_id": user_id})
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def is_token_near_expiry(token: str) -> bool:
    """检查token是否即将过期（剩余时间少于阈值）"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp_timestamp = payload.get("exp")
        if not exp_timestamp:
            return True  # 没有过期时间，认为需要刷新

        exp_datetime = datetime.utcfromtimestamp(exp_timestamp)
        current_datetime = datetime.utcnow()
        time_remaining = exp_datetime - current_datetime

        # 如果剩余时间少于阈值，返回True
        return time_remaining.total_seconds() < (TOKEN_REFRESH_THRESHOLD_MINUTES * 60)
    except (JWTError, ValueError):
        return True  # 解析失败，认为需要刷新


def google_login(google_secret_key: Optional[str], code: str, device_id: str = None, user_id: int = None):
    """
    Google登录验证
    
    :param google_secret_key: Google Secret Key
    :type google_secret_key: Optional[str]
    :param code: Google Authenticator验证码
    :type code: str
    :param device_id: 设备ID
    :type device_id: str
    :param user_id: 用户ID
    :type user_id: int
    :return: 包含token的字典
    :rtype: dict
    """
    google_secret = None
    user = get_user()
    if user:
        google_secret = user.secret
    if google_secret is None:
        # 首次登录，需前端传 google_secret_key 和 code
        if not google_secret_key or not code:
            raise HTTPException(status_code=400, detail="首次登录需提供google_secret_key和code")
        if not verify_google_code(google_secret_key, code):
            raise HTTPException(status_code=400, detail="Google验证码错误")
    else:
        # 后续登录，只需传 code
        if not verify_google_code(google_secret, code):
            raise HTTPException(status_code=400, detail="Google验证码错误")
    
    # 登录成功，生成token（包含设备信息）
    access_token = create_access_token(
        data={"sub": "google_user"}, 
        device_id=device_id, 
        user_id=user_id or (user.id if user else None)
    )
    return {"access_token": access_token, "token_type": "Bearer"}


def verify_token(token: str):
    """验证token并返回用户信息，包含设备验证"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="WebUI会话已到期",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    device_inactive_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="设备已被踢下线，请重新登录",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # 解码JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        device_id: str = payload.get("device_id")
        user_id: int = payload.get("user_id")
        
        if username is None:
            raise credentials_exception
        
        # 验证用户存在
        user = get_user()
        if not user:
            raise credentials_exception
        
        # 如果token包含设备信息，进行设备验证
        if device_id:
            # 验证设备是否仍然活跃
            if not verify_device_active(device_id):
                logger.warning(f"设备已被踢下线: {device_id}")
                raise device_inactive_exception
            
            # 更新设备活跃时间
            update_device_activity(device_id)
        
        return {
            "username": username,
            "token": token,
            "device_id": device_id,
            "user_id": user_id or user.id
        }
        
    except JWTError:
        raise credentials_exception


def get_current_user_from_request(request: Request):
    """从请求中获取当前用户信息（通过中间件设置）"""
    if hasattr(request.state, 'current_user'):
        return request.state.current_user
    return None


class AuthMiddleware(BaseHTTPMiddleware):
    """认证中间件，统一处理token校验和刷新"""

    # 不需要认证的路径
    SKIP_AUTH_PATHS = {
        f"/{PREFIX}/first",
        f"/{PREFIX}/login",
        f"/{PREFIX}/declaration",
    }

    # wx用户信息不进行验证的路径
    SKIP_AUTH_USER_PATHS = {
        f"/{PREFIX}/user/info",
        f"/{PREFIX}/logout",
    }

    @staticmethod
    def _should_refresh_xbx_token(user) -> bool:
        """判断是否需要刷新xbx token"""
        if not user.xbx_token_expiry_time:
            return True
        
        try:
            expiry_time = datetime.strptime(user.xbx_token_expiry_time, '%Y-%m-%d %H:%M:%S')
            time_remaining = (expiry_time - datetime.now()).total_seconds()
            return time_remaining < (TOKEN_REFRESH_THRESHOLD_MINUTES * 60)
        except (ValueError, TypeError):
            return True

    def _refresh_xbx_token_if_needed(self):
        """如果需要，刷新xbx token"""
        user = get_user()
        if self._should_refresh_xbx_token(user):
            api = XbxAPI.get_instance()
            api._ensure_token()

    async def dispatch(self, request: Request, call_next):
        # 跳过不需要认证的路径
        if request.url.path in self.SKIP_AUTH_PATHS:
            return await call_next(request)

        # 检查是否有Authorization头
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            return Response(
                content=json.dumps({"msg": "未提供认证token", "code": 401}),
                status_code=401,
                media_type="application/json"
            )

        # 提取token
        token = authorization.split(" ")[1]

        try:
            # 验证token（只捕获认证相关异常）
            user_info = verify_token(token)

            # 将用户信息添加到request.state中，供后续使用
            request.state.current_user = user_info

        except HTTPException as e:
            # 认证相关的HTTPException
            return Response(
                content=json.dumps({"msg": e.detail, "code": e.status_code}),
                status_code=e.status_code,
                media_type="application/json"
            )
        except (JWTError, ValueError) as e:
            # JWT解析相关异常
            return Response(
                content=json.dumps({"msg": "token无效", "code": 401}),
                status_code=401,
                media_type="application/json"
            )

        # 如果不是绑定用户的接口，都需要验证一下 wx 是否过期
        if request.url.path not in self.SKIP_AUTH_USER_PATHS:
            try:
                self._refresh_xbx_token_if_needed()
            except Exception as e:
                logger.error(f"验证 wx token 错误： {e}")
                logger.error(traceback.format_exc())
                return Response(
                    content=json.dumps({"msg": "WX用户信息失效，请重新扫描二维码绑定用户", "code": 444}),
                    status_code=444,
                    media_type="application/json"
                )

        # 调用下一个处理器（业务逻辑异常会正常抛出）
        response = await call_next(request)

        # 只在请求成功处理且token即将过期时才刷新token
        if response.status_code < 400 and is_token_near_expiry(token):
            # 刷新token时保持设备信息
            device_id = user_info.get("device_id")
            user_id = user_info.get("user_id")
            new_token = create_access_token(
                data={"sub": user_info["username"]},
                device_id=device_id,
                user_id=user_id
            )
            response.headers["X-Refresh-Token"] = new_token
            
            # 更新设备token（如果有设备信息）
            if device_id:
                device = get_device_by_id(device_id)
                if device:
                    register_or_update_device(
                        device_id=device_id,
                        user_id=user_id,
                        device_type=device.device_type,
                        browser_info=device.browser_info,
                        ip_address=device.ip_address,
                        token=new_token
                    )
            else:
                # 向后兼容：更新用户token
                update_user_token(new_token)

        return response
 