from pandas import show_versions

from utils.log_kit import logger, divider

sys_version = '0.5.0'
sys_name = 'qronos'
build_version = f'v{sys_version}.20251121'

def version_prompt():
    show_versions()
    divider('[SYSTEM INFO]', '-')
    logger.debug(f'# VERSION:\t{sys_name}({sys_version})')
    logger.debug(f'# BUILD:\t{build_version}')
    divider('[SYSTEM INFO]', '-')
