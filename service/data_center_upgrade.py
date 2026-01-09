"""
数据中心升级服务模块

该模块提供数据中心升级所需的核心功能，包括：
1. PM2进程管理操作
2. 框架配置更新
3. 数据迁移操作
4. 升级主流程协调

主要特性：
- 统一的PM2操作封装
- 批量框架配置更新
- 安全的数据迁移机制
- 完善的错误处理和日志记录

"""

import json
import shutil
import subprocess
from pathlib import Path
from typing import List, Tuple

from db.db_ops import (
    get_finished_data_center_status, get_all_finished_framework_status,
    get_framework_status, clean_old_data_center_records
)
from service.command import get_pm2_list, get_pm2_env
from service.xbx_api import XbxAPI
from utils.constant import DATA_CENTER_TYPE
from utils.log_kit import get_logger

# 初始化日志记录器
logger = get_logger()


def stop_framework_pm2(framework_id: str) -> bool:
    """
    停止指定框架的PM2进程
    
    :param framework_id: 框架ID
    :type framework_id: str
    :return: 操作成功返回True，失败返回False
    :rtype: bool
    """
    logger.info(f"停止框架PM2进程: {framework_id}")
    
    try:
        # 执行PM2停止命令
        command = f"pm2 stop {framework_id}"
        logger.debug(f"执行PM2命令: {command}")
        
        subprocess.Popen(command, env=get_pm2_env(), shell=True)
        logger.info(f"PM2停止命令已执行: {framework_id}")
        return True
        
    except Exception as e:
        logger.error(f"停止框架PM2进程失败 {framework_id}: {e}")
        return False


def start_framework_pm2(framework_id: str) -> bool:
    """
    启动指定框架的PM2进程
    
    :param framework_id: 框架ID
    :type framework_id: str
    :return: 操作成功返回True，失败返回False
    :rtype: bool
    """
    logger.info(f"启动框架PM2进程: {framework_id}")
    
    try:
        framework_status = get_framework_status(framework_id)
        if not framework_status or not framework_status.path:
            logger.error(f"框架状态异常或路径为空: {framework_id}")
            return False
        
        # 检查PM2进程列表
        pm2_processes = get_pm2_list()
        framework_running = any(item['framework_id'] == framework_id for item in pm2_processes)
        
        if not framework_running:
            # 进程不存在，使用startup.json启动
            startup_config = Path(framework_status.path) / 'startup.json'
            if not startup_config.exists():
                logger.error(f"启动配置文件不存在: {startup_config}")
                return False
            
            logger.info(f"使用配置文件启动PM2: {startup_config}")
            
            try:
                result = subprocess.run(f"pm2 start {startup_config}", env=get_pm2_env(),
                                       shell=True, capture_output=True, text=True, timeout=30)
                logger.info(f'PM2启动结果: {result.stdout}')
                if result.stderr:
                    logger.warning(f'PM2启动警告: {result.stderr}')
                
                # 保存PM2配置
                subprocess.Popen(f"pm2 save -f", env=get_pm2_env(), shell=True)
                logger.info(f"框架已启动: {framework_id}")
                return True
                
            except subprocess.TimeoutExpired:
                logger.error(f'PM2启动超时: {framework_id}')
                return False
            except Exception as e:
                logger.error(f'PM2启动异常 {framework_id}: {e}')
                return False
        else:
            # 进程存在，执行start命令
            command = f"pm2 start {framework_id}"
            logger.info(f"执行PM2命令: {command}")
            subprocess.Popen(command, env=get_pm2_env(), shell=True)
            logger.info(f"PM2启动命令已执行: {framework_id}")
            subprocess.Popen(f"pm2 save -f", env=get_pm2_env(), shell=True)
            return True
            
    except Exception as e:
        logger.error(f"启动框架PM2进程失败 {framework_id}: {e}")
        return False


def get_running_strategy_frameworks(filter_framework_id: str) -> List[str]:
    """
    获取当前运行中的实盘框架ID列表
    
    :return: 运行中的框架ID列表
    :rtype: List[str]
    """
    logger.info("获取运行中的实盘框架列表")
    
    try:
        pm2_processes = get_pm2_list()
        running_frameworks = []
        
        for process in pm2_processes:
            framework_id = process.get('framework_id')
            # 过滤掉数据中心框架
            if framework_id and framework_id != filter_framework_id:
                running_frameworks.append(framework_id)
        
        logger.info(f"找到运行中的实盘框架: {running_frameworks}")
        return running_frameworks
        
    except Exception as e:
        logger.error(f"获取运行中框架列表失败: {e}")
        return []


def update_framework_data_path(framework_id: str, new_data_path: str) -> bool:
    """
    更新指定框架的数据路径配置
    
    :param framework_id: 框架ID
    :type framework_id: str
    :param new_data_path: 新的数据路径
    :type new_data_path: str
    :return: 更新成功返回True，失败返回False
    :rtype: bool
    """
    logger.info(f"更新框架数据路径: {framework_id} -> {new_data_path}")
    
    try:
        # 获取框架状态
        framework_status = get_framework_status(framework_id)
        if not framework_status or not framework_status.path:
            logger.error(f"框架状态异常或路径为空: {framework_id}")
            return False
        
        # 读取配置文件
        config_json_path = Path(framework_status.path) / 'config.json'
        if not config_json_path.exists():
            logger.warning(f"配置文件不存在，跳过更新: {config_json_path}")
            return True  # 配置文件不存在不算失败
        
        # 读取并更新配置
        config_data = json.loads(config_json_path.read_text(encoding='utf-8'))
        old_data_path = config_data.get('realtime_data_path', '')
        config_data['realtime_data_path'] = new_data_path
        
        # 保存配置文件
        config_json_path.write_text(
            json.dumps(config_data, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
        
        logger.info(f"框架配置已更新: {framework_id}, 数据路径: {old_data_path} -> {new_data_path}")
        return True
        
    except Exception as e:
        logger.error(f"更新框架数据路径失败 {framework_id}: {e}")
        return False


def migrate_data_center_data(source_path: str, target_path: str) -> bool:
    """
    迁移数据中心的数据和配置
    
    使用move操作将数据从旧数据中心迁移到新数据中心，减少磁盘IO压力。
    
    :param source_path: 源数据中心路径
    :type source_path: str
    :param target_path: 目标数据中心路径
    :type target_path: str
    :return: 迁移成功返回True，失败返回False
    :rtype: bool
    """
    logger.info(f"迁移数据中心数据: {source_path} -> {target_path}")
    
    try:
        source_path_obj = Path(source_path)
        target_path_obj = Path(target_path)
        
        if not source_path_obj.exists():
            logger.error(f"源数据中心路径不存在: {source_path}")
            return False
        
        if not target_path_obj.exists():
            logger.error(f"目标数据中心路径不存在: {target_path}")
            return False
        
        # 迁移data目录
        source_data_dir = source_path_obj / 'data'
        target_data_dir = target_path_obj / 'data'
        
        if source_data_dir.exists():
            # # 检查源data目录大小
            # try:
            #     import os
            #     total_size = sum(
            #         os.path.getsize(os.path.join(dirpath, filename))
            #         for dirpath, dirnames, filenames in os.walk(source_data_dir)
            #         for filename in filenames
            #     )
            #     logger.info(f"源data目录大小: {total_size / (1024**3):.2f} GB")
            # except Exception as e:
            #     logger.warning(f"计算目录大小失败: {e}")
            #
            # 如果目标data目录已存在，先删除
            if target_data_dir.exists():
                logger.warning(f"目标data目录已存在，将被覆盖: {target_data_dir}")
                shutil.rmtree(target_data_dir)
            
            # 移动整个data目录
            logger.info(f"开始移动data目录: {source_data_dir} -> {target_data_dir}")
            shutil.move(str(source_data_dir), str(target_data_dir))
            logger.info(f"已移动data目录: {source_data_dir} -> {target_data_dir}")
        else:
            logger.warning(f"源data目录不存在，跳过迁移: {source_data_dir}")
        
        # 复制config.json文件（保留原文件）
        source_config = source_path_obj / 'config.json'
        target_config = target_path_obj / 'config.json'
        
        if source_config.exists():
            shutil.copy2(source_config, target_config)
            logger.info(f"已复制配置文件: {source_config} -> {target_config}")
        else:
            logger.warning(f"源配置文件不存在，跳过复制: {source_config}")
        
        logger.info("数据中心数据迁移完成")
        return True
        
    except Exception as e:
        logger.error(f"迁移数据中心数据失败: {e}")
        return False


def upgrade_data_center() -> Tuple[bool, str]:
    """
    数据中心升级主流程
    
    :return: (升级成功标志, 结果消息)
    :rtype: Tuple[bool, str]
    """
    logger.info("开始数据中心升级流程")
    
    try:
        # 步骤1：预检查和清理旧记录
        logger.info("步骤1：预检查和清理旧记录")
        
        # 获取当前数据中心状态
        old_data_center = get_finished_data_center_status()
        if not old_data_center or not old_data_center.path:
            return False, "当前数据中心状态异常，无法升级"
        
        old_data_center_path = old_data_center.path
        old_data_center_time = old_data_center.time
        logger.info(f"当前数据中心: 路径={old_data_center_path}, 时间={old_data_center_time}")

        # 步骤2：下载最新数据中心
        logger.info("步骤2：下载最新数据中心")
        api = XbxAPI.get_instance()
        api.download_data_center_latest()

        # 清理旧的数据中心记录
        cleaned_count = clean_old_data_center_records()
        if cleaned_count > 0:
            logger.info(f"已清理 {cleaned_count} 条旧数据中心记录")

        # 获取新下载的数据中心状态
        new_data_center = get_finished_data_center_status()
        if not new_data_center or not new_data_center.path:
            return False, "下载最新数据中心失败"
        
        new_data_center_path = new_data_center.path
        new_data_center_time = new_data_center.time
        logger.info(f"新数据中心: 路径={new_data_center_path}, 时间={new_data_center_time}")
        
        # 使用时间戳比较版本，如果时间相同说明已是最新版本
        if old_data_center_time == new_data_center_time:
            logger.info("数据中心已是最新版本，无需升级")
            return True, "数据中心已是最新版本"
        
        # 检查时间戳确保新版本更新
        if new_data_center_time <= old_data_center_time:
            logger.warning(f"新版本时间戳不新于当前版本: 新={new_data_center_time}, 旧={old_data_center_time}")
            return True, "数据中心已是最新版本"
        
        # 步骤3：停止相关服务
        logger.info("步骤3：停止相关服务")
        
        # 获取运行中的实盘框架
        running_frameworks = get_running_strategy_frameworks(old_data_center.framework_id)
        logger.info(f"运行中的实盘框架: {running_frameworks}")
        
        # 停止数据中心
        if not stop_framework_pm2(old_data_center.framework_id):
            return False, "停止数据中心服务失败"
        
        # 停止所有实盘框架
        for framework_id in running_frameworks:
            if not stop_framework_pm2(framework_id):
                logger.warning(f"停止实盘框架失败: {framework_id}")
        
        logger.info("相关服务已停止")
        
        # 步骤4：更新实盘框架配置
        logger.info("步骤4：更新实盘框架配置")
        
        # 获取所有已完成的非数据中心框架
        all_frameworks = get_all_finished_framework_status()
        strategy_frameworks = [fw for fw in all_frameworks if fw.type != DATA_CENTER_TYPE]

        new_data_path = str(Path(new_data_center_path) / 'data')
        logger.info(f"新数据路径: {new_data_path}")
        
        for framework in strategy_frameworks:
            if not update_framework_data_path(framework.framework_id, new_data_path):
                logger.warning(f"更新框架配置失败: {framework.framework_id}")
        
        logger.info("实盘框架配置更新完成")
        
        # 步骤5：迁移数据
        logger.info("步骤5：迁移数据")
        
        if not migrate_data_center_data(old_data_center_path, new_data_center_path):
            return False, "数据迁移失败"
        
        # 注意：migrate_data_center_data已经使用move操作移动了data目录，无需手动删除
        logger.info("数据迁移完成")
        
        # 步骤6：重启服务
        logger.info("步骤6：重启服务")
        
        # 启动新数据中心
        if not start_framework_pm2(new_data_center.framework_id):
            return False, "重启数据中心服务出错"
        
        # 启动之前运行的实盘框架
        failed_frameworks = []
        for framework_id in running_frameworks:
            if not start_framework_pm2(framework_id):
                failed_frameworks.append(framework_id)
        
        if failed_frameworks:
            return False, f"重启实盘框架服务出错: {failed_frameworks}"
        
        logger.info("服务重启完成")
        logger.info("数据中心升级流程完成")
        
        return True, "数据中心升级成功"
        
    except Exception as e:
        logger.error(f"数据中心升级流程异常: {e}")
        return False, f"升级流程异常: {str(e)}"
