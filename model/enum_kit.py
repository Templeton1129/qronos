"""
邢不行｜策略分享会
选币策略实盘框架𝓟𝓻𝓸

版权所有 ©️ 邢不行
微信: xbx1717

本代码仅供个人学习使用，未经授权不得复制、修改或用于商业用途。

Author: 邢不行
"""
from enum import Enum


class StatusEnum(str, Enum):
    NOT_DOWNLOADED = 'not_downloaded'
    DOWNLOADING = 'downloading'
    FINISHED = 'finished'
    FAILED = 'failed'


class UploadFolderEnum(str, Enum):
    FACTORS = 'factors'  # 时序因子
    SECTIONS = 'sections'  # 截面因子
    POSITIONS = 'positions'  # 仓管策略
    SIGNALS = 'signals'  # 择时因子


class AccountTypeEnum(str, Enum):
    PORTFOLIO_MARGIN = '统一账户'
    STANDARD = '普通账户'


class DeviceTypeEnum(str, Enum):
    """设备类型枚举"""
    PC = 'pc'
    MOBILE = 'mobile'
    TABLET = 'tablet'


class FrameworkSourceEnum(str, Enum):
    """
    框架来源枚举

    区分框架是官方下载还是用户上传导入，用于 framework_status 表的 source 列。
    """
    OFFICIAL = 'official'  # 官方下载（XBX API）
    IMPORTED = 'imported'  # 用户上传导入
