from typing import Optional, Any, List, Dict

from pydantic import BaseModel

from model.enum_kit import StatusEnum, AccountTypeEnum


class LoginRequest(BaseModel):
    google_secret_key: Optional[str] = None  # 首次登录时必传
    code: str


class ResponseModel(BaseModel):
    msg: str = "success"
    code: int = 200
    data: Optional[Any] = None

    @classmethod
    def ok(cls, data: Any = None, msg: str = "success", code: int = 200):
        return cls(msg=msg, code=code, data=data)

    @classmethod
    def error(cls, msg: str = "error", code: int = 400):
        return cls(msg=msg, code=code, data=None)


class UseApiModel(BaseModel):
    kline: bool = False
    coin_cap: bool = False


class DataCenterCfgModel(BaseModel):
    id: str
    kline_count_1h: int
    error_webhook_url: str
    use_api: UseApiModel
    data_api_uuid: Optional[str] = None
    data_api_key: Optional[str] = None
    enabled_hour_offsets: List[str]
    funding_rate: bool = True
    is_first: bool = True


class BasicCodeStatusModel(BaseModel):
    id: str
    status: StatusEnum
    type: str
    time: str


class BasicCodeOperateModel(BaseModel):
    framework_id: str | int
    pm_id: Optional[str | int] = None
    secret_key: Optional[str] = None
    lines: int = 50
    type: str


class AccountConfigModel(BaseModel):
    apiKey: Optional[str]
    secret: Optional[str]
    account_type: AccountTypeEnum
    seed_coins: Optional[List] = None  # 统一账户模式且存在底仓时，才会有配置
    coin_margin: Optional[Dict] = {}
    hour_offset: str = '0m'
    order_spot_money_limit: int = 10
    order_swap_money_limit: int = 5
    max_one_order_amount: int = 100
    twap_interval: int = 2
    if_use_bnb_burn: bool = True
    buy_bnb_value: int = 11
    if_transfer_bnb: bool = True
    wechat_webhook_url: str = ''
    base_margin: dict = {'USDT': 1}  # 基本稳定币保证金


class AccountModel(BaseModel):
    framework_id: str
    account_name: str
    account_config: AccountConfigModel
    strategy_name: Optional[str] = ''
    strategy_config: Optional[Dict] = {}
    strategy_pool: Optional[List] = []
    min_kline_num: int = 168
    get_kline_num: int = 999
    leverage: int | float = 1
    rebalance_mode: Optional[Dict] = None
    black_list: List[str] = []
    white_list: List[str] = []
    is_lock: bool = False


class ApiKeySecretModel(BaseModel):
    framework_id: str
    account_name: str
    keyword: str  # apikey，secret
    total: int  # 分段总数
    sort_id: int  # 分段下标
    content: str  # 分段内容


class Pm2AppModel(BaseModel):
    name: str
    namespace: str
    script: str
    exec_interpreter: str = '~/anaconda3/envs/Alpha/bin/python'  # 默认环境
    merge_logs: bool = False
    watch: bool = False
    error_file: str
    out_file: str
    log_date_format: str = "YYYY-MM-DD HH:mm:ss.SSS Z"


class Pm2CfgModel(BaseModel):
    apps: List[Pm2AppModel]


class FrameworkCfgModel(BaseModel):
    framework_id: str
    realtime_data_path: Optional[str] = ''
    # is_debug: bool = False
    error_webhook_url: str = ''
    factor_col_limit: int = 32
    is_encrypt: bool = False
    is_simulate: Optional[str] = 'none'


class DeviceInfo(BaseModel):
    id: str
    device_type: str
    browser_info: str
    ip_address: str
    last_active_time: str
    created_time: str
    is_current: bool = False
