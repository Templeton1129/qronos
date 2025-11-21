"""
XBX API 服务模块

该模块提供与第三方XBX API的交互功能，主要包括：
1. 用户认证和token管理
2. 基础代码版本获取和下载
3. 市值数据下载
4. 文件下载和解压功能
5. 自动重试和错误处理机制

主要特性：
- 单例模式管理API实例
- 自动token刷新机制
- 统一的重试装饰器
- 完善的错误处理和日志记录
- 支持大文件下载和解压

"""

import json
import os
import time
import traceback
import zipfile
import random
from datetime import datetime
from typing import Optional, Tuple
from functools import wraps

import requests

from model.enum_kit import StatusEnum
from model.model import Pm2CfgModel
from service.command import create_pm2_cfg
from utils.constant import (
    api_qtcls_user_login_token_url, api_qtcls_data_client_basic_code_url, api_qtcls_data_coin_cap_hist_url,
    api_qtcls_user_info_url, api_qtcls_basic_code_download_ticket_url, api_qtcls_basic_code_download_link_url,
    TMP_PATH, FRAMEWORK_TYPE, DATA_CENTER_ID, FRAMEWORK_ROOT_PATH, api_qtcls_user_info_v2_url,
)
from db.db_ops import (
    get_user, save_user_credentials, update_user_xbx_token, save_framework_status, update_framework_status_and_path,
    get_framework_status
)
from utils.log_kit import logger


class TokenExpiredException(Exception):
    """
    Token过期异常
    
    当检测到多次401错误且token刷新失败时抛出此异常。
    表示用户的apikey已过期，需要重新获取wx_token和更新用户凭据。
    """

    def __init__(self, message="Token已过期，需要重新认证"):
        self.message = message
        super().__init__(self.message)


def retry_request(max_retries=5):
    """
    请求重试装饰器
    
    为网络请求提供自动重试功能，支持指数退避策略。
    当请求失败时，会自动重试指定次数，每次重试间隔递增。
    
    :param max_retries: 最大重试次数，默认5次
    :type max_retries: int
    :return: 装饰器函数
    :rtype: function
    
    Example:
        @retry_request(max_retries=3)
        def api_call():
            return requests.get("https://api.example.com")
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:  # 不是最后一次重试
                        # 指数退避策略：1-3秒 * (重试次数 + 1)
                        delay = random.uniform(1, 3) * (attempt + 1)
                        logger.warning(f"请求失败，第{attempt + 1}次重试，{delay:.2f}秒后重试: {e}")
                        time.sleep(delay)
                    else:
                        logger.error(f"请求失败，已达到最大重试次数{max_retries}: {e}")

            # 所有重试都失败，抛出最后一个异常
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


def _download_file_zip(download_url, temp_path, target_path, max_retries=5):
    """
    下载并解压ZIP文件，带重试逻辑
    
    该函数实现了完整的文件下载和解压流程，包括：
    - 流式下载大文件
    - 自动重试机制
    - 损坏文件清理
    - 解压到指定目录
    
    :param download_url: 文件下载链接
    :type download_url: str
    :param temp_path: 临时文件存储路径
    :type temp_path: Path
    :param target_path: 目标解压路径
    :type target_path: Path
    :param max_retries: 最大重试次数，默认3次
    :type max_retries: int
    :return: 成功返回True，失败返回False
    :rtype: bool
    
    note:
        - 使用流式下载避免内存溢出
        - 失败时会自动清理损坏的临时文件
        - 支持断点续传（如果文件已存在则跳过下载）
    """
    for attempt in range(max_retries):
        try:
            # 检查文件是否已存在，避免重复下载
            if not temp_path.exists():
                logger.info(f"开始下载文件: {download_url}")
                # 使用流式下载，避免大文件导致内存溢出
                with requests.get(download_url, stream=True, timeout=60 * 5) as r:
                    r.raise_for_status()
                    with open(temp_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                logger.info(f"文件下载完成: {temp_path}")

            # 解压ZIP文件到目标目录
            logger.info(f"开始解压文件到: {target_path}")
            with zipfile.ZipFile(temp_path, 'r') as zip_ref:
                zip_ref.extractall(target_path)

            # 清理临时文件
            temp_path.unlink(missing_ok=True)
            logger.info(f"文件解压完成并清理临时文件")
            return True

        except Exception as e:
            if attempt < max_retries - 1:  # 不是最后一次重试
                # 指数退避策略
                delay = random.uniform(1, 3) * (attempt + 1)
                logger.warning(f"下载或解压失败，第{attempt + 1}次重试，{delay:.2f}秒后重试: {e}")
                time.sleep(delay)
                # 清理可能损坏的临时文件
                if temp_path.exists():
                    temp_path.unlink(missing_ok=True)
            else:
                logger.error(f"下载或解压失败，已达到最大重试次数{max_retries}: {e}")
                logger.error(traceback.format_exc())

    # 最终清理可能存在的损坏临时文件
    temp_path.unlink(missing_ok=True)
    return False  # 返回False而不是抛出异常，确保调用方能正常处理失败情况


class XbxAPI:
    """
    XBX API 客户端类
    
    该类采用单例模式，提供与XBX第三方API的完整交互功能。
    主要功能包括用户认证、代码下载、数据获取等。
    
    Features:
        - 单例模式：确保全局只有一个API实例
        - 自动token管理：包括获取、刷新、存储
        - 统一错误处理：标准化的异常处理和重试机制
        - 数据库集成：自动保存用户凭据和状态信息

    Example:
        # 获取API实例
        api = XbxAPI.get_instance()
        
        # 设置用户凭据
        api.set_credentials("user_uuid", "user_apikey")
        
        # 登录获取token
        if api.login():
            # 获取基础代码版本
            versions = api.get_basic_code_version()
    """

    _instance: Optional['XbxAPI'] = None

    def __init__(self):
        """
        初始化XBX API客户端
        
        私有构造函数，仅在单例模式中使用。
        自动从数据库加载用户凭据和token。
        """
        self.uuid: Optional[str] = None
        self.apikey: Optional[str] = None
        self.token: Optional[str] = None
        self._auth_failure_count: int = 0  # 401认证失败计数器
        self._max_auth_failures: int = 5  # 最大允许的认证失败次数
        self._load_credentials()  # 从数据库加载用户凭据
        self._load_token()  # 从数据库加载token

    @classmethod
    def get_instance(cls, uuid=None, apikey=None):
        """
        获取XBX API单例实例
        
        :param uuid: 用户UUID，如果提供则更新凭据
        :type uuid: str, optional
        :param apikey: 用户API密钥，如果提供则更新凭据
        :type apikey: str, optional
        :return: API实例
        :rtype: XbxAPI
        
        note:
            如果是首次调用，会创建新实例。
            如果提供了uuid和apikey，会更新实例的凭据。
        """
        if cls._instance is None:
            cls._instance = XbxAPI()
        if uuid and apikey:
            cls._instance.set_credentials(uuid, apikey)
        return cls._instance

    def _load_credentials(self):
        """
        从数据库加载用户凭据
        
        从数据库中读取用户的UUID和API密钥。
        如果数据库中没有用户信息，凭据将保持为None。
        """
        user = get_user()
        if user:
            self.uuid = user.uuid
            self.apikey = user.apikey

    def _save_credentials(self):
        """
        保存用户凭据到数据库
        
        将当前的UUID和API密钥保存到数据库中。
        用于持久化用户认证信息。
        """
        save_user_credentials(self.uuid, self.apikey)

    def _load_token(self):
        """
        从数据库加载访问token
        
       从数据库中读取当前有效的访问token。
       token用于后续的API调用认证。
       """
        user = get_user()
        if user:
            self.token = user.xbx_token

    def _save_token(self, token):
        """
        保存访问token到数据库
        
        :param token: 要保存的访问token
        :type token: str
        
        将新的token保存到数据库并更新实例状态。
        """
        self.token = token
        update_user_xbx_token(token)

    def set_credentials(self, uuid: str, apikey: str):
        """
        设置用户凭据
        
        :param uuid: 用户UUID
        :type uuid: str
        :param apikey: 用户API密钥
        :type apikey: str
        
        更新实例的凭据信息并保存到数据库。
        通常在用户首次登录或更换账户时调用。
        重置认证失败计数器。
        """
        self.uuid = uuid
        self.apikey = apikey
        self._auth_failure_count = 0  # 重置认证失败计数器
        self._save_credentials()
        logger.info("用户凭据已更新，认证失败计数器已重置")

    @retry_request()
    def login(self) -> bool:
        """
        用户登录获取访问token
        
        使用UUID和API密钥向XBX服务器请求访问token。
        
        :return: 登录成功返回True，失败返回False
        :rtype: bool
        :raises TokenExpiredException: 当连续多次401认证失败时抛出
        
        note:
            - 需要先设置有效的uuid和apikey
            - 成功后会自动保存token到数据库并重置错误计数器
            - 失败时会清空token并增加错误计数器
            - 多次401错误时抛出TokenExpiredException
        """
        if not self.uuid or not self.apikey:
            logger.warning("登录失败：缺少UUID或API密钥")
            return False

        resp = requests.post(api_qtcls_user_login_token_url, data={"uuid": self.uuid, "api_key": self.apikey}, timeout=10)

        if resp.status_code == 200 and resp.json().get("data"):
            token = resp.json()["data"]
            self._save_token(token)
            self._auth_failure_count = 0  # 重置认证失败计数器
            logger.info("登录成功，token已保存，认证失败计数器已重置")
            return True
        else:
            logger.error(f"登录失败，状态码: {resp.status_code}, 响应: {resp.text}")
            self._save_token("")  # 清空无效token

            # 处理401认证失败
            if 400 <= resp.status_code < 500:
                self._auth_failure_count += 1
                logger.warning(f"检测到4xx认证失败，当前失败次数: {self._auth_failure_count}/{self._max_auth_failures}")

                if self._auth_failure_count >= self._max_auth_failures:
                    logger.error(f"连续{self._max_auth_failures}次认证失败，token已过期，需要重新获取用户凭据")
                    raise TokenExpiredException(
                        f"连续{self._max_auth_failures}次认证失败，apikey可能已过期，需要重新认证")

            return False

    def _ensure_token(self):
        """
        确保有有效的访问token
        
        检查当前是否有有效token，如果没有则尝试登录获取。
        
        :raises TokenExpiredException: 当连续多次401认证失败时抛出

        note:
            该方法在所有需要token的API调用前被调用。
        """
        self._load_token()  # 重新加载token，确保是最新的
        if not self.login():
            raise TokenExpiredException("XBX API登录失败，无法获取有效token")

    def _handle_token_refresh(self, resp, params, url, method='GET'):
        """
        统一处理token刷新逻辑
        
        当API返回4xx状态码时，尝试刷新token并重新发送请求。
        
        :param resp: 原始响应对象
        :type resp: Response
        :param params: 请求参数
        :type params: dict
        :param url: 请求URL
        :type url: str
        :param method: 请求方法，默认'GET'
        :type method: str
        :return: 刷新token后的新响应，失败返回None
        :rtype: Response or None
        :raises TokenExpiredException: 当连续多次401认证失败时抛出
        
        note:
            - 仅在4xx状态码时尝试刷新
            - 刷新成功后会更新params中的token
            - 支持GET和POST方法
            - 多次401错误时抛出TokenExpiredException
        """
        if 400 <= resp.status_code < 500:
            logger.info(f"检测到4xx状态码({resp.status_code})，尝试刷新token")

            # 特别处理4xx错误
            self._auth_failure_count += 1
            logger.warning(f"检测到4xx认证失败，当前失败次数: {self._auth_failure_count}/{self._max_auth_failures}")

            if self._auth_failure_count >= self._max_auth_failures:
                logger.error(f"连续{self._max_auth_failures}次认证失败，token已过期，需要重新获取用户凭据")
                raise TokenExpiredException(f"连续{self._max_auth_failures}次认证失败，apikey可能已过期，需要重新认证")

            try:
                if self.login():
                    params["token"] = self.token
                    logger.info("Token刷新成功，重新发送请求")
                    if method.upper() == 'GET':
                        return requests.get(url, params=params, timeout=10)
                    elif method.upper() == 'POST':
                        return requests.post(url, data=params, timeout=10)
                else:
                    logger.error("Token刷新失败")
            except TokenExpiredException:
                # 直接向上传播TokenExpiredException
                raise
        return None

    @retry_request()
    def get_basic_code_version(self, version: str = '') -> dict:
        """
        获取基础代码版本信息
        
        从XBX服务器获取所有可用的基础代码版本信息。
        
        :return: 包含版本信息的字典或错误信息
        :rtype: dict
        
        返回格式::
        
            {
                "data": [
                    {
                        "id": "framework_id",
                        "name": "framework_name",
                        "versions": [
                            {
                                "time": "2024-01-01 12:00",
                                "file": {
                                    "id": "file_id",
                                    "name": "file_name"
                                }
                            }
                        ]
                    }
                ]
            }
            
        或错误信息::
        
            {"error": "error_message"}
            
        note:
            - 自动处理token刷新
            - 返回的数据包含所有框架的版本信息
        """
        self._ensure_token()
        params = {"token": self.token, "version": version}
        resp = requests.get(api_qtcls_data_client_basic_code_url, params=params, timeout=10)

        # 尝试刷新token
        refreshed_resp = self._handle_token_refresh(resp, params, api_qtcls_data_client_basic_code_url)
        if refreshed_resp:
            resp = refreshed_resp
        elif 400 <= resp.status_code < 500:
            return {"error": "token_invalid"}

        if resp.status_code == 200:
            return resp.json()
        return {"error": resp.text}

    @staticmethod
    def _create_pm2_config(framework_id: str, framework_path, app_configs: list):
        """
        创建PM2配置文件
        
        为下载的框架生成PM2进程管理配置文件。
        
        :param framework_id: 框架ID
        :type framework_id: str
        :param framework_path: 框架本地路径
        :type framework_path: Path
        :param app_configs: 应用配置列表，每个元素是app_name
        :type app_configs: list
        
        note:
            - 生成的配置文件保存为 startup.json
            - 支持多个应用的配置
            - 配置包含启动脚本、日志路径等信息
        """
        logger.info(f"为框架 {framework_id} 创建PM2配置，应用列表: {app_configs}")
        pm2_cfg = Pm2CfgModel(apps=[
            create_pm2_cfg(app_name=app_name, framework_id=framework_id, framework_path=framework_path)
            for app_name in app_configs
        ])
        config_path = framework_path / 'startup.json'
        config_path.write_text(json.dumps(pm2_cfg.model_dump(), ensure_ascii=False, indent=2))
        logger.info(f"PM2配置文件已保存: {config_path}")

    def download_data_center_latest(self):
        """
        下载最新的数据中心代码
        
        获取数据中心的最新版本并下载到本地。
        数据中心用于提供实时数据服务。
        
        Process:
            1. 获取所有基础代码版本
            2. 筛选数据中心相关版本
            3. 按时间排序获取最新版本
            4. 下载并解压代码
            5. 生成PM2配置文件
            6. 更新数据库状态
            
        note:
            - 仅处理DATA_CENTER_ID对应的框架
            - 自动生成realtime_data应用的PM2配置
            - 下载过程中会更新数据库状态
        """
        logger.info("开始下载最新数据中心代码")
        result = self.get_basic_code_version()
        if result.get("error"):
            logger.error(f"获取基础代码版本失败: {result.get('error')}")
            return

        # 查找数据中心框架 (ID: '6789163a488832004afe2cda')
        for item in result.get("data", []):
            if item.get("id") == DATA_CENTER_ID:
                if not item.get("versions"):
                    logger.warning("数据中心无可用版本")
                    continue

                # 按时间降序排序，获取最新版本
                sorted_data = sorted(
                    item.get("versions"),
                    key=lambda x: datetime.strptime(x['time'], '%Y-%m-%d %H:%M'),
                    reverse=True
                )
                last_data = sorted_data[0]
                file_info = last_data.get('file')

                logger.info(f"找到最新数据中心版本: {file_info.get('name')} ({last_data.get('time')})")

                framework_status = get_framework_status(file_info.get('id'))
                if framework_status and framework_status.status in [StatusEnum.FINISHED, StatusEnum.DOWNLOADING]:
                    logger.warning(f'数据库中查询框架已经下载完毕或者正在下载中，跳过当前下载， {framework_status}')
                    return

                # 保存下载状态到数据库
                save_framework_status(
                    file_info.get('id'),
                    file_info.get('name'),
                    StatusEnum.DOWNLOADING,
                    FRAMEWORK_TYPE.get(item.get("id")),
                    last_data.get('time')
                )

                # 执行下载
                success, framework_path = self.download_basic_code(file_info.get('id'))

                # 更新最终状态
                update_framework_status_and_path(
                    file_info.get('id'),
                    StatusEnum.FINISHED if success else StatusEnum.FAILED,
                    framework_path
                )

                if success:
                    logger.info("数据中心下载成功，生成PM2配置")
                    # 为数据中心生成PM2配置（仅包含realtime_data应用）
                    self._create_pm2_config(file_info.get('id'), framework_path, ['realtime_data'])
                else:
                    logger.error("数据中心下载失败")

    def download_basic_code_for_id(self, framework_id):
        """
        根据框架ID下载指定的基础代码
        
        :param framework_id: 要下载的框架ID
        :type framework_id: str
        
        Process:
            1. 获取所有基础代码版本
            2. 查找指定ID的框架版本
            3. 下载并解压代码
            4. 生成PM2配置文件
            5. 更新数据库状态
            
        note:
            - 支持所有类型的框架下载
            - 自动生成完整的PM2配置（startup, delist, monitor）
            - 下载过程中会更新数据库状态
        """
        logger.info(f"开始下载框架: {framework_id}")
        result = self.get_basic_code_version()
        if result.get("error"):
            logger.error(f"获取基础代码版本失败: {result.get('error')}")
            return

        # 查找指定ID的框架版本
        for item in result.get("data", []):
            for version in item.get("versions", []):
                if version.get("file").get("id") == framework_id:
                    file_info = version.get("file")

                    logger.info(f"找到框架版本: {file_info.get('name')} ({version.get('time')})")

                    framework_status = get_framework_status(framework_id)
                    if framework_status and framework_status.status in [StatusEnum.FINISHED, StatusEnum.DOWNLOADING]:
                        logger.warning(f'数据库中查询框架已经下载完毕或者正在下载中，跳过当前下载， {framework_status}')
                        return

                    # 保存下载状态到数据库
                    save_framework_status(
                        framework_id,
                        file_info.get("name"),
                        StatusEnum.DOWNLOADING,
                        FRAMEWORK_TYPE.get(item.get("id")),
                        version.get("time")
                    )

                    # 执行下载
                    success, framework_path = self.download_basic_code(framework_id)

                    # 更新最终状态
                    update_framework_status_and_path(
                        framework_id,
                        StatusEnum.FINISHED if success else StatusEnum.FAILED,
                        framework_path
                    )

                    if success:
                        logger.info("框架下载成功，生成PM2配置")
                        # 生成完整的PM2配置
                        if framework_id == DATA_CENTER_ID:
                            self._create_pm2_config(file_info.get('id'), framework_path, ['realtime_data'])
                        else:
                            self._create_pm2_config(framework_id, framework_path, ['startup', 'delist', 'monitor'])
                    else:
                        logger.error("框架下载失败")
                    return

    @retry_request()
    def download_coin_cap_hist(self, coin_cap_path):
        """
        下载历史市值数据
        
        从XBX服务器下载历史市值数据文件。
        
        :param coin_cap_path: 市值数据保存路径
        :type coin_cap_path: Path
        :return: 下载成功返回True，失败返回False
        :rtype: bool
        
        Process:
            1. 获取下载链接
            2. 下载ZIP文件
            3. 解压到指定目录
            
        note:
            - 自动处理token刷新
            - 使用流式下载处理大文件
            - 支持重试机制
        """
        if coin_cap_path.exists():
            logger.warning(f'市值数据目录已存在，可能已经下载过了，跳过当前下载操作')
            return True

        logger.info(f"开始下载市值数据到: {coin_cap_path}")
        self._ensure_token()
        params = {"token": self.token}
        resp = requests.get(api_qtcls_data_coin_cap_hist_url, params=params, timeout=10)

        # 修复：使用正确的URL进行token刷新
        refreshed_resp = self._handle_token_refresh(resp, params, api_qtcls_data_coin_cap_hist_url)
        if refreshed_resp:
            resp = refreshed_resp
        elif 400 <= resp.status_code < 500:
            logger.error("市值数据下载失败：token无效")
            return False

        if resp.status_code == 200 and resp.json().get("code") == 200:
            download_url = resp.json().get("data").get("url")
            logger.info(f"获取到下载链接: {download_url}")

            # 确保目录存在
            TMP_PATH.mkdir(parents=True, exist_ok=True)
            coin_cap_path.mkdir(parents=True, exist_ok=True)

            # 提取文件名
            filename = download_url.split("/")[-1].split('?')[0]

            # 执行下载
            success = _download_file_zip(download_url, TMP_PATH / filename, coin_cap_path)
            if success:
                logger.info("市值数据下载成功")
            else:
                logger.error("市值数据下载失败")
            return success
        else:
            logger.error(f"获取市值数据下载链接失败，状态码: {resp.status_code}, 返回结果: {resp.content}")
            return False

    def get_user_info(self, authorization: str):
        """
        获取用户信息

        根据参数，选择不同的方式获取用户的详细信息。

        :return 用户信息
        """
        if authorization:
            return self.get_user_info_by_authorization(authorization)
        else:
            return self.get_user_info_by_token()

    @staticmethod
    @retry_request()
    def get_user_info_by_authorization(authorization: str):
        """
        获取用户信息

        使用授权token获取用户的详细信息。

        :param authorization: 授权token
        :type authorization: str
        :return: 用户信息字典，失败返回None
        :rtype: dict or None

        note:
            - 静态方法，不需要实例化
            - 用于验证用户身份和获取基本信息
            - 包含UUID、API密钥等关键信息
        """
        logger.info("获取用户信息")
        resp = requests.post(api_qtcls_user_info_url, headers={"Authorization": authorization}, timeout=10)
        if resp.status_code == 200:
            logger.info("用户信息获取成功")
            return resp.json()
        else:
            logger.error(f"用户信息获取失败，状态码: {resp.status_code}")
            return None

    @retry_request()
    def get_user_info_by_token(self):
        """
        获取用户信息v2

        使用授权token获取用户的详细信息。

        :return: 用户信息字典，失败返回None
        :rtype: dict or None

        note:
            - 用于验证用户身份和获取基本信息
            - 包含UUID、API密钥等关键信息
        """
        logger.info("获取用户信息v2")
        self._ensure_token()
        resp = requests.post(api_qtcls_user_info_v2_url, params={"token": self.token}, timeout=10)
        if resp.status_code == 200:
            logger.info("用户信息v2获取成功")
            return resp.json()
        else:
            logger.error(f"用户信息获取v2失败，状态码: {resp.status_code}")
            return None

    @retry_request()
    def _get_download_ticket(self, code_id: str) -> Optional[str]:
        """
        获取下载ticket，带重试机制
        
        向服务器请求下载ticket，用于后续获取实际下载链接。
        
        :param code_id: 代码ID
        :type code_id: str
        :return: 下载ticket，失败返回None
        :rtype: str or None
        
        note:
            - 使用重试装饰器确保稳定性
            - 自动处理token刷新
            - ticket是获取下载链接的前置条件
        """
        self._ensure_token()
        ticket_params = {"token": self.token, "method": "link"}
        ticket_url = api_qtcls_basic_code_download_ticket_url % code_id

        logger.info(f"获取下载ticket: {code_id}")
        ticket_resp = requests.get(ticket_url, params=ticket_params, timeout=10)
        refreshed_resp = self._handle_token_refresh(ticket_resp, ticket_params, ticket_url)
        if refreshed_resp:
            ticket_resp = refreshed_resp
        elif 400 <= ticket_resp.status_code < 500:
            logger.error("获取ticket失败：token无效")
            return None

        if ticket_resp.status_code != 200:
            logger.error(f"获取ticket失败，状态码: {ticket_resp.status_code}")
            return None

        ticket = ticket_resp.json().get("ticket")
        if ticket:
            logger.info(f"成功获取ticket: {ticket}")
        else:
            logger.error("响应中未包含ticket")
        return ticket

    def get_download_url_for_code(self, code_id: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        获取代码下载链接，合并ticket和link获取逻辑
        
        完整的下载链接获取流程，包括ticket获取和链接获取两个步骤。
        
        :param code_id: 代码ID
        :type code_id: str
        :return: (成功标志, 下载链接, ticket)
        :rtype: Tuple[bool, Optional[str], Optional[str]]
        
        Process:
            1. 获取下载ticket（带重试）
            2. 使用ticket获取实际下载链接（最多60次重试）
            3. 返回结果
            
        note:
            - 第一步使用装饰器重试
            - 第二步使用循环重试，因为服务器可能需要时间准备文件
            - 每次重试间隔3秒
        """
        self._ensure_token()
        logger.info(f"开始获取代码下载链接: {code_id}")

        # 第一步：获取ticket（带重试机制）
        try:
            ticket = self._get_download_ticket(code_id)
            if not ticket:
                logger.error("获取ticket失败")
                return False, None, None
        except Exception as e:
            logger.error(f"获取下载ticket异常: {e}")
            return False, None, None

        # 第二步：使用ticket获取下载链接，最多重试60次
        # 服务器可能需要时间准备文件，所以需要多次重试
        link_params = {"token": self.token}
        link_url = api_qtcls_basic_code_download_link_url % ticket

        logger.info(f"使用ticket获取下载链接，最多重试60次")
        for attempt in range(60):
            try:
                link_resp = requests.get(link_url, params=link_params, timeout=10)
                refreshed_resp = self._handle_token_refresh(link_resp, link_params, link_url)
                if refreshed_resp:
                    link_resp = refreshed_resp
                elif 400 <= link_resp.status_code < 500:
                    logger.error("获取下载链接失败：token无效")
                    return False, None, ticket

                if link_resp.status_code == 200:
                    download_url = link_resp.json().get("link")
                    if download_url:
                        logger.info(f"成功获取下载链接: {download_url}")
                        return True, download_url, ticket

                # 如果没有获取到链接，等待3秒后重试
                if attempt < 59:  # 避免最后一次重试时的无意义等待
                    logger.debug(f"第{attempt + 1}次尝试未获取到链接，3秒后重试")
                    time.sleep(3)

            except Exception as e:
                logger.error(f"获取下载链接失败:{link_url} (尝试 {attempt + 1}/60): {e}")
                if attempt < 59:
                    time.sleep(3)

        logger.error("获取下载链接失败：已达到最大重试次数")
        return False, None, ticket

    def download_basic_code(self, code_id):
        """
        下载基础代码
        
        完整的代码下载流程，包括链接获取、文件下载、解压等步骤。
        
        :param code_id: 代码ID
        :type code_id: str
        :return: (成功标志, 框架路径)
        :rtype: Tuple[bool, Optional[Path]]
        
        Process:
            1. 获取下载链接
            2. 解析文件名和目标路径
            3. 检查是否已存在
            4. 下载并解压文件
            5. 返回结果
            
        note:
            - 如果目标路径已存在，会跳过下载
            - 使用ticket从文件名中提取框架名称
            - 下载失败时返回None路径
        """
        logger.info(f"开始下载基础代码: {code_id}")

        # 获取下载链接
        success, download_url, ticket = self.get_download_url_for_code(code_id)
        if not success or not download_url:
            logger.error("获取下载链接失败，无法继续下载")
            return False, None

        # 解析文件名和目标路径
        filename = download_url.split("/")[-1].split('?')[0]  # "b8c225ccb4_select-stock-pro-dev.zip"
        base_name = os.path.splitext(filename)[0]  # "b8c225ccb4_select-stock-pro-dev"
        folder_name = base_name.replace(f"{ticket}_", "")  # "select-stock-pro-dev"
        framework_path = (FRAMEWORK_ROOT_PATH / folder_name)

        logger.info(f"目标路径: {framework_path}")

        # 检查是否已存在
        if framework_path.exists():
            logger.warning(f'框架已存在，跳过下载: {framework_path}')
            return True, framework_path

        # 确保临时目录存在
        TMP_PATH.mkdir(parents=True, exist_ok=True)

        # 执行下载
        logger.info(f"开始下载文件: {filename}")
        success = _download_file_zip(download_url, TMP_PATH / filename, framework_path)

        if success:
            logger.info(f"基础代码下载成功: {framework_path}")
            return True, framework_path
        else:
            logger.error("基础代码下载失败")
            return False, None
