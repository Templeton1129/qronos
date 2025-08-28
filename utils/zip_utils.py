import os
import zipfile
import shutil
from pathlib import Path
from typing import List, Dict, Tuple, Optional

from utils.constant import TMP_PATH
from utils.log_kit import get_logger

logger = get_logger()

# ZIP安全限制
MAX_EXTRACT_SIZE = 100 * 1024 * 1024  # 100MB
MAX_FILES_COUNT = 10000
ALLOWED_EXTENSIONS = {'.json', '.py', '.pkl', '.csv', '.txt', '.log'}


def is_safe_path(path: str, base_path: str) -> bool:
    """
    检查路径是否安全，防止路径遍历攻击
    
    Args:
        path: 要检查的路径
        base_path: 基础路径
        
    Returns:
        bool: 路径是否安全
    """
    try:
        # 获取规范化的绝对路径
        abs_path = os.path.abspath(os.path.join(base_path, path))
        abs_base = os.path.abspath(base_path)
        
        # 检查路径是否在基础路径内
        return abs_path.startswith(abs_base)
    except Exception as e:
        logger.error(f"路径安全检查失败: {e}")
        return False


def validate_zip_content(zip_path: Path) -> Tuple[bool, str, Dict]:
    """
    验证ZIP文件内容的安全性和完整性
    
    Args:
        zip_path: ZIP文件路径
        
    Returns:
        tuple: (是否有效, 错误信息, 文件信息)
    """
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_file:
            file_list = zip_file.infolist()
            
            # 检查文件数量
            if len(file_list) > MAX_FILES_COUNT:
                return False, f"ZIP文件包含太多文件: {len(file_list)} > {MAX_FILES_COUNT}", {}
            
            total_size = 0
            file_info = {
                'files': [],
                'total_files': len(file_list),
                'total_size': 0
            }
            
            for file_info_item in file_list:
                # 检查文件名安全性
                if not is_safe_path(file_info_item.filename, '/'):
                    return False, f"不安全的文件路径: {file_info_item.filename}", {}
                
                # 检查文件扩展名
                file_ext = Path(file_info_item.filename).suffix.lower()
                if file_ext and file_ext not in ALLOWED_EXTENSIONS:
                    return False, f"不允许的文件类型: {file_ext}", {}
                
                # 检查文件大小
                file_size = file_info_item.file_size
                total_size += file_size
                
                if total_size > MAX_EXTRACT_SIZE:
                    return False, f"ZIP文件过大: {total_size} > {MAX_EXTRACT_SIZE}", {}
                
                file_info['files'].append({
                    'filename': file_info_item.filename,
                    'size': file_size,
                    'compressed_size': file_info_item.compress_size
                })
            
            file_info['total_size'] = total_size
            return True, "", file_info
            
    except zipfile.BadZipFile:
        return False, "无效的ZIP文件", {}
    except Exception as e:
        return False, f"ZIP文件验证失败: {str(e)}", {}


def create_zip_archive(source_paths: List[Path], output_path: Path, 
                      base_path: Optional[Path] = None) -> Tuple[bool, str]:
    """
    创建ZIP归档文件
    
    Args:
        source_paths: 要压缩的文件/目录路径列表
        output_path: 输出ZIP文件路径
        base_path: 基础路径，用于计算相对路径
        
    Returns:
        tuple: (是否成功, 错误信息)
    """
    try:
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for source_path in source_paths:
                if not source_path.exists():
                    logger.warning(f"路径不存在，跳过: {source_path}")
                    continue
                
                if source_path.is_file():
                    # 计算在ZIP中的相对路径
                    if base_path:
                        try:
                            arcname = source_path.relative_to(base_path)
                        except ValueError:
                            # 如果无法计算相对路径，使用文件名
                            arcname = source_path.name
                    else:
                        arcname = source_path.name
                    
                    zip_file.write(source_path, arcname)
                    logger.debug(f"已添加文件到ZIP: {source_path} -> {arcname}")
                    
                elif source_path.is_dir():
                    # 递归添加目录下的所有文件
                    for file_path in source_path.rglob('*'):
                        if file_path.is_file():
                            # 计算相对路径
                            if base_path:
                                try:
                                    arcname = file_path.relative_to(base_path)
                                except ValueError:
                                    arcname = file_path.relative_to(source_path.parent)
                            else:
                                arcname = file_path.relative_to(source_path.parent)
                            
                            zip_file.write(file_path, arcname)
                            logger.debug(f"已添加文件到ZIP: {file_path} -> {arcname}")
        
        logger.info(f"ZIP归档创建成功: {output_path}")
        return True, ""
        
    except Exception as e:
        logger.error(f"创建ZIP归档失败: {e}")
        return False, str(e)


def extract_zip_archive(zip_path: Path, extract_to: Path, 
                       safe_mode: bool = True) -> Tuple[bool, str, List[str]]:
    """
    解压ZIP归档文件
    
    Args:
        zip_path: ZIP文件路径
        extract_to: 解压目标目录
        safe_mode: 是否启用安全模式
        
    Returns:
        tuple: (是否成功, 错误信息, 解压的文件列表)
    """
    extracted_files = []
    
    try:
        # 安全验证
        if safe_mode:
            is_valid, error_msg, _ = validate_zip_content(zip_path)
            if not is_valid:
                return False, error_msg, []
        
        # 确保解压目录存在
        extract_to.mkdir(parents=True, exist_ok=True)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_file:
            for member in zip_file.infolist():
                # 安全路径检查
                if safe_mode and not is_safe_path(member.filename, str(extract_to)):
                    logger.warning(f"跳过不安全的路径: {member.filename}")
                    continue
                
                # 解压文件
                zip_file.extract(member, extract_to)
                extracted_files.append(member.filename)
                logger.debug(f"已解压文件: {member.filename}")
        
        logger.info(f"ZIP文件解压成功: {zip_path} -> {extract_to}")
        return True, "", extracted_files
        
    except Exception as e:
        logger.error(f"解压ZIP文件失败: {e}")
        return False, str(e), extracted_files


def create_temp_directory(prefix: str = "qronos_temp_") -> Path:
    """
    创建临时目录
    
    Args:
        prefix: 目录名前缀
        
    Returns:
        Path: 临时目录路径
    """
    temp_dir = TMP_PATH / prefix
    temp_dir.mkdir(parents=True, exist_ok=True)
    logger.debug(f"创建临时目录: {temp_dir}")
    return temp_dir


def cleanup_temp_directory(temp_dir: Path) -> bool:
    """
    清理临时目录
    
    Args:
        temp_dir: 临时目录路径
        
    Returns:
        bool: 是否清理成功
    """
    try:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
            logger.debug(f"已清理临时目录: {temp_dir}")
            return True
        return True
    except Exception as e:
        logger.error(f"清理临时目录失败: {e}")
        return False


def get_file_size_human_readable(size_bytes: int) -> str:
    """
    将文件大小转换为人类可读格式
    
    Args:
        size_bytes: 字节大小
        
    Returns:
        str: 人类可读的大小字符串
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def calculate_directory_size(directory: Path) -> int:
    """
    计算目录总大小
    
    Args:
        directory: 目录路径
        
    Returns:
        int: 目录大小（字节）
    """
    total_size = 0
    try:
        for file_path in directory.rglob('*'):
            if file_path.is_file():
                total_size += file_path.stat().st_size
    except Exception as e:
        logger.error(f"计算目录大小失败: {e}")
    return total_size


def copy_directory_with_filter(
    source: Path, 
    target: Path, 
    exclude_dirs: Optional[List[str]] = None,
    include_only_dirs: Optional[List[str]] = None
) -> int:
    """
    带过滤条件的目录复制
    
    Args:
        source: 源目录路径
        target: 目标目录路径  
        exclude_dirs: 需要排除的目录名列表（如 ["__pycache__"]）
        include_only_dirs: 只包含的目录名列表（如 ["账户信息"]）
        
    Returns:
        int: 复制的文件数量
    """
    if exclude_dirs is None:
        exclude_dirs = []
    if include_only_dirs is None:
        include_only_dirs = []
    
    copied_files = 0
    
    try:
        # 确保目标目录存在
        target.mkdir(parents=True, exist_ok=True)
        
        # 遍历源目录中的所有项目
        for item in source.iterdir():
            item_name = item.name
            target_item = target / item_name
            
            if item.is_file():
                # 复制文件
                shutil.copy2(item, target_item)
                copied_files += 1
                logger.debug(f"已复制文件: {item.name}")
                
            elif item.is_dir():
                # 检查目录过滤条件
                should_skip = False
                
                # 检查排除列表
                if item_name in exclude_dirs:
                    logger.debug(f"跳过排除目录: {item_name}")
                    should_skip = True
                
                # 检查只包含列表
                if include_only_dirs and item_name not in include_only_dirs:
                    logger.debug(f"跳过非包含目录: {item_name}")
                    should_skip = True
                
                if not should_skip:
                    # 递归复制子目录
                    sub_copied = copy_directory_with_filter(
                        item, 
                        target_item, 
                        exclude_dirs=exclude_dirs,
                        include_only_dirs=None  # 子目录不再应用include_only_dirs限制
                    )
                    copied_files += sub_copied
                    logger.debug(f"已复制目录: {item_name} ({sub_copied} 个文件)")
        
        logger.debug(f"目录复制完成: {source.name} -> {target.name} ({copied_files} 个文件)")
        
    except Exception as e:
        logger.error(f"目录复制失败: {source} -> {target}: {e}")
        
    return copied_files


def cleanup_zip_files_by_count(zip_dir: Optional[Path] = None, max_count: int = 30) -> Tuple[int, int, List[str]]:
    """
    按数量清理ZIP文件，保留最新的指定数量
    
    Args:
        zip_dir: ZIP文件目录（默认使用TMP_PATH）
        max_count: 最大保留文件数量（默认30）
        
    Returns:
        tuple: (总文件数, 删除文件数, 删除的文件列表)
    """
    if zip_dir is None:
        zip_dir = TMP_PATH
    
    deleted_files = []
    total_files = 0
    deleted_count = 0
    
    try:
        # 检查目录是否存在
        if not zip_dir.exists():
            logger.warning(f"目录不存在，无需清理: {zip_dir}")
            return 0, 0, []
        
        # 获取所有ZIP文件
        zip_files = []
        for item in zip_dir.iterdir():
            if item.is_file() and item.suffix.lower() == '.zip':
                try:
                    # 获取文件统计信息
                    stat_info = item.stat()
                    zip_files.append((item, stat_info.st_mtime))
                except Exception as e:
                    logger.warning(f"获取文件信息失败，跳过: {item} - {e}")
                    continue
        
        total_files = len(zip_files)
        
        if total_files == 0:
            logger.info("未找到ZIP文件，无需清理")
            return 0, 0, []
        
        if total_files <= max_count:
            logger.info(f"ZIP文件数量({total_files})未超过限制({max_count})，无需清理")
            return total_files, 0, []
        
        # 按修改时间降序排序（最新的在前）
        zip_files.sort(key=lambda x: x[1], reverse=True)
        
        # 保留前max_count个文件，删除剩余的
        files_to_delete = zip_files[max_count:]
        
        for file_path, _ in files_to_delete:
            try:
                file_path.unlink(missing_ok=True)
                deleted_files.append(file_path.name)
                deleted_count += 1
                logger.debug(f"已删除ZIP文件: {file_path.name}")
            except Exception as e:
                logger.error(f"删除ZIP文件失败: {file_path.name} - {e}")
                continue
        
        logger.info(f"ZIP文件清理完成: 总数={total_files}, 保留={max_count}, 删除={deleted_count}")
        if deleted_files:
            logger.info(f"删除的文件: {deleted_files[:5]}{'...' if len(deleted_files) > 5 else ''}")
    
    except Exception as e:
        logger.error(f"ZIP文件清理过程中发生错误: {e}")
        
    return total_files, deleted_count, deleted_files
