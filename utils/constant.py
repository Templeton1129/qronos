from utils.path_kit import get_file_path

"""
目录配置
"""
# 临时目录
TMP_PATH = get_file_path('data', 'temp')

# 下载框架根目录
FRAMEWORK_ROOT_PATH = get_file_path('').parent / 'firm'
FRAMEWORK_ROOT_PATH.mkdir(parents=True, exist_ok=True)

"""
额外的请求 url，静态配置
"""

# 请求地址域名前缀
api_qtcls_root_url = 'https://api.quantclass.cn'
# api_qtcls_root_url = 'http://192.168.100.138:3000'

# 获取用户信息
api_qtcls_user_info_url = f'{api_qtcls_root_url}/user/info'

# 获取用户信息v2
api_qtcls_user_info_v2_url = f'{api_qtcls_root_url}/user/info/v2'

# 获取用户 token
api_qtcls_user_login_token_url = f'{api_qtcls_root_url}/user/login/user_token'

# 获取框架版本号
api_qtcls_data_client_basic_code_url = f'{api_qtcls_root_url}/download/data-client/basic-code/v2'

# 获取全量市值数据下载链接
api_qtcls_data_coin_cap_hist_url = f'{api_qtcls_root_url}/api/data/coin-cap/get-hist-download-link'

# 获取下载框架的 ticket
api_qtcls_basic_code_download_ticket_url = f'{api_qtcls_root_url}/download/%s/basic-code-download'

# 获取下载框架链接
api_qtcls_basic_code_download_link_url = f'{api_qtcls_root_url}/download/get-code-download-link/%s'

"""
文件存储路径，静态配置
"""
# 数据库
DB_PATH = get_file_path('data', 'qronos.db')

# 接口请求前缀
PREFIX_FILE = get_file_path('data', 'prefix.txt')

# 框架启动端口
PORT_FILE = get_file_path('data', 'port.txt')

# 上次确认的声明 code 文件
CACHE_CODE_FILE = get_file_path('data', 'code.txt')

# 框架声明 code 文件
LOCAL_CODE_FILE = get_file_path('code.txt')

"""
框架类型
"""
POSITION_TYPE = 'position'
DATA_CENTER_TYPE = 'data_center'

"""
启动实盘的 conda 环境
"""
CONDA_ENV_NAME = 'Alpha'

# Docker容器内的Python环境路径
ALPHA_ENV_PATH = "/opt/alpha_env/bin/python"

# 接口前缀
PREFIX = 'qronos'
