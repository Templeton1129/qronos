import json
import os
import time as time_mod
from datetime import datetime
from pathlib import Path
from typing import Dict

import pandas as pd

from utils.log_kit import get_logger

logger = get_logger()

# ===== 晒单统计缓存 =====
_showcase_statistics_cache: Dict[tuple, dict] = {}
_SHOWCASE_CACHE_TTL = 300


def _collect_showcase_file_mtimes(account_json_path: Path, account_info_path: Path) -> dict:
    """
    收集晒单统计依赖文件的修改时间。

    Args:
        account_json_path: 账户配置文件路径。
        account_info_path: 账户统计目录路径。

    Returns:
        dict: 文件路径与修改时间的映射，用于缓存失效判断。
    """
    mtimes = {}
    for file_path in [
        account_json_path,
        account_info_path / 'equity.pkl',
    ]:
        if file_path.exists():
            mtimes[str(file_path)] = os.path.getmtime(file_path)
    return mtimes


def _is_showcase_cache_valid(cache_entry: dict, current_mtimes: dict) -> bool:
    """
    判断晒单缓存是否仍然有效。

    Args:
        cache_entry: 缓存中保存的数据结构。
        current_mtimes: 当前文件修改时间快照。

    Returns:
        bool: 未过期且文件未变化时返回 True。
    """
    if time_mod.time() - cache_entry['ts'] > _SHOWCASE_CACHE_TTL:
        return False
    if cache_entry['mtimes'] != current_mtimes:
        return False
    return True


def _round_nullable(value, digits: int = 2):
    """
    将可空数值统一转为浮点并保留固定位数。

    Args:
        value: 待处理数值。
        digits: 保留的小数位数。

    Returns:
        float | None: 转换后的数值；为空时返回 None。
    """
    if value is None or pd.isna(value):
        return None
    return round(float(value), digits)


def _format_equity_time(value, hour_offset: str) -> str | None:
    """
    将时间字段转为前端展示时间。

    Args:
        value: 原始时间值。
        hour_offset: 账户时区偏移。

    Returns:
        str | None: 偏移后的时间字符串；为空时返回 None。
    """
    if value is None or pd.isna(value):
        return None
    return (pd.Timestamp(value) + pd.to_timedelta(hour_offset)).strftime('%Y-%m-%d %H:%M:%S')


def _prepare_showcase_equity_df(df: pd.DataFrame, hour_offset: str) -> pd.DataFrame:
    """
    将原始资金曲线转换为晒单接口使用的标准结构。

    Args:
        df: 从 `equity.pkl` 读取的原始资金曲线。
        hour_offset: 账户时区偏移，用于展示时间修正。

    Returns:
        pd.DataFrame: 字段名与 `basic_code_account_statistics` 尽量保持一致的资金曲线。
    """
    equity_df = df.sort_values('time').reset_index(drop=True).copy()
    if equity_df.empty:
        return equity_df

    equity_df['净值'] = pd.to_numeric(equity_df['净值'])
    equity_df['display_time'] = (
        equity_df['time'] + pd.to_timedelta(hour_offset)
    ).dt.strftime('%Y-%m-%d %H:%M:%S')
    equity_df['net'] = (100 * (equity_df['净值'] / equity_df['净值'].iloc[0] - 1)).round(2)
    # 这里只保留晒单页真正需要的衍生指标：收益率和区间回撤。
    equity_df['max2here'] = equity_df['净值'].cummax()
    equity_df['dd2here'] = ((equity_df['净值'] / equity_df['max2here'] - 1) * 100).round(2)

    rename_map = {
        '账户总净值': 'equity_amount',
        '多头选币': 'long_coin_num',
        '空头选币': 'short_coin_num',
    }
    for raw_col, target_col in rename_map.items():
        if raw_col in equity_df.columns:
            equity_df[target_col] = pd.to_numeric(equity_df[raw_col])

    for col in ['long_ratio', 'short_ratio', 'empty_ratio', 'long_coin_num', 'short_coin_num']:
        if col in equity_df.columns:
            equity_df[col] = pd.to_numeric(equity_df[col])

    # ===== 多空敞口 =====
    # 与原统计接口保持一致：正值记为多头敞口，负值记为空头敞口。
    if 'exposure' in equity_df.columns:
        exposure_pct = pd.to_numeric(equity_df['exposure']) * 100
        equity_df['exposure_long'] = exposure_pct.clip(lower=0).round(2)
        equity_df['exposure_short'] = exposure_pct.clip(upper=0).round(2)

    return equity_df


def _select_summary_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    选择用于汇总指标计算的资金曲线。

    Args:
        df: 已标准化的资金曲线。

    Returns:
        pd.DataFrame: 优先使用 `type == log` 的日志点；缺失时回退到全量曲线。
    """
    if 'type' in df.columns:
        log_df = df[df['type'] == 'log'].copy()
        if not log_df.empty:
            return log_df
    return df


def _filter_equity_by_days(df: pd.DataFrame, query_days: int) -> pd.DataFrame:
    """
    根据 query_days 裁切资金曲线。

    Args:
        df: 已标准化的资金曲线。
        query_days: 最近 N 天；0 或 None 表示返回全量。

    Returns:
        pd.DataFrame: 裁切后的资金曲线。
    """
    if not query_days:
        return df.copy()
    return df[df['time'] >= datetime.now() - pd.Timedelta(days=query_days)].copy()


def _build_equity_payload(df: pd.DataFrame) -> dict:
    """
    将最近区间的资金曲线转为前端可直接使用的 dict-of-list 结构。

    Args:
        df: 裁切后的资金曲线。

    Returns:
        dict: 与 `basic_code_account_statistics` 风格一致、但只保留晒单页需要字段的 `equity` 结构。
    """
    columns = [
        'net', 'long_ratio', 'short_ratio', 'empty_ratio',
        'long_coin_num', 'short_coin_num', 'exposure_long', 'exposure_short',
    ]
    if df.empty:
        data = {'time': []}
        for col in columns:
            data[col] = []
        return data

    result = {'time': df['display_time'].tolist()}
    for col in columns:
        if col in df.columns:
            result[col] = [_round_nullable(value) for value in df[col].tolist()]
        else:
            result[col] = []
    return result


def process_account_showcase_statistics(framework_status, account_name: str, query_days: int) -> dict:
    """
    获取指定账户的晒单统计数据。

    Args:
        framework_status: 框架状态对象，内部包含框架 ID、名称和本地路径。
        account_name: 目标账户名称。
        query_days: 前端选择的最近 N 天；0 表示查看全部资金曲线。

    Returns:
        dict: 单账户晒单页所需的扁平统计数据。
    """
    logger.info(
        f"处理账户晒单统计: {framework_status.framework_name} ({framework_status.framework_id}) / {account_name}"
    )

    if not framework_status.path:
        raise FileNotFoundError(f"框架 {framework_status.framework_id} 未下载完成")

    account_json_path = Path(framework_status.path) / 'accounts' / f'{account_name}.json'
    if not account_json_path.exists():
        raise FileNotFoundError(f"账户 {account_name} 配置文件不存在")

    account_info_path = Path(framework_status.path) / 'data' / account_name / '账户信息'
    if not account_info_path.exists():
        raise FileNotFoundError(f"账户 {account_name} 暂无账户统计数据")

    cache_key = ('showcase', framework_status.framework_id, account_name, query_days)
    current_mtimes = _collect_showcase_file_mtimes(account_json_path, account_info_path)
    cached = _showcase_statistics_cache.get(cache_key)
    if cached and _is_showcase_cache_valid(cached, current_mtimes):
        return cached['data']

    account_json = json.loads(account_json_path.read_text(encoding='utf-8'))
    hour_offset = account_json.get('account_config', {}).get('hour_offset', '0h')

    equity_path = account_info_path / 'equity.pkl'
    if not equity_path.exists():
        raise FileNotFoundError(f"账户 {account_name} 暂无资金曲线数据")

    equity_df: pd.DataFrame = pd.read_pickle(equity_path)
    if equity_df.empty:
        raise ValueError(f"账户 {account_name} 资金曲线为空")

    # ===== 先构造全量曲线，再裁切最近 N 天曲线 =====
    # 头部汇总指标必须基于全量曲线计算；图表区域则只返回最近 query_days 的数据。
    full_df = _prepare_showcase_equity_df(equity_df, hour_offset)
    summary_df = _select_summary_df(full_df)
    period_df = _filter_equity_by_days(full_df, query_days)

    start_time = summary_df.iloc[0]['time']
    end_time = summary_df.iloc[-1]['time']
    running_days = max((end_time.date() - start_time.date()).days + 1, 1)
    duration_days = max((end_time - start_time).total_seconds() / 86400, 1 / 24)

    start_net = summary_df.iloc[0]['净值']
    end_net = summary_df.iloc[-1]['净值']
    eq_annualized = None
    if start_net > 0 and end_net > 0:
        eq_annualized = _round_nullable((end_net / start_net) ** (365 / duration_days) * 100 - 100)

    last_24h_df = summary_df[summary_df['time'] > summary_df['time'].max() - pd.Timedelta(hours=24)]
    eq_pct_24h = None
    if len(last_24h_df) >= 2 and 'equity_amount' in last_24h_df.columns:
        start_equity = last_24h_df.iloc[0].get('equity_amount')
        end_equity = last_24h_df.iloc[-1].get('equity_amount')
        if start_equity not in [None, 0] and end_equity is not None:
            eq_pct_24h = _round_nullable(100 * (end_equity / start_equity - 1))

    current_row = full_df.iloc[-1]
    end_at = _format_equity_time(end_time, hour_offset)
    is_running = pd.Timestamp(end_time) >= pd.Timestamp.now() - pd.Timedelta(hours=24)

    # ===== 外层当前快照修正 =====
    # 1. 空仓比例由多头/空头反推，避免四舍五入后出现 long + short + empty != 1。
    # 2. 账户停运时，外层展示的当前持仓、敞口、选币数量和最近 24h 收益统一归零；
    #    但历史曲线 `equity` 仍然保留真实数据，便于前端继续展示历史表现。
    if is_running:
        current_long_ratio = _round_nullable(current_row.get('long_ratio'))
        current_short_ratio = _round_nullable(current_row.get('short_ratio'))
        current_empty_ratio = None
        if current_long_ratio is not None and current_short_ratio is not None:
            current_empty_ratio = _round_nullable(max(0, 1 - (current_long_ratio + current_short_ratio)))

        current_long_coin_num = _round_nullable(current_row.get('long_coin_num'))
        current_short_coin_num = _round_nullable(current_row.get('short_coin_num'))
        current_exposure_long = _round_nullable(current_row.get('exposure_long'))
        current_exposure_short = _round_nullable(current_row.get('exposure_short'))
        current_eq_pct_24h = 0 if eq_pct_24h is None else eq_pct_24h
    else:
        current_long_ratio = 0
        current_short_ratio = 0
        current_empty_ratio = 0
        current_long_coin_num = 0
        current_short_coin_num = 0
        current_exposure_long = 0
        current_exposure_short = 0
        current_eq_pct_24h = 0

    result = {
        'framework_id': framework_status.framework_id,
        'framework_name': framework_status.framework_name,
        'account_name': account_name,
        'strategy_name': account_json.get('strategy_name'),
        'query_days': query_days,
        'status_text': '运行中' if is_running else '已停止',
        'running_days': running_days,
        'start_at': _format_equity_time(start_time, hour_offset),
        'end_at': end_at,
        'eq_pct': _round_nullable(100 * (end_net / start_net - 1)),
        'eq_drawdown': _round_nullable(full_df['dd2here'].min()),
        'eq_annualized': eq_annualized,
        'eq_pct_24h': current_eq_pct_24h,
        'long_ratio': current_long_ratio,
        'short_ratio': current_short_ratio,
        'empty_ratio': current_empty_ratio,
        'long_coin_num': current_long_coin_num,
        'short_coin_num': current_short_coin_num,
        'exposure_long': current_exposure_long,
        'exposure_short': current_exposure_short,
        'equity': _build_equity_payload(period_df),
    }

    _showcase_statistics_cache[cache_key] = {
        'data': result,
        'mtimes': current_mtimes,
        'ts': time_mod.time(),
    }
    return result
