import ast
import json
import shutil
import traceback
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Tuple, Dict, Optional

import pandas as pd

from utils.constant import TMP_PATH
from utils.log_kit import get_logger
from utils.zip_utils import (
    create_zip_archive, extract_zip_archive, create_temp_directory, cleanup_temp_directory, calculate_directory_size,
    cleanup_zip_files_by_count, copy_directory_with_filter
)

logger = get_logger()


def process_framework_account_statistics(framework_status, query_days: int) -> list:
    """
    处理单个框架的账户统计信息
    
    从指定框架中提取所有账户的详细统计信息，包括资金曲线、持仓数据等。
    
    Args:
        framework_status: 框架状态对象，包含框架ID、路径等信息
        query_days: 查询最近多少天
        
    Returns:
        list: 该框架下所有账户的统计信息列表
    """
    logger.info(f"处理框架账户统计: {framework_status.framework_name} ({framework_status.framework_id})")
    
    result = []
    
    if not framework_status.path:
        logger.error(f"框架未下载完成: {framework_status.framework_id}")
        return result

    account_path = Path(framework_status.path) / 'accounts'
    if not account_path.exists():
        logger.warning(f"账户目录不存在: {account_path}")
        return result

    data_path = Path(framework_status.path) / 'data'
    if not data_path.exists():
        logger.warning(f"数据目录不存在: {data_path}")
        return result

    # 获取所有有效的账户配置文件
    account_list = [
        file.stem
        for file in account_path.iterdir()
        if file.is_file() and file.suffix == ".json" and not file.name.startswith('_')
    ]
    
    logger.info(f"框架 {framework_status.framework_name} 中找到 {len(account_list)} 个账户")

    for account_name in account_list:
        try:
            # 读取账户配置
            account_json_path = account_path / f"{account_name}.json"
            account_json = json.loads(account_json_path.read_text(encoding='utf-8'))
            
            # 基础账户信息
            account_info = {
                'edit_id': framework_status.id,
                'framework_id': framework_status.framework_id,
                'framework_name': framework_status.framework_name,
                'account_name': account_name,
                'hour_offset': account_json['account_config']['hour_offset'],
                'strategy_name': account_json['strategy_name'],
                'strategy_config': account_json['strategy_config'],
                'strategy_pool': account_json['strategy_pool'],
            }
            
            # 检查账户信息目录
            account_info_path = data_path / account_name / '账户信息'
            if not account_info_path.exists():
                logger.warning(f'{account_name} 没有生成 [账户信息] 目录，该账户当前未下过单····')
                continue
            
            # 处理资金曲线数据
            equity_start_time = None
            equity_path = account_info_path / 'equity.pkl'
            if equity_path.exists():
                try:
                    df: pd.DataFrame = pd.read_pickle(equity_path)

                    # 数据裁切
                    if query_days:
                        df = df[df['time'] >= datetime.now() - pd.Timedelta(days=query_days)]

                    if df.empty:
                        account_info['equity'] = None
                    else:
                        equity_start_time = df['time'].min()
                        # 计算24小时数据
                        last_24h_df = df[df['time'] > df['time'].max() - pd.Timedelta(hours=24)]
                        _filter_24h_df = last_24h_df.loc[last_24h_df['type'] == 'log']
                        if not _filter_24h_df.empty:
                            account_info['eq_pct_24h'] = round(100 * (_filter_24h_df.iloc[-1]['账户总净值'] / _filter_24h_df.iloc[0]['账户总净值'] - 1), 2)
                            account_info['eq_pnl_24h'] = round(_filter_24h_df.iloc[-1]['账户总净值'] - _filter_24h_df.iloc[0]['账户总净值'], 2)
                            account_info['eq_max_24h'] = _filter_24h_df['账户总净值'].max()
                            account_info['eq_min_24h'] = _filter_24h_df['账户总净值'].min()

                        # 格式化资金曲线数据
                        df['time'] = df['time'].dt.strftime('%Y-%m-%d %H:%M:%S')
                        df['net'] = (df['净值'] - 1) * 100
                        df['max2here'] = df['净值'].expanding().max()
                        df['dd2here'] = (df['净值'] / df['max2here'] - 1) * 100
                        df.rename(columns={
                            '账户总净值': 'equity_amount',
                            '多头选币': 'long_coin_num', '空头选币': 'short_coin_num',
                            '多头仓位': 'long_pos_val', '空头仓位': 'short_pos_val',
                        }, inplace=True)

                        cols = ['equity_amount', 'long_pos_val', 'short_pos_val', 'long_coin_num', 'short_coin_num', 'net',
                                'max2here', 'dd2here', 'long_ratio', 'short_ratio', 'empty_ratio']
                        for col in cols:
                            if col in df.columns:
                                df[col] = df[col].round(2)

                        df_dict = df[['time', *[col for col in cols if col in df.columns]]].to_dict('list')
                        account_info['equity'] = df_dict
                    
                except Exception as e:
                    logger.error(f"处理 {account_name} 资金曲线数据失败: {e}")
            
            # 处理子策略资金曲线
            sub_stg_eqs_path = account_info_path / 'sub_stg_eqs.pkl'
            if sub_stg_eqs_path.exists() and equity_start_time:
                try:
                    account_info['sub_stg_eqs'] = {}
                    sub_stg_eqs_dict = pd.read_pickle(sub_stg_eqs_path)
                    for stg_name, df in sub_stg_eqs_dict.items():
                        # 使用布尔索引过滤数据
                        mask = df['candle_begin_time'] >= equity_start_time
                        if mask.any():
                            # 使用 .loc 直接对过滤后的数据进行操作，避免 SettingWithCopyWarning
                            df.loc[mask, 'candle_begin_time'] = df.loc[mask, 'candle_begin_time'].dt.strftime('%Y-%m-%d %H:%M:%S')
                            df.loc[mask, 'net'] = (100 * (df.loc[mask, 'equity'] / df.loc[mask, 'equity'].iloc[0] - 1)).round(2)
                            account_info['sub_stg_eqs'][stg_name] = df.loc[mask, ['candle_begin_time', 'net']].to_dict('list')
                except Exception as e:
                    logger.error(f"处理 {account_name} 子策略资金曲线失败: {e}")
            
            # 处理现货持仓数据
            pos_spot_path = account_info_path / 'pos_spot.pkl'
            if pos_spot_path.exists() and equity_start_time:
                try:
                    pos_spot = pd.read_pickle(pos_spot_path)
                    if pos_spot:
                        pos_spot_list = {}
                        for timestamp_key, df in pos_spot.items():
                            if not df.empty:
                                pos_spot_list[timestamp_key] = df.reset_index().to_dict('records')
                        account_info['pos_spot'] = pos_spot_list
                except Exception as e:
                    logger.error(f"处理 {account_name} 现货持仓数据失败: {e}")
            
            # 处理合约持仓数据
            pos_swap_path = account_info_path / 'pos_swap.pkl'
            if pos_swap_path.exists() and equity_start_time:
                try:
                    pos_swap = pd.read_pickle(pos_swap_path)
                    if pos_swap:
                        pos_swap_list = {}
                        for timestamp_key, df in pos_swap.items():
                            if not df.empty:
                                pos_swap_list[timestamp_key] = df.reset_index().to_dict('records')
                        account_info['pos_swap'] = pos_swap_list
                except Exception as e:
                    logger.error(f"处理 {account_name} 合约持仓数据失败: {e}, {traceback.format_exc()}")

            # 处理持仓盈亏数据
            pnl_history_path = account_info_path / 'pnl_history.pkl'
            if pnl_history_path.exists() and equity_start_time:
                try:
                    pnl_history = pd.read_pickle(pnl_history_path)
                    account_info['pnl_history'] = pnl_history if pnl_history else {}
                except Exception as e:
                    logger.error(f"处理  {account_name} 持仓盈亏数据失败: {e}, {traceback.format_exc()}")

            result.append(account_info)
            logger.debug(f"成功处理账户: {account_name}")
            
        except Exception as e:
            logger.error(f"处理账户 {account_name} 统计信息失败: {e}")
            continue
    
    logger.info(f"框架 {framework_status.framework_name} 处理完成，成功处理 {len(result)} 个账户")
    return result


def python_repr(obj, indent=4):
    """
    将 Python 对象转换为正确的 Python 代码字符串表示
    
    与 json.dumps() 不同，这个函数会生成正确的 Python 语法：
    - 布尔值: True/False (而不是 true/false)
    - None: None (而不是 null)
    - 字符串: 使用单引号或双引号
    - 枚举类型: 使用枚举的字符串值
    
    Args:
        obj: 要转换的 Python 对象
        indent: 缩进空格数
        
    Returns:
        str: Python 代码字符串
    """
    if obj is None:
        return 'None'
    elif isinstance(obj, bool):
        return 'True' if obj else 'False'
    elif isinstance(obj, Enum):
        # 处理枚举类型：返回枚举的字符串值
        return repr(obj.value)
    elif isinstance(obj, (int, float)):
        return str(obj)
    elif isinstance(obj, str):
        return repr(obj)
    elif isinstance(obj, list):
        if not obj:
            return '[]'
        items = [python_repr(item, indent) for item in obj]
        if len(str(obj)) < 80:  # 短列表单行显示
            return '[' + ', '.join(items) + ']'
        else:  # 长列表多行显示
            indent_str = ' ' * indent
            items_str = (',\n' + indent_str).join(items)
            return '[\n' + indent_str + items_str + '\n]'
    elif isinstance(obj, dict):
        if not obj:
            return '{}'
        items = [f'{python_repr(k, indent)}: {python_repr(v, indent)}' for k, v in obj.items()]
        if len(str(obj)) < 80:  # 短字典单行显示
            return '{' + ', '.join(items) + '}'
        else:  # 长字典多行显示
            indent_str = ' ' * indent
            items_str = (',\n' + indent_str).join(items)
            return '{\n' + indent_str + items_str + '\n}'
    else:
        # 对于其他类型，尝试使用 repr()
        return repr(obj)


def read_existing_py_file(py_path: Path):
    """
    读取现有的 Python 文件，解析其中的变量值

    Args:
        py_path: Python 文件路径

    Returns:
        dict: 解析出的变量字典
    """
    if not py_path.exists():
        return {}

    try:
        content = py_path.read_text(encoding='utf-8')
        # 使用已有的解析函数
        key_map = {
            "strategy_name": "strategy_name",
            "get_kline_num": "get_kline_num",
            "strategy_config": "strategy_config",
            "strategy_pool": "strategy_pool",
            "leverage": "leverage",
            "black_list": "black_list",
            "white_list": "white_list",
            "rebalance_mode": "rebalance_mode",
            "account_config": "account_config",
            "is_pure_long": "is_pure_long"
        }
        existing_data, _ = extract_variables_from_py(content, key_map)
        return existing_data or {}
    except Exception:
        return {}


def get_field_value(key: str, default, account_json: dict, existing_data: dict,
                    strategy_fields: list, account_fields: list):
    """
    获取字段值的工具函数

    Args:
        key: 字段名
        default: 默认值
        account_json: 账户配置 JSON
        existing_data: 现有数据
        strategy_fields: 策略相关字段列表
        account_fields: 账户相关字段列表

    Returns:
        字段值
    """
    # 策略相关字段：优先使用现有文件中的内容
    if key in strategy_fields:
        existing_value = existing_data.get(key)
        if existing_value is not None:
            return existing_value
        # 如果现有文件中没有，才使用 JSON 中的值
        json_value = account_json.get(key)
        return json_value if json_value is not None else default

    # AccountModel 字段：允许更新，但只更新非空字段
    elif key in account_fields:
        json_value = account_json.get(key)
        if json_value is not None and json_value != "":
            return json_value
        return existing_data.get(key, default)

    # 其他字段：使用默认逻辑
    else:
        json_value = account_json.get(key)
        if json_value is not None and json_value != "":
            return json_value
        return existing_data.get(key, default)


def generate_account_py_file_from_json(account_name: str, account_json: dict, accounts_dir: Path,
                                       update_mode: bool = False):
    """
    根据 account_json 生成 Python 文件（用于 basic_code_account 接口）
    
    根据 is_lock 状态管理文件名前缀：
    - is_lock=True: 生成 _用户名.py 文件（锁定账号），删除 用户名.py 文件
    - is_lock=False: 生成 用户名.py 文件（正常使用），删除 _用户名.py 文件

    Args:
        account_name: 账户名称
        account_json: 账户配置 JSON
        accounts_dir: accounts 目录路径
        update_mode: 是否为更新模式（保留已有字段）

    Returns:
        Path: 生成的 Python 文件路径
    """
    # 确保目录存在
    accounts_dir.mkdir(parents=True, exist_ok=True)

    # 根据 is_lock 状态确定文件名
    is_lock = account_json.get('is_lock', False)
    if is_lock:
        # 锁定状态：生成 _用户名.py 文件
        target_py_path = accounts_dir / f'_{account_name}.py'
        old_py_path = accounts_dir / f'{account_name}.py'
    else:
        # 正常状态：生成 用户名.py 文件
        target_py_path = accounts_dir / f'{account_name}.py'
        old_py_path = accounts_dir / f'_{account_name}.py'

    # 删除旧的文件（如果存在）
    if old_py_path.exists():
        old_py_path.unlink(missing_ok=True)
        logger.info(f"已删除旧文件: {old_py_path}")

    # 如果是更新模式，先读取现有文件（从目标文件路径读取）
    existing_data = {}
    if update_mode:
        existing_data = read_existing_py_file(target_py_path)

    # 策略相关字段：优先使用现有文件中的内容（由 config 上传产生）
    strategy_fields = ['strategy_name', 'strategy_config', 'strategy_pool', 'rebalance_mode']

    # AccountModel 相关字段：允许更新
    account_fields = ['account_config', 'get_kline_num', 'leverage', 'black_list', 'white_list', 'min_kline_num']

    # 生成 Python 文件内容
    py_content = f"""# ====================================================================================================
# ** 实盘账户配置 **
# ‼️‼️‼️账户配置，需要在accounts下的文件中做配置 ‼️‼️‼️
# 此处只是展示配置的结构，具体配置情参考 accounts 文件夹下的 _55mBTC样例.py
# 文件名就是账户名，比如 `15m大学生.py` 或者 `_55mBTC样例.py`
# ====================================================================================================
account_config = {python_repr(get_field_value('account_config', {}, account_json, existing_data, strategy_fields, account_fields))}  # 实盘账户配置

# ====================================================================================================
# ** 策略细节配置 **
# ‼️‼️‼️需要在accounts下的文件中做配置‼️‼️‼️
# 此处只是展示配置的结构，具体配置情参考 accounts 文件夹下的 _55mBTC样例.py
# ====================================================================================================
strategy_name = {python_repr(get_field_value('strategy_name', account_name, account_json, existing_data, strategy_fields, account_fields))}  # 当前账户运行策略的名称
get_kline_num = {python_repr(get_field_value('get_kline_num', 999, account_json, existing_data, strategy_fields, account_fields))}  # 获取多少根K线
min_kline_num = {python_repr(get_field_value('min_kline_num', 168, account_json, existing_data, strategy_fields, account_fields))}  # 最小k线数量
strategy_config = {python_repr(get_field_value('strategy_config', {}, account_json, existing_data, strategy_fields, account_fields))}  # 策略配置
strategy_pool = {python_repr(get_field_value('strategy_pool', [], account_json, existing_data, strategy_fields, account_fields))}  # 策略池
leverage = {python_repr(get_field_value('leverage', 1, account_json, existing_data, strategy_fields, account_fields))}  # 杠杆数
black_list = {python_repr(get_field_value('black_list', [], account_json, existing_data, strategy_fields, account_fields))}  # 拉黑名单
white_list = {python_repr(get_field_value('white_list', [], account_json, existing_data, strategy_fields, account_fields))}  # 白名单
"""

    # 添加 rebalance_mode（如果存在）
    rebalance_mode = get_field_value('rebalance_mode', None, account_json, existing_data, strategy_fields,
                                     account_fields)
    if rebalance_mode is not None:
        py_content += f"rebalance_mode = {python_repr(rebalance_mode)}  # 再平衡模式\n"

    # 写入 Python 文件
    target_py_path.write_text(py_content, encoding='utf-8')
    logger.info(f"已生成账户配置文件: {target_py_path}")
    return target_py_path


def generate_account_py_file_from_config(account_name: str, account_json: dict, extracted: dict,
                                         strategy_name_value: str, accounts_dir: Path):
    """
    根据配置文件解析结果生成 Python 文件（用于 basic_code_account_binding_strategy 接口）

    Args:
        account_name: 账户名称
        account_json: 账户配置 JSON
        extracted: 从配置文件中解析出的数据
        strategy_name_value: 策略名称
        accounts_dir: accounts 目录路径

    Returns:
        Path: 生成的 Python 文件路径
    """
    # 将 extracted 数据合并到 account_json 中
    merged_data = account_json.copy()
    merged_data.update({
        'strategy_name': strategy_name_value,
        'strategy_config': extracted.get("strategy_config"),
        'strategy_pool': extracted.get("strategy_pool"),
        'rebalance_mode': extracted.get("rebalance_mode"),
    })

    return generate_account_py_file_from_json(account_name, merged_data, accounts_dir, update_mode=False)


def ast_eval_node_with_context(node, var_context=None):
    """
    递归解析 AST 节点，支持变量上下文
    
    Args:
        node: AST 节点
        var_context: 变量上下文字典，用于替换变量引用
    
    Returns:
        解析后的值
    """
    if var_context is None:
        var_context = {}
        
    if isinstance(node, ast.Constant):
        return node.value
    elif isinstance(node, ast.Str):  # Python < 3.8 兼容
        return node.s
    elif isinstance(node, ast.Num):  # Python < 3.8 兼容
        return node.n
    elif isinstance(node, ast.List):
        return [ast_eval_node_with_context(elem, var_context) for elem in node.elts]
    elif isinstance(node, ast.Dict):
        keys = [ast_eval_node_with_context(k, var_context) if k else None for k in node.keys]
        values = [ast_eval_node_with_context(v, var_context) for v in node.values]
        return dict(zip(keys, values))
    elif isinstance(node, ast.BinOp):
        # 处理二元运算：加减乘除等
        left = ast_eval_node_with_context(node.left, var_context)
        right = ast_eval_node_with_context(node.right, var_context)
        if isinstance(node.op, ast.Add):
            return left + right
        elif isinstance(node.op, ast.Sub):
            return left - right
        elif isinstance(node.op, ast.Mult):
            return left * right
        elif isinstance(node.op, ast.Div):
            return left / right
        elif isinstance(node.op, ast.FloorDiv):
            return left // right
        elif isinstance(node.op, ast.Mod):
            return left % right
        elif isinstance(node.op, ast.Pow):
            return left ** right
    elif isinstance(node, ast.UnaryOp):
        # 处理一元运算：负号等
        operand = ast_eval_node_with_context(node.operand, var_context)
        if isinstance(node.op, ast.UAdd):
            return +operand
        elif isinstance(node.op, ast.USub):
            return -operand
    elif isinstance(node, ast.Call):
        # 处理函数调用
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name == 'dict':
                # dict() 调用
                result_dict = {}
                for keyword in node.keywords:
                    result_dict[keyword.arg] = ast_eval_node_with_context(keyword.value, var_context)
                return result_dict
            elif func_name == 'list':
                # list() 调用
                if node.args:
                    return list(ast_eval_node_with_context(node.args[0], var_context))
                return []
            elif func_name == 'range':
                # range() 调用
                args = [ast_eval_node_with_context(arg, var_context) for arg in node.args]
                return list(range(*args))
            elif func_name == 'max':
                # max() 调用
                args = [ast_eval_node_with_context(arg, var_context) for arg in node.args]
                return max(args)
            elif func_name == 'min':
                # min() 调用
                args = [ast_eval_node_with_context(arg, var_context) for arg in node.args]
                return min(args)
    elif isinstance(node, ast.Tuple):
        return tuple(ast_eval_node_with_context(elem, var_context) for elem in node.elts)
    elif isinstance(node, ast.NameConstant):  # True, False, None
        return node.value
    elif isinstance(node, ast.Name):
        # 优先使用上下文中的变量值
        if node.id in var_context:
            return var_context[node.id]
        # 对于未知变量引用，返回变量名字符串
        return f"<variable:{node.id}>"

    # 对于其他复杂表达式，尝试字面量解析
    try:
        return ast.literal_eval(node)
    except:
        # 如果还是无法解析，尝试执行代码（安全模式）
        try:
            # 对于复杂表达式，尝试编译并执行
            # 这是一个安全的方式，因为我们只处理配置文件
            code = compile(ast.Expression(node), '<string>', 'eval')
            
            # 创建一个安全的执行环境，包含变量上下文
            safe_dict = {
                'dict': dict,
                'list': list,
                'tuple': tuple,
                'set': set,
                'range': range,
                'max': max,
                'min': min,
                'len': len,
                'sum': sum,
                'abs': abs,
                'round': round,
                'True': True,
                'False': False,
                'None': None,
            }
            # 添加变量上下文
            safe_dict.update(var_context)
            
            result = eval(code, {"__builtins__": {}}, safe_dict)
            return result
        except Exception:
            return f"<unparseable>"


def ast_eval_node(node):
    """递归解析 AST 节点，支持复杂表达式"""
    if isinstance(node, ast.Constant):
        return node.value
    elif isinstance(node, ast.Str):  # Python < 3.8 兼容
        return node.s
    elif isinstance(node, ast.Num):  # Python < 3.8 兼容
        return node.n
    elif isinstance(node, ast.List):
        return [ast_eval_node(elem) for elem in node.elts]
    elif isinstance(node, ast.Dict):
        keys = [ast_eval_node(k) if k else None for k in node.keys]
        values = [ast_eval_node(v) for v in node.values]
        return dict(zip(keys, values))
    elif isinstance(node, ast.BinOp):
        # 处理二元运算：加减乘除等
        left = ast_eval_node(node.left)
        right = ast_eval_node(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        elif isinstance(node.op, ast.Sub):
            return left - right
        elif isinstance(node.op, ast.Mult):
            return left * right
        elif isinstance(node.op, ast.Div):
            return left / right
        elif isinstance(node.op, ast.FloorDiv):
            return left // right
        elif isinstance(node.op, ast.Mod):
            return left % right
        elif isinstance(node.op, ast.Pow):
            return left ** right
    elif isinstance(node, ast.UnaryOp):
        # 处理一元运算：负号等
        operand = ast_eval_node(node.operand)
        if isinstance(node.op, ast.UAdd):
            return +operand
        elif isinstance(node.op, ast.USub):
            return -operand
    elif isinstance(node, ast.Call):
        # 处理函数调用
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name == 'dict':
                # dict() 调用
                result_dict = {}
                for keyword in node.keywords:
                    result_dict[keyword.arg] = ast_eval_node(keyword.value)
                return result_dict
            elif func_name == 'list':
                # list() 调用
                if node.args:
                    return list(ast_eval_node(node.args[0]))
                return []
            elif func_name == 'range':
                # range() 调用
                args = [ast_eval_node(arg) for arg in node.args]
                return list(range(*args))
            elif func_name == 'max':
                # max() 调用
                args = [ast_eval_node(arg) for arg in node.args]
                return max(args)
            elif func_name == 'min':
                # min() 调用
                args = [ast_eval_node(arg) for arg in node.args]
                return min(args)
    elif isinstance(node, ast.Tuple):
        return tuple(ast_eval_node(elem) for elem in node.elts)
    elif isinstance(node, ast.NameConstant):  # True, False, None
        return node.value
    elif isinstance(node, ast.Name):
        # 对于变量引用，返回变量名字符串（简化处理）
        return f"<variable:{node.id}>"
    elif isinstance(node, ast.ListComp):
        # 处理列表推导式 [expr for target in iter if condition]
        # 支持多个生成器：[expr for x in iter1 for y in iter2 ...]
        try:
            # 处理多个生成器的情况
            generators = node.generators
            if not generators:
                return f"<list_comprehension>"
            
            # 递归处理所有生成器，构建嵌套循环
            def process_generators(gen_index, current_context):
                if gen_index >= len(generators):
                    # 所有生成器都处理完了，计算元素表达式
                    return [ast_eval_node_with_context(node.elt, current_context)]
                
                # 处理当前生成器
                generator = generators[gen_index]
                iter_node = generator.iter
                target_var = generator.target
                
                # 获取迭代器的值
                iter_values = ast_eval_node_with_context(iter_node, current_context)
                
                if not isinstance(target_var, ast.Name) or not isinstance(iter_values, list):
                    return [f"<complex_generator_{gen_index}>"]
                
                target_var_name = target_var.id
                result = []
                
                # 对每个值进行迭代
                for value in iter_values:
                    # 创建新的上下文，包含当前变量
                    new_context = current_context.copy()
                    new_context[target_var_name] = value
                    
                    # 递归处理下一个生成器
                    sub_results = process_generators(gen_index + 1, new_context)
                    result.extend(sub_results)
                
                return result
            
            # 从第一个生成器开始处理
            result = process_generators(0, {})
            return result
            
        except Exception as e:
            logger.warning(f"列表推导式解析失败: {e}")
            return f"<list_comprehension>"
    elif isinstance(node, ast.SetComp):
        # 处理集合推导式
        return f"<set_comprehension>"
    elif isinstance(node, ast.DictComp):
        # 处理字典推导式
        return f"<dict_comprehension>"
    elif isinstance(node, ast.GeneratorExp):
        # 处理生成器表达式
        return f"<generator_expression>"

    # 对于其他复杂表达式，尝试字面量解析
    try:
        return ast.literal_eval(node)
    except:
        # 如果还是无法解析，尝试执行代码（安全模式）
        try:
            # 对于复杂表达式，尝试编译并执行
            # 这是一个安全的方式，因为我们只处理配置文件
            code = compile(ast.Expression(node), '<string>', 'eval')
            
            # 创建一个安全的执行环境
            safe_dict = {
                'dict': dict,
                'list': list,
                'tuple': tuple,
                'set': set,
                'range': range,
                'max': max,
                'min': min,
                'len': len,
                'sum': sum,
                'abs': abs,
                'round': round,
                'True': True,
                'False': False,
                'None': None,
            }
            
            result = eval(code, {"__builtins__": {}}, safe_dict)
            return result
        except Exception:
            return f"<unparseable>"


def detect_config_file_type(content: str) -> str:
    """
    检测配置文件类型

    通过检查文件中是否存在 strategy_pool 变量来判断文件类型。

    Args:
        content: 配置文件内容

    Returns:
        'pos' - 仓位管理框架格式（有 strategy_pool）
        'coin' - 选币框架格式（无 strategy_pool）
    """
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == 'strategy_pool':
                        return 'pos'
        return 'coin'
    except Exception as e:
        logger.warning(f"解析配置文件时出错，默认按 coin 类型处理: {e}")
        return 'coin'


def extract_variables_from_coin_config(content: str, account_name: str, default_strategy_name: str = None) -> Tuple[Dict, Optional[str]]:
    """
    从 Coin 类型配置文件中提取变量并转换为 Pos 格式

    支持两种 Coin 配置格式：
    1. coin1（实盘多账户）：有 account_config 字典
    2. coin2（回测）：顶层变量直接定义

    Args:
        content: 配置文件内容
        account_name: 账户名称（用于日志记录）
        default_strategy_name: 默认策略名称，当文件中没有 backtest_name 时使用

    Returns:
        (dict, str): (提取的变量字典, 错误信息)
        成功时错误信息为 None
    """
    result = {}

    try:
        # 创建 Mock 类型
        class MockPath:
            def __init__(self, *args):
                pass
            def __truediv__(self, other):
                return self
            def exists(self):
                return False

        class MockOS:
            @staticmethod
            def cpu_count():
                return 8

            class path:
                @staticmethod
                def abspath(p):
                    return '/mock/absolute/path'
                @staticmethod
                def dirname(p):
                    return '/mock/dir'
                @staticmethod
                def join(*args):
                    return '/'.join(args)

        # 创建一个智能的 __import__ 函数
        def mock_import(name, *args, **kwargs):
            """模拟导入，返回包含所需属性的 Mock 模块"""
            # 为不同的模块返回不同的 Mock
            if name == 'pathlib':
                return type('MockPathlibModule', (), {'Path': MockPath})()
            elif name == 'core.utils.path_kit' or 'path_kit' in name:
                return type('MockPathKitModule', (), {
                    'get_folder_path': lambda *args, **kwargs: '/mock/path'
                })()
            elif name == 'os':
                return MockOS
            elif name == 'time':
                return type('MockTimeModule', (), {
                    'localtime': lambda *args, **kwargs: type('MockLocalTime', (), {'tm_gmtoff': 28800})(),
                })()
            else:
                # 通用 Mock 模块，支持任意属性访问
                class UniversalMock:
                    def __getattr__(self, item):
                        # 返回一个灵活的 Mock 对象
                        def mock_method(*args, **kwargs):
                            # 返回 self 以支持链式调用
                            return self
                        return mock_method
                    def __call__(self, *args, **kwargs):
                        return self
                return UniversalMock()

        # 创建安全的执行环境
        safe_globals = {
            "__builtins__": {
                '__import__': mock_import,
                'print': lambda *args, **kwargs: None,  # Mock print，不输出
                'exit': lambda *args, **kwargs: None,  # Mock exit，不退出
                'int': int,
                'float': float,
                'str': str,
                'bool': bool,
                'dict': dict,
                'list': list,
                'tuple': tuple,
                'set': set,
                'range': range,
                'max': max,
                'min': min,
                'len': len,
                'sum': sum,
                'abs': abs,
                'round': round,
                'True': True,
                'False': False,
                'None': None,
                'type': type,
                'isinstance': isinstance,
            },
            'dict': dict,
            'list': list,
            'tuple': tuple,
            'set': set,
            'range': range,
            'max': max,
            'min': min,
            'len': len,
            'sum': sum,
            'abs': abs,
            'round': round,
            'True': True,
            'False': False,
            'None': None,
        }

        safe_locals = {}
        # 添加一些特殊变量
        safe_globals['__file__'] = '/mock/config.py'
        safe_globals['__name__'] = '__main__'

        exec(content, safe_globals, safe_locals)

        # 1. 提取 backtest_name（如果没有则使用默认值）
        backtest_name = safe_locals.get('backtest_name')
        if not backtest_name:
            if default_strategy_name:
                backtest_name = default_strategy_name
                logger.info(f"文件中未找到 backtest_name，使用默认值: {backtest_name}")
            else:
                return {}, "Coin类型配置文件必须包含 backtest_name 属性，或提供默认策略名称"
        else:
            logger.info(f"提取到 backtest_name: {backtest_name}")

        # 2. 检测是否有 account_config（区分 coin1 和 coin2）
        account_config = safe_locals.get('account_config')

        # 3. 提取 strategy_list
        strategy_list = None
        if account_config and isinstance(account_config, dict):
            # coin1 类型：从第一个账户提取
            logger.info("检测到 account_config，按 coin1 类型（实盘多账户）处理")
            if not account_config:
                return {}, "account_config 不能为空"

            first_account_config = list(account_config.values())[0]
            strategy_list = first_account_config.get('strategy_list')
            logger.info(f"从第一个账户配置中提取 strategy_list，包含 {len(strategy_list) if strategy_list else 0} 个策略")
        else:
            # coin2 类型：从顶层提取
            logger.info("未检测到 account_config，按 coin2 类型（回测）处理")
            strategy_list = safe_locals.get('strategy_list')
            logger.info(f"从顶层提取 strategy_list，包含 {len(strategy_list) if strategy_list else 0} 个策略")

        if not strategy_list:
            return {}, "配置文件缺少 strategy_list 属性"

        # 4. 构造 strategy_pool（转换为 pos 格式）
        result['strategy_pool'] = [{
            'name': backtest_name,
            'strategy_list': strategy_list
        }]
        logger.info(f"构造 strategy_pool 完成")

        # 5. 设置 strategy_name
        result['strategy_name_from_backtest'] = backtest_name

        # 6. 构造固定的 strategy_config
        result['strategy_config'] = {
            'name': 'FixedRatioStrategy',
            'hold_period': '1H',
            'cap_ratios': [1]
        }
        logger.info("设置固定的 strategy_config")

        # 7. 提取其他变量（保持原有逻辑）
        optional_vars = {
            'get_kline_num': safe_locals.get('get_kline_num'),
            'min_kline_num': safe_locals.get('min_kline_num'),
            'leverage': safe_locals.get('leverage'),
            'black_list': safe_locals.get('black_list'),
            'white_list': safe_locals.get('white_list'),
            'rebalance_mode': safe_locals.get('rebalance_mode'),
        }

        # 只添加非 None 的变量
        for key, value in optional_vars.items():
            if value is not None:
                result[key] = value
                logger.info(f"提取到 {key}: {value}")

        logger.info(f"Coin 配置文件转换完成，提取到 {len(result)} 个字段")
        return result, None

    except Exception as e:
        error_msg = f"解析 Coin 配置文件失败: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return {}, error_msg


def extract_variables_from_py(content: str, key_map: dict):
    """
    提取指定 keys 的顶层变量赋值，支持复杂的 Python 表达式
    key_map: {目标字段: 源文件变量名}
    """
    result = {}

    try:
        # 方法1：尝试直接执行代码在安全环境中
        try:
            # 创建一个安全的执行环境
            safe_globals = {
                "__builtins__": {},
                'dict': dict,
                'list': list,
                'tuple': tuple,
                'set': set,
                'range': range,
                'max': max,
                'min': min,
                'len': len,
                'sum': sum,
                'abs': abs,
                'round': round,
                'True': True,
                'False': False,
                'None': None,
                # 添加一些配置文件中可能用到的模块和函数
                'os': type('MockOS', (), {
                    'cpu_count': lambda: 8,  # 模拟 os.cpu_count()
                })(),
                'Path': type('MockPath', (), {
                    '__call__': lambda self, *args: type('MockPathInstance', (), {
                        '__truediv__': lambda self, other: self,
                        'exists': lambda: False,
                    })()
                })(),
            }
            safe_locals = {}
            
            # 执行整个代码，提取需要的变量
            exec(content, safe_globals, safe_locals)
            
            # 从执行结果中提取需要的变量
            for target_key, source_var in key_map.items():
                if source_var in safe_locals:
                    result[target_key] = safe_locals[source_var]
                else:
                    result[target_key] = None
            
            logger.info("使用 exec 方法成功解析配置文件")
            return result, None
            
        except Exception as exec_error:
            logger.warning(f"exec 方法解析失败: {exec_error}，回退到 AST 方法")
            
        # 方法2：回退到 AST 解析方法
        tree = ast.parse(content)
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                var_name = node.targets[0].id if isinstance(node.targets[0], ast.Name) else None
                for target_key, source_var in key_map.items():
                    if var_name == source_var:
                        try:
                            value = ast_eval_node(node.value)
                            result[target_key] = value
                        except Exception as e:
                            # 如果解析失败，记录错误但继续
                            logger.error(f"AST 解析变量 {source_var} 失败: {e}")
                            result[target_key] = f"<parse_error: {e}>"
                                
    except Exception as e:
        return None, f"代码解析失败: {e}"

    # 没有的字段补 None
    for k in key_map:
        if k not in result:
            result[k] = None

    return result, None


def migrate_framework_data(raw_framework_status, target_framework_status):
    """
    框架数据迁移核心逻辑
    
    将源框架的账户配置和数据迁移到目标框架。
    包括账户配置文件（.json 和 .py）以及对应的用户数据目录。
    
    Args:
        raw_framework_status: 源框架状态对象
        target_framework_status: 目标框架状态对象
        
    Returns:
        tuple: (success: bool, result: dict, error_msg: str)
    """
    logger.info(f"开始框架数据迁移: {raw_framework_status.framework_name} -> {target_framework_status.framework_name}")
    
    try:
        # 获取框架路径
        raw_framework_path = Path(raw_framework_status.path)
        target_framework_path = Path(target_framework_status.path)
        
        logger.info(f"源框架路径: {raw_framework_path}")
        logger.info(f"目标框架路径: {target_framework_path}")
        
        # 检查源框架的accounts目录是否存在
        raw_accounts_dir = raw_framework_path / 'accounts'
        if not raw_accounts_dir.exists():
            error_msg = f'源框架 {raw_framework_status.framework_id} 的accounts目录不存在'
            logger.warning(error_msg)
            return False, None, error_msg

        raw_config_path = raw_framework_path / 'config.json'
        target_config_path = target_framework_path / 'config.json'
        if raw_config_path.exists():
            config_json = json.loads(raw_config_path.read_text(encoding='utf-8'))
            config_json['framework_id'] = target_framework_status.framework_id
            target_config_path.write_text(
                json.dumps(config_json, ensure_ascii=False, indent=2),
                encoding='utf-8'
            )
            logger.info(f'已迁移框架配置文件 config.json')

        # 确保目标框架的accounts目录存在
        target_accounts_dir = target_framework_path / 'accounts'
        target_accounts_dir.mkdir(exist_ok=True)
        
        # 迁移账户配置文件
        migrated_users = []
        failed_users = []
        
        # 获取源框架中所有的JSON账户配置文件
        json_files = [file for file in raw_accounts_dir.iterdir() 
                     if file.is_file() and file.suffix == ".json" and not file.name.startswith('_')]
        
        logger.info(f"找到 {len(json_files)} 个账户配置文件需要迁移")
        
        if len(json_files) == 0:
            error_msg = f'源框架 {raw_framework_status.framework_id} 中没有找到有效的账户配置文件'
            logger.warning(error_msg)
            return False, None, error_msg
        
        for json_file in json_files:
            account_name = json_file.stem
            logger.info(f"开始迁移账户: {account_name}")
            
            try:
                # 读取并更新JSON配置文件中的framework_id
                account_json = json.loads(json_file.read_text(encoding='utf-8'))
                
                # 更新framework_id为目标框架ID
                old_framework_id = account_json.get('framework_id')
                account_json['framework_id'] = target_framework_status.framework_id
                logger.info(f"更新账户配置中的framework_id: {old_framework_id} -> {target_framework_status.framework_id}")
                
                # 保存更新后的JSON配置文件到目标位置
                target_json_file = target_accounts_dir / json_file.name
                target_json_file.write_text(
                    json.dumps(account_json, ensure_ascii=False, indent=2),
                    encoding='utf-8'
                )
                logger.info(f"已迁移并更新JSON配置文件: {json_file.name}")
                
                # 查找对应的Python配置文件（正常和锁定状态）
                normal_py_file = raw_accounts_dir / f"{account_name}.py"
                locked_py_file = raw_accounts_dir / f"_{account_name}.py"
                
                py_files_migrated = []
                if normal_py_file.exists():
                    target_py_file = target_accounts_dir / normal_py_file.name
                    shutil.copy2(normal_py_file, target_py_file)
                    py_files_migrated.append(normal_py_file.name)
                    logger.info(f"已迁移Python配置文件: {normal_py_file.name}")
                
                if locked_py_file.exists():
                    target_locked_py_file = target_accounts_dir / locked_py_file.name
                    shutil.copy2(locked_py_file, target_locked_py_file)
                    py_files_migrated.append(locked_py_file.name)
                    logger.info(f"已迁移锁定Python配置文件: {locked_py_file.name}")
                
                # 迁移用户数据目录
                data_migrated = _migrate_user_data(
                    raw_framework_path, target_framework_path, account_name
                )
                
                # 迁移snapshot数据
                snapshot_migrated = _migrate_snapshot_data(
                    raw_framework_path, target_framework_path, account_name
                )
                
                migrated_users.append({
                    'account_name': account_name,
                    'json_file': json_file.name,
                    'py_files': py_files_migrated,
                    'data_migrated': data_migrated,
                    'snapshot_migrated': snapshot_migrated,
                    'framework_id_updated': {
                        'old': old_framework_id,
                        'new': target_framework_status.framework_id
                    }
                })
                
                logger.info(f"账户 {account_name} 迁移成功")
                
            except Exception as e:
                logger.error(f"迁移账户 {account_name} 失败: {e}")
                failed_users.append({
                    'account_name': account_name,
                    'error': str(e)
                })
        
        # 生成迁移报告
        migration_report = {
            'source_framework': {
                'id': raw_framework_status.framework_id,
                'name': raw_framework_status.framework_name,
                'path': str(raw_framework_path)
            },
            'target_framework': {
                'id': target_framework_status.framework_id,
                'name': target_framework_status.framework_name,
                'path': str(target_framework_path)
            },
            'migration_summary': {
                'total_accounts': len(json_files),
                'migrated_successfully': len(migrated_users),
                'failed_migrations': len(failed_users)
            },
            'migrated_accounts': migrated_users,
            'failed_accounts': failed_users
        }
        
        logger.info(f"数据迁移完成: 成功迁移 {len(migrated_users)} 个账户，失败 {len(failed_users)} 个账户")
        
        success = len(failed_users) == 0
        error_msg = None if success else f"有 {len(failed_users)} 个账户迁移失败"
        
        return success, migration_report, error_msg
    
    except Exception as e:
        logger.error(f"数据迁移过程中发生异常: {e}")
        return False, None, f"数据迁移失败: {str(e)}"


def _migrate_user_data(raw_framework_path, target_framework_path, account_name):
    """
    迁移用户数据目录
    
    Args:
        raw_framework_path: 源框架路径
        target_framework_path: 目标框架路径
        account_name: 账户名称
        
    Returns:
        bool: 是否成功迁移用户数据
    """
    try:
        raw_data_dir = raw_framework_path / 'data'
        target_data_dir = target_framework_path / 'data'
        
        if not raw_data_dir.exists():
            logger.warning(f"源框架data目录不存在: {raw_data_dir}")
            return False
        
        target_data_dir.mkdir(exist_ok=True)
        
        # 迁移用户名称对应的数据目录
        user_data_dir = raw_data_dir / account_name
        if user_data_dir.exists() and user_data_dir.is_dir():
            target_user_data_dir = target_data_dir / account_name
            
            # 如果目标目录已存在，先删除
            if target_user_data_dir.exists():
                logger.warning(f"目标用户数据目录已存在，将被覆盖: {target_user_data_dir}")
                shutil.rmtree(target_user_data_dir)
            
            # 复制整个用户数据目录
            shutil.copytree(user_data_dir, target_user_data_dir)
            logger.info(f"已迁移用户数据目录: {account_name}")
            return True
        else:
            logger.warning(f"用户数据目录不存在，跳过: {user_data_dir}")
            return False
            
    except Exception as e:
        logger.error(f"迁移用户数据目录失败 {account_name}: {e}")
        return False


def _migrate_snapshot_data(raw_framework_path, target_framework_path, account_name):
    """
    迁移snapshot数据
    
    Args:
        raw_framework_path: 源框架路径
        target_framework_path: 目标框架路径
        account_name: 账户名称
        
    Returns:
        list: 成功迁移的snapshot目录列表
    """
    migrated_snapshots = []
    
    try:
        raw_data_dir = raw_framework_path / 'data'
        target_data_dir = target_framework_path / 'data'
        
        raw_snapshot_dir = raw_data_dir / 'snapshot'
        if not raw_snapshot_dir.exists():
            logger.info(f"源框架snapshot目录不存在: {raw_snapshot_dir}")
            return migrated_snapshots
        
        target_snapshot_dir = target_data_dir / 'snapshot'
        target_snapshot_dir.mkdir(exist_ok=True)
        
        # 查找以账户名开头的snapshot目录
        snapshot_prefix = f"{account_name}_"
        snapshot_dirs = [d for d in raw_snapshot_dir.iterdir() 
                        if d.is_dir() and d.name.startswith(snapshot_prefix)]
        
        for snapshot_dir in snapshot_dirs:
            try:
                target_snapshot_subdir = target_snapshot_dir / snapshot_dir.name
                
                # 如果目标目录已存在，先删除
                if target_snapshot_subdir.exists():
                    logger.warning(f"目标snapshot目录已存在，将被覆盖: {target_snapshot_subdir}")
                    shutil.rmtree(target_snapshot_subdir)
                
                # 复制snapshot目录
                shutil.copytree(snapshot_dir, target_snapshot_subdir)
                migrated_snapshots.append(snapshot_dir.name)
                logger.info(f"已迁移snapshot目录: {snapshot_dir.name}")
                
            except Exception as e:
                logger.error(f"迁移snapshot目录失败 {snapshot_dir.name}: {e}")
        
        logger.info(f"账户 {account_name} 共迁移了 {len(migrated_snapshots)} 个snapshot目录")
        
    except Exception as e:
        logger.error(f"迁移snapshot数据失败 {account_name}: {e}")
    
    return migrated_snapshots


def export_framework_data(framework_status, export_name: Optional[str] = None) -> Tuple[bool, Dict, str]:
    """
    导出框架数据到ZIP包
    
    Args:
        framework_status: 框架状态对象
        export_name: 导出包名称（可选）
        
    Returns:
        tuple: (success: bool, result: dict, error_msg: str)
    """
    logger.info(f"开始导出框架数据: {framework_status.framework_name} ({framework_status.framework_id})")
    
    try:
        # 获取框架路径
        framework_path = Path(framework_status.path)
        
        if not framework_path.exists():
            error_msg = f'框架路径不存在: {framework_path}'
            logger.error(error_msg)
            return False, {}, error_msg
        
        # 生成导出文件名
        if not export_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_name = f"export_{framework_status.framework_id}_{timestamp}"
        
        # 创建临时目录
        temp_dir = create_temp_directory("qronos_export_")
        export_dir = temp_dir / "export_data"
        export_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # 收集需要导出的数据
            exported_accounts = []
            exported_data_dirs = []
            total_files = 0
            
            # 1. 导出accounts目录
            accounts_source = framework_path / 'accounts'
            if accounts_source.exists():
                accounts_target = export_dir / 'accounts'
                accounts_target.mkdir(parents=True, exist_ok=True)
                
                for file in accounts_source.iterdir():
                    if file.is_file() and file.suffix in ['.json', '.py']:
                        shutil.copy2(file, accounts_target / file.name)
                        if file.suffix == '.json' and not file.name.startswith('_'):
                            exported_accounts.append(file.stem)
                        total_files += 1
                        # logger.debug(f"已导出账户文件: {file.name}")
            
            # 2. 导出data目录（只导出账户名对应的目录）
            data_source = framework_path / 'data'
            if data_source.exists():
                data_target = export_dir / 'data'
                data_target.mkdir(parents=True, exist_ok=True)
                
                # 只导出有效账户对应的数据目录（仅包含"账户信息"子目录）
                for account_name in exported_accounts:
                    account_data_dir = data_source / account_name
                    if account_data_dir.exists() and account_data_dir.is_dir():
                        # 复制账户数据目录，只包含"账户信息"子目录
                        target_item = data_target / account_name
                        copied_files = copy_directory_with_filter(
                            account_data_dir, 
                            target_item,
                            include_only_dirs=["账户信息"]
                        )
                        
                        if copied_files > 0:
                            exported_data_dirs.append(account_name)
                            total_files += copied_files
                            logger.debug(f"已导出账户数据目录: {account_name} (只包含: 账户信息, 文件数: {copied_files})")
                        else:
                            logger.warning(f"账户 {account_name} 没有账户信息目录，跳过导出")
            
            # 3. 导出config.json
            config_source = framework_path / 'config.json'
            if config_source.exists():
                shutil.copy2(config_source, export_dir / 'config.json')
                total_files += 1
                logger.debug("已导出config.json")
            
            # 4. 导出框架核心目录 (factors, positions, sections, signals)
            exported_framework_dirs = []
            framework_dirs = ['factors', 'positions', 'sections', 'signals']
            
            for dir_name in framework_dirs:
                source_dir = framework_path / dir_name
                if source_dir.exists() and source_dir.is_dir():
                    target_dir = export_dir / dir_name
                    copied_files = copy_directory_with_filter(
                        source_dir, 
                        target_dir,
                        exclude_dirs=["__pycache__"]
                    )
                    
                    if copied_files > 0:
                        exported_framework_dirs.append(dir_name)
                        total_files += copied_files
                        logger.debug(f"已导出框架目录: {dir_name} (排除: __pycache__, 文件数: {copied_files})")
                    else:
                        logger.warning(f"框架目录 {dir_name} 没有有效文件，跳过导出")
                else:
                    logger.debug(f"框架目录不存在，跳过: {dir_name}")
            
            # 5. 生成导出元数据
            total_size = calculate_directory_size(export_dir)
            metadata = {
                "export_time": datetime.now().isoformat(),
                "source_framework_id": framework_status.framework_id,
                "source_framework_name": framework_status.framework_name,
                "source_framework_path": str(framework_path),
                "exported_accounts": exported_accounts,
                "exported_data_dirs": exported_data_dirs,
                "exported_framework_dirs": exported_framework_dirs,
                "total_files": total_files,
                "total_size": total_size,
            }
            
            metadata_file = export_dir / 'metadata.json'
            metadata_file.write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2),
                encoding='utf-8'
            )
            
            # 5. 创建ZIP包
            zip_path = temp_dir / f"{export_name}.zip"
            files_to_zip = [export_dir]
            
            success, error_msg = create_zip_archive(files_to_zip, zip_path, temp_dir)
            if not success:
                return False, {}, error_msg
            
            # 6. 移动ZIP包到最终位置
            final_zip_path = Path(TMP_PATH) / f"{export_name}.zip"
            final_zip_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(zip_path, final_zip_path)

            # 7. 清理多余的ZIP文件
            try:
                total_zip_files, deleted_count, deleted_file_list = cleanup_zip_files_by_count()
                cleanup_info = f"ZIP文件清理: 总数={total_zip_files}, 删除={deleted_count}"
                if deleted_count > 0:
                    logger.info(cleanup_info)
                else:
                    logger.debug(cleanup_info)
            except Exception as e:
                logger.warning(f"ZIP文件清理失败，但不影响导出: {e}")

            # 8. 生成结果
            result = {
                "filename": f"{export_name}.zip",
                "success": True,
                "message": "导出成功"
            }
            
            logger.info(f"框架数据导出完成: {final_zip_path}")
            logger.info(f"框架数据导出metadata: {metadata_file}")
            logger.info(f"导出统计: 账户数={len(exported_accounts)}, 数据目录数={len(exported_data_dirs)}, "
                       f"框架目录数={len(exported_framework_dirs)}, 总文件数={total_files}")
            logger.info(f"导出的框架目录: {exported_framework_dirs}")
            
            return True, result, ""
            
        finally:
            # 清理临时目录
            cleanup_temp_directory(temp_dir)
    
    except Exception as e:
        logger.error(f"导出框架数据失败: {e}")
        return False, {}, f"导出失败: {str(e)}"


def import_framework_data(zip_file_path: Path, target_framework_status) -> Tuple[bool, Dict, str]:
    """
    从ZIP包导入框架数据
    
    Args:
        zip_file_path: ZIP文件路径
        target_framework_status: 目标框架状态对象

    Returns:
        tuple: (success: bool, result: dict, error_msg: str)
    """
    logger.info(f"开始导入框架数据: {zip_file_path} -> {target_framework_status.framework_name}")
    
    try:
        # 获取目标框架路径
        target_framework_path = Path(target_framework_status.path)
        
        if not target_framework_path.exists():
            error_msg = f'目标框架路径不存在: {target_framework_path}'
            logger.error(error_msg)
            return False, {}, error_msg
        
        # 创建临时目录
        temp_dir = create_temp_directory("qronos_import_")
        
        try:
            # 1. 解压ZIP文件
            success, error_msg, extracted_files = extract_zip_archive(zip_file_path, temp_dir)
            if not success:
                return False, {}, error_msg
            
            # 2. 查找并验证解压后的数据目录
            export_data_dir = None
            for item in temp_dir.iterdir():
                if item.is_dir() and (item / 'metadata.json').exists():
                    export_data_dir = item
                    break
            
            if not export_data_dir:
                error_msg = "ZIP包中未找到有效的导出数据"
                logger.error(error_msg)
                return False, {}, error_msg
            
            # 3. 读取并验证元数据
            metadata_file = export_data_dir / 'metadata.json'
            try:
                metadata = json.loads(metadata_file.read_text(encoding='utf-8'))
            except Exception as e:
                error_msg = f"读取元数据失败: {e}"
                logger.error(error_msg)
                return False, {}, error_msg
            
            logger.info(f"导入数据元信息: 源框架={metadata.get('source_framework_name')}, "
                       f"账户数={len(metadata.get('exported_accounts', []))}")
            
            # 4. 导入数据
            imported_accounts = []
            updated_paths = []
            errors = []
            
            # 导入accounts目录
            accounts_source = export_data_dir / 'accounts'
            if accounts_source.exists():
                accounts_target = target_framework_path / 'accounts'
                accounts_target.mkdir(parents=True, exist_ok=True)
                
                for file in accounts_source.iterdir():
                    if file.is_file():
                        target_file = accounts_target / file.name
                        
                        try:
                            # 对于JSON文件，需要更新framework_id
                            if file.suffix == '.json':
                                account_data = json.loads(file.read_text(encoding='utf-8'))
                                old_framework_id = account_data.get('framework_id')
                                account_data['framework_id'] = target_framework_status.framework_id
                                
                                target_file.write_text(
                                    json.dumps(account_data, ensure_ascii=False, indent=2),
                                    encoding='utf-8'
                                )
                                
                                if old_framework_id != target_framework_status.framework_id:
                                    updated_paths.append(f"{file.name}: framework_id")
                                
                                if not file.name.startswith('_'):
                                    imported_accounts.append(file.stem)
                            else:
                                shutil.copy2(file, target_file)
                            
                            logger.debug(f"已导入账户文件: {file.name}")
                            
                        except Exception as e:
                            error_msg = f"导入账户文件失败 {file.name}: {e}"
                            errors.append(error_msg)
                            logger.error(error_msg)
            
            # 导入data目录
            data_source = export_data_dir / 'data'
            if data_source.exists():
                data_target = target_framework_path / 'data'
                data_target.mkdir(parents=True, exist_ok=True)
                
                for item in data_source.iterdir():
                    if item.is_dir():
                        target_item = data_target / item.name
                        
                        try:
                            if target_item.exists():
                                shutil.rmtree(target_item)
                            # 导入时也要排除__pycache__目录（保持一致性）
                            copied_files = copy_directory_with_filter(
                                item, 
                                target_item,
                                exclude_dirs=["__pycache__"]
                            )
                            logger.debug(f"已导入数据目录: {item.name} (文件数: {copied_files})")
                        except Exception as e:
                            error_msg = f"导入数据目录失败 {item.name}: {e}"
                            errors.append(error_msg)
                            logger.error(error_msg)
            
            # 导入框架核心目录 (factors, positions, sections, signals)
            framework_dirs = ['factors', 'positions', 'sections', 'signals']
            imported_framework_dirs = []
            
            for dir_name in framework_dirs:
                source_dir = export_data_dir / dir_name
                if source_dir.exists() and source_dir.is_dir():
                    target_dir = target_framework_path / dir_name
                    
                    try:
                        # 如果目标目录已存在，先删除
                        if target_dir.exists():
                            shutil.rmtree(target_dir)
                        
                        # 复制框架目录，排除__pycache__
                        copied_files = copy_directory_with_filter(
                            source_dir, 
                            target_dir,
                            exclude_dirs=["__pycache__"]
                        )
                        imported_framework_dirs.append(dir_name)
                        logger.debug(f"已导入框架目录: {dir_name} (排除: __pycache__, 文件数: {copied_files})")
                        
                    except Exception as e:
                        error_msg = f"导入框架目录失败 {dir_name}: {e}"
                        errors.append(error_msg)
                        logger.error(error_msg)
                else:
                    logger.debug(f"导出包中不包含框架目录: {dir_name}")
            
            # 导入并更新config.json
            config_source = export_data_dir / 'config.json'
            if config_source.exists():
                try:
                    config_data = json.loads(config_source.read_text(encoding='utf-8'))
                    
                    # 更新framework_id
                    old_framework_id = config_data.get('framework_id')
                    config_data['framework_id'] = target_framework_status.framework_id
                    
                    # 更新realtime_data_path
                    from db.db_ops import get_finished_data_center_status
                    data_center_status = get_finished_data_center_status()
                    if data_center_status and data_center_status.path:
                        old_data_path = config_data.get('realtime_data_path')
                        new_data_path = str(Path(data_center_status.path) / 'data')
                        config_data['realtime_data_path'] = new_data_path
                        
                        if old_data_path != new_data_path:
                            updated_paths.append(f"config.json: realtime_data_path")
                    
                    # 保存更新后的config.json
                    config_target = target_framework_path / 'config.json'
                    config_target.write_text(
                        json.dumps(config_data, ensure_ascii=False, indent=2),
                        encoding='utf-8'
                    )
                    
                    if old_framework_id != target_framework_status.framework_id:
                        updated_paths.append(f"config.json: framework_id")
                    
                    logger.info("已导入并更新config.json")
                    
                except Exception as e:
                    error_msg = f"导入config.json失败: {e}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            else:
                error_msg = f"压缩包中config.json不存在"
                errors.append(error_msg)
                logger.error(error_msg)
            
            # 7. 生成结果
            result = {
                "imported_accounts": imported_accounts,
                "imported_framework_dirs": imported_framework_dirs,
                "updated_paths": updated_paths,
                "errors": errors,
                "success": len(errors) == 0,
                "message": "导入成功" if len(errors) == 0 else f"导入完成，但有{len(errors)}个错误"
            }
            
            logger.info(f"框架数据导入完成: 成功导入 {len(imported_accounts)} 个账户, "
                       f"{len(imported_framework_dirs)} 个框架目录")
            if imported_framework_dirs:
                logger.info(f"导入的框架目录: {imported_framework_dirs}")
            if updated_paths:
                logger.info(f"已更新路径: {updated_paths}")
            if errors:
                logger.warning(f"导入错误: {errors}")
            
            return True, result, ""
            
        finally:
            # 清理临时目录
            cleanup_temp_directory(temp_dir)
    
    except Exception as e:
        logger.error(f"导入框架数据失败: {e}")
        return False, {}, f"导入失败: {str(e)}"
