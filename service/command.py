"""
命令执行模块

该模块提供系统命令执行功能，主要用于：
1. PM2进程管理操作
2. Python环境路径获取
3. PM2配置文件生成

Docker环境适配：
- 原本使用conda Alpha环境，现在使用容器内的/opt/alpha_env虚拟环境
- 确保与Docker容器内的环境配置保持一致

Author: 项目团队
Date: 2024
Version: 1.0
"""

import json
import os
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

from model.model import Pm2AppModel, Pm2CfgModel
from utils.constant import CONDA_ENV_NAME, ALPHA_ENV_PATH
from utils.log_kit import get_logger

# 初始化日志记录器
logger = get_logger()

def get_pm2_list() -> List[Dict[str, Any]]:
    """
    获取PM2进程列表
    
    查询所有PM2管理的进程信息，过滤出用户创建的进程（排除default命名空间）。
    
    :return: PM2进程信息列表
    :rtype: List[Dict[str, Any]]
    
    返回格式::
    
        [
            {
                "pm_id": 0,
                "name": "framework_startup",
                "framework_id": "xxx",
                "status": "online"
            },
            ...
        ]
        
    Note:
        - 自动排除default命名空间的进程
        - 超时时间为30秒
        - 发生异常时返回空列表
    """
    logger.info("获取PM2进程列表")

    try:
        # 执行PM2命令获取JSON格式的进程列表
        result = subprocess.run(
            ["pm2", "jlist"],
            env=get_pm2_env(),
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            logger.error(f"PM2命令执行失败: {result.stderr}")
            return []

        # 解析JSON输出
        pm2_data = json.loads(result.stdout.split("\n")[-1])
        logger.debug(f"PM2原始数据包含{len(pm2_data)}个进程")

        # 过滤并格式化数据
        data = []
        for item in pm2_data:
            # 跳过default命名空间的进程
            if item.get('pm2_env', {}).get('namespace') == 'default':
                continue

            formatted_item = {
                'pm_id': item.get('pm_id'),
                'name': item.get('name'),
                'framework_id': item.get('pm2_env', {}).get('namespace'),
                'status': item.get('pm2_env', {}).get('status'),
                'restart_time': item.get('pm2_env', {}).get('restart_time'),  # 重启次数
                'mem_usage': f'{round(item["monit"]["memory"] / (1024 ** 2), 2)}MB',  # 内存使用
                'cpu_usage': f'{item["monit"]["cpu"]}%',  # cpu使用
                'pm_uptime': item["pm2_env"]["pm_uptime"],  # 启动时间
            }
            data.append(formatted_item)

        logger.info(f"成功获取PM2进程列表，共{len(data)}个用户进程")
        return data

    except subprocess.TimeoutExpired:
        logger.error("PM2命令执行超时")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"PM2输出JSON解析失败: {e}")
        return []
    except Exception as e:
        logger.error(f"获取PM2进程列表失败: {e}")
        return []


def del_pm2(framework_id: str) -> bool:
    """
    删除PM2进程
    
    根据框架ID删除对应的PM2进程。
    
    :param framework_id: 框架ID，用作PM2的命名空间
    :type framework_id: str
    :return: 删除成功返回True，失败返回False
    :rtype: bool
    
    Note:
        - 使用异步方式执行，不等待结果
        - 即使删除失败也不会抛出异常
        - 删除的是整个命名空间下的所有进程
    """
    logger.info(f"删除PM2进程: {framework_id}")

    try:
        # 使用Popen异步执行删除命令
        subprocess.Popen(["pm2", "del", str(framework_id)], env=get_pm2_env())
        logger.info(f"PM2删除命令已执行: {framework_id}")
        return True

    except Exception as e:
        logger.error(f"删除PM2进程失败 {framework_id}: {e}")
        return False


def get_conda_env(env_name: str = 'Alpha') -> str:
    """
    获取conda环境的Python解释器路径
    
    在Docker环境中，该函数被重构为返回容器内的虚拟环境路径。
    保留原函数签名以保持兼容性。
    
    :param env_name: 环境名称（Docker环境中忽略此参数）
    :type env_name: str
    :return: Python解释器路径
    :rtype: str
    
    Note:
        - Docker环境：直接返回/opt/alpha_env/bin/python
        - 传统环境：查找conda环境路径
        - 如果找不到环境，返回系统默认python
    """
    logger.debug(f"获取Python环境路径，环境名: {env_name}")

    # Docker环境中直接返回预配置的虚拟环境路径
    if Path(ALPHA_ENV_PATH).exists():
        logger.info(f"使用Docker容器内的Python环境: {ALPHA_ENV_PATH}")
        return ALPHA_ENV_PATH

    # 兼容性：如果不在Docker环境中，尝试查找conda环境
    try:
        logger.debug("尝试查找conda环境...")
        result = subprocess.run(
            ["conda", "env", "list"],
            capture_output=True,
            text=True,
            timeout=30
        )

        # 解析conda环境列表输出
        for line in result.stdout.splitlines():
            if env_name in line and not line.startswith("#"):
                # 提取环境路径
                path_parts = line.split()
                if len(path_parts) >= 2:
                    env_path = f"{path_parts[-1]}/bin/python"
                    logger.info(f"找到conda环境: {env_path}")
                    return env_path

        logger.warning(f"未找到conda环境 {env_name}，使用系统默认python")
        return 'python'

    except subprocess.TimeoutExpired:
        logger.error("conda命令执行超时")
        return 'python'
    except Exception as e:
        logger.error(f"获取conda环境失败: {e}")
        return 'python'


def get_pm2_env() -> dict:
    # shell=False 时 env 会完全替换子进程环境，需要显式带上 PATH 让系统找到 pm2
    # 除此之外保持最小化，避免 Python 进程的环境变量干扰 PM2 行为（如 namespace 丢失）
    env = {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
    }

    # 1. 检查环境变量(容器内)
    if env_home := os.environ.get('PM2_HOME'):
        env["PM2_HOME"] = env_home
        return env

    # 2. 尝试通过进程检查(调试)
    try:
        result = subprocess.run(
            ["pm2", "info", "pm2-logrotate"],
            env=env,
            capture_output=True,
            text=True
        )

        for line in result.stdout.split('\n'):
            if "exec cwd" in line:
                parts = line.split('│')
                if len(parts) > 2:
                    cwd = parts[2].strip().split('/modules')[0]
                    env["PM2_HOME"] = cwd
                    return env
    except:
        pass
    env["PM2_HOME"] = os.path.expanduser('~/.pm2')
    return env


def create_pm2_cfg(app_name: str = 'startup', framework_id: str = '',
                   framework_path: Optional[Path] = None) -> Pm2AppModel:
    """
    创建PM2配置模型
    
    为指定的应用和框架生成PM2进程配置。
    
    :param app_name: 应用名称（启动脚本名）
    :type app_name: str
    :param framework_id: 框架唯一标识符
    :type framework_id: str
    :param framework_path: 框架本地路径
    :type framework_path: Optional[Path]
    :return: PM2配置模型对象
    :rtype: Pm2AppModel
    
    配置包含内容：
        - 进程名称：{框架名}_{应用名}
        - 命名空间：框架ID
        - 启动脚本：{框架路径}/{应用名}.py
        - Python解释器：容器内的alpha_env环境
        - 日志文件：{框架路径}/logs/目录下
        
    Example:
        config = create_pm2_cfg('startup', 'framework_123', Path('/app/firm/strategy'))
        # 生成配置用于启动 strategy_startup 进程
    """
    logger.info(f"创建PM2配置: 应用={app_name}, 框架={framework_id}")

    if not framework_path:
        logger.warning("框架路径为空，可能导致配置错误")
        framework_path = Path('.')

    # 确保日志目录存在
    log_dir = framework_path / 'logs'
    log_dir.mkdir(exist_ok=True)
    logger.debug(f"日志目录: {log_dir}")

    # 获取Python解释器路径
    python_path = get_conda_env(CONDA_ENV_NAME)
    logger.debug(f"使用Python解释器: {python_path}")

    # 生成PM2配置
    config = Pm2AppModel(
        name=f'{framework_path.name}_{app_name}',
        namespace=framework_id,
        script=str(framework_path / f'{app_name}.py'),
        exec_interpreter=python_path,
        out_file=str(log_dir / f'{app_name}.out.log'),
        error_file=str(log_dir / f'{app_name}.error.log'),
    )

    logger.info(f"PM2配置创建完成: {config.name}")
    logger.debug(f"配置详情: 脚本={config.script}, 解释器={config.exec_interpreter}")

    return config


def write_pm2_startup_json(
    framework_id: str, framework_path: Path, app_names
) -> Path:
    """
    为指定框架生成 PM2 startup.json 配置文件

    供下载流程（service/xbx_api.py）和导入流程（service/basic_code.py）共同调用，
    消除了两处重复生成 startup.json 的代码。

    :param framework_id: 框架唯一标识，写入 PM2 config 的 namespace 字段
    :type framework_id: str
    :param framework_path: 框架本地根目录，startup.json 会被写入此目录
    :type framework_path: Path
    :param app_names: 要生成的 app 名字列表（例如 ['startup', 'delist', 'monitor']）
    :type app_names: Sequence[str]
    :return: 已写入的 startup.json 文件路径
    :rtype: Path

    Note:
        - 内部调用现有的 create_pm2_cfg() 生成每个 app 的配置
        - 写出的文件名固定为 'startup.json'（与现有约定一致）
        - 覆盖写入，不做备份
    """
    logger.info(f"生成 PM2 startup.json: 框架={framework_id}, app_names={app_names}")

    pm2_cfg = Pm2CfgModel(apps=[
        create_pm2_cfg(app_name=app_name, framework_id=framework_id, framework_path=framework_path)
        for app_name in app_names
    ])

    config_path = framework_path / 'startup.json'
    config_path.write_text(json.dumps(pm2_cfg.model_dump(), ensure_ascii=False, indent=2))

    logger.info(f"PM2 startup.json 已保存: {config_path}")
    return config_path
