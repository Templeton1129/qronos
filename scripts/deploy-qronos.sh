#!/bin/bash

# 量化交易框架管理系统 - 一键部署脚本
#
# 该脚本集成了Docker安装和框架部署功能：
# 1. 检查当前系统是否安装Docker
# 2. 如果没有Docker，自动安装Docker CE
# 3. 拉取镜像并启动量化交易框架容器
#
# 使用方法：
# ./scripts/deploy-qronos.sh [Docker Hub镜像名] [版本号] [容器名] [--docker-mirror 镜像源]
# 例如: ./scripts/deploy-qronos.sh xbxtempleton/qronos-trading-framework v0.0.1 qronos-app --docker-mirror china

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# 日志函数
log_info() { echo -e "${BLUE}ℹ️  ${NC}$1"; }
log_success() { echo -e "${GREEN}✅ ${NC}$1"; }
log_warning() { echo -e "${YELLOW}⚠️  ${NC}$1"; }
log_error() { echo -e "${RED}❌ ${NC}$1"; }
log_step() { echo -e "${PURPLE}[STEP]${NC} $1"; }

# 默认参数
DOCKER_HUB_IMAGE=""
VERSION=""
CONTAINER_NAME=""
DOCKER_MIRROR="china"  # 默认使用中国镜像源加速
SKIP_DOCKER_INSTALL=false
SKIP_SWAP_CHECK=false
AUTO_SETUP_SWAP=false

# 解析命令行参数
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --docker-mirror)
                DOCKER_MIRROR="$2"
                shift 2
                ;;
            --skip-docker-install)
                SKIP_DOCKER_INSTALL=true
                shift
                ;;
            --skip-swap-check)
                SKIP_SWAP_CHECK=true
                shift
                ;;
            --auto-setup-swap)
                AUTO_SETUP_SWAP=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            -*)
                log_error "未知参数: $1"
                show_help
                exit 1
                ;;
            *)
                if [[ -z "$DOCKER_HUB_IMAGE" ]]; then
                    DOCKER_HUB_IMAGE="$1"
                elif [[ -z "$VERSION" ]]; then
                    VERSION="$1"
                elif [[ -z "$CONTAINER_NAME" ]]; then
                    CONTAINER_NAME="$1"
                else
                    log_error "过多的参数: $1"
                    show_help
                    exit 1
                fi
                shift
                ;;
        esac
    done
    
    # 设置默认值（确保变量正确初始化）
    if [[ -z "$DOCKER_HUB_IMAGE" ]]; then
        DOCKER_HUB_IMAGE="xbxtempleton/qronos-trading-framework"
    fi
    
    if [[ -z "$VERSION" ]]; then
        VERSION="latest"
    fi
    
    if [[ -z "$CONTAINER_NAME" ]]; then
        CONTAINER_NAME="qronos-app"
    fi
    
    # 布尔值默认设置
    SKIP_SWAP_CHECK=${SKIP_SWAP_CHECK:-false}
    AUTO_SETUP_SWAP=${AUTO_SETUP_SWAP:-false}
    
    # 显示最终使用的参数
    log_info "使用配置："
    log_info "  镜像名称: $DOCKER_HUB_IMAGE"
    log_info "  版本标签: $VERSION"
    log_info "  容器名称: $CONTAINER_NAME"
    log_info "  镜像源: $DOCKER_MIRROR"
}

# 显示帮助信息
show_help() {
    echo "量化交易框架管理系统 - 一键部署脚本"
    echo ""
    echo "用法: $0 [镜像名] [版本号] [容器名] [选项]"
    echo ""
    echo "参数:"
    echo "  镜像名       Docker Hub 镜像名 (默认: xbxtempleton/qronos-trading-framework)"
    echo "  版本号       镜像版本标签 (默认: latest)"
    echo "  容器名       容器名称 (默认: qronos-app)"
    echo ""
    echo "选项:"
    echo "  --docker-mirror <源>    Docker镜像源 (official|china|tencent|aliyun|ustc) [默认: china]"
    echo "  --skip-docker-install   跳过Docker安装检查"
    echo "  --skip-swap-check       跳过内存检查"
    echo "  --auto-setup-swap       自动设置虚拟内存"
    echo "  --help, -h              显示此帮助信息"
    echo ""
    echo "Docker镜像源说明:"
    echo "  official         Docker官方源"
    echo "  china           中科大镜像源 (推荐)"
    echo "  tencent         腾讯云镜像源"
    echo "  aliyun          阿里云镜像源"
    echo "  ustc            中科大镜像源"
    echo ""
    echo "内存配置说明:"
    echo "  该脚本会自动检测系统内存配置，并在需要时推荐配置虚拟内存"
    echo "  虚拟内存配置建议："
    echo "    - 2GB物理内存：建议配置6GB虚拟内存"
    echo "    - 4GB物理内存：建议配置4GB虚拟内存"
    echo "    - 8GB以上：通常无需额外虚拟内存"
    echo ""
    echo "示例:"
    echo "  $0                                                   # 使用默认参数"
    echo "  $0 myuser/qronos v1.0.0 my-container                # 指定镜像和容器名"
    echo "  $0 --docker-mirror aliyun                           # 使用阿里云镜像源"
    echo "  $0 --auto-setup-swap                                # 自动配置虚拟内存"
    echo "  $0 --skip-swap-check                                # 跳过内存检查"
    echo "  $0 myuser/qronos latest qronos --auto-setup-swap    # 完整参数示例"
    echo ""
    echo "注意事项:"
    echo "  - 内存检查和虚拟内存配置仅在Linux系统上执行"
    echo "  - 配置虚拟内存需要root权限"
    echo "  - 虚拟内存配置会占用磁盘空间，请确保有足够的存储空间"
    echo "  - 虚拟内存虽然可以缓解内存不足，但会影响性能"
}

# ============================================================================
# Docker 检查和安装功能
# ============================================================================

# 检查是否为root用户或有sudo权限
check_privileges() {
    if [[ $EUID -eq 0 ]]; then
        log_info "以root用户身份运行"
        SUDO_CMD=""
    elif sudo -n true 2>/dev/null; then
        log_info "检测到sudo权限"
        SUDO_CMD="sudo"
    else
        log_error "此脚本需要root权限或sudo权限来安装Docker"
        echo "请使用以下方式运行："
        echo "  sudo $0 $@"
        exit 1
    fi
}

# 检测操作系统
detect_operating_system() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [[ -f /etc/os-release ]]; then
            # 保存当前的VERSION变量值（Docker镜像版本）
            local SAVED_VERSION="$VERSION"
            
            # 读取系统信息
            source /etc/os-release
            
            # 使用系统信息设置操作系统变量
            OS_ID="$ID"
            OS_VERSION="$VERSION_ID"
            OS_CODENAME="${VERSION_CODENAME:-}"
            
            # 恢复Docker镜像版本变量
            VERSION="$SAVED_VERSION"
            
            log_info "检测到操作系统: $ID $VERSION_ID"
        else
            log_error "无法检测操作系统版本"
            exit 1
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS_ID="macos"
        OS_VERSION=$(sw_vers -productVersion)
        log_info "检测到操作系统: macOS $OS_VERSION"
        log_info "macOS用户请手动安装Docker Desktop"
        log_info "下载地址: https://www.docker.com/products/docker-desktop"
        exit 1
    else
        log_error "不支持的操作系统: $OSTYPE"
        exit 1
    fi
}

# 检查Docker是否已安装
check_docker_installation() {
    if command -v docker >/dev/null 2>&1; then
        if docker info > /dev/null 2>&1; then
            DOCKER_VERSION=$(docker --version 2>/dev/null || echo "未知版本")
            log_success "Docker已安装并运行: $DOCKER_VERSION"
            return 0
        else
            log_warning "Docker已安装但未运行，尝试启动Docker服务..."
            if [[ "$OS_ID" == "ubuntu" ]] || [[ "$OS_ID" == "debian" ]]; then
                $SUDO_CMD systemctl start docker || {
                    log_error "无法启动Docker服务"
                    return 1
                }
                sleep 3
                if docker info > /dev/null 2>&1; then
                    log_success "Docker服务已启动"
                    return 0
                fi
            fi
            log_error "Docker服务启动失败"
            return 1
        fi
    else
        log_info "Docker未安装"
        return 1
    fi
}

# 配置镜像源信息
configure_docker_mirror() {
    log_info "配置Docker镜像源：$DOCKER_MIRROR"
    
    case $DOCKER_MIRROR in
        "official")
            DOCKER_DOWNLOAD_URL="https://download.docker.com"
            APT_SOURCE_URL="https://download.docker.com/linux/ubuntu"
            GPG_KEY_URL="https://download.docker.com/linux/ubuntu/gpg"
            REGISTRY_MIRRORS=""
            log_info "使用Docker官方源"
            ;;
        "china"|"ustc")
            DOCKER_DOWNLOAD_URL="https://mirrors.ustc.edu.cn/docker-ce"
            APT_SOURCE_URL="https://mirrors.ustc.edu.cn/docker-ce/linux/ubuntu"
            GPG_KEY_URL="https://mirrors.ustc.edu.cn/docker-ce/linux/ubuntu/gpg"
            REGISTRY_MIRRORS='["https://docker.mirrors.ustc.edu.cn"]'
            log_info "使用中科大镜像源"
            ;;
        "tencent")
            DOCKER_DOWNLOAD_URL="https://mirrors.cloud.tencent.com/docker-ce"
            APT_SOURCE_URL="https://mirrors.cloud.tencent.com/docker-ce/linux/ubuntu"
            GPG_KEY_URL="https://mirrors.cloud.tencent.com/docker-ce/linux/ubuntu/gpg"
            REGISTRY_MIRRORS='["https://mirror.ccs.tencentyun.com"]'
            log_info "使用腾讯云镜像源"
            ;;
        "aliyun")
            DOCKER_DOWNLOAD_URL="https://mirrors.aliyun.com/docker-ce"
            APT_SOURCE_URL="https://mirrors.aliyun.com/docker-ce/linux/ubuntu"
            GPG_KEY_URL="https://mirrors.aliyun.com/docker-ce/linux/ubuntu/gpg"
            REGISTRY_MIRRORS='["https://registry.cn-hangzhou.aliyuncs.com"]'
            log_info "使用阿里云镜像源"
            ;;
        *)
            log_error "不支持的镜像源：$DOCKER_MIRROR"
            log_info "支持的镜像源：official, china, tencent, aliyun, ustc"
            exit 1
            ;;
    esac
}

# 安装Docker (Ubuntu/Debian)
install_docker_ubuntu() {
    log_step "在Ubuntu/Debian系统上安装Docker..."
    
    # 移除旧版本
    log_info "移除旧版本的Docker包..."
    OLD_PACKAGES=("docker" "docker-engine" "docker.io" "docker-ce-cli" "docker-ce" "containerd" "runc")
    for package in "${OLD_PACKAGES[@]}"; do
        if dpkg -l | grep -q "^ii.*$package"; then
            log_info "移除包：$package"
            $SUDO_CMD apt-get remove -y "$package" 2>/dev/null || true
        fi
    done
    $SUDO_CMD apt-get autoremove -y 2>/dev/null || true
    
    # 更新系统包
    log_info "更新系统包列表..."
    $SUDO_CMD apt-get update
    
    log_info "安装必要的依赖包..."
    $SUDO_CMD apt-get install -y \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg \
        lsb-release \
        software-properties-common
    
    # 添加Docker官方GPG密钥
    log_info "添加Docker GPG密钥..."
    $SUDO_CMD mkdir -p /etc/apt/keyrings
    curl -fsSL "$GPG_KEY_URL" | $SUDO_CMD gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    $SUDO_CMD chmod a+r /etc/apt/keyrings/docker.gpg
    
    # 添加Docker APT源
    log_info "添加Docker APT源..."
    echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] $APT_SOURCE_URL \
        $(lsb_release -cs) stable" | $SUDO_CMD tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # 更新包列表
    $SUDO_CMD apt-get update
    
    # 安装Docker CE
    log_info "安装Docker CE..."
    $SUDO_CMD apt-get install -y \
        docker-ce \
        docker-ce-cli \
        containerd.io \
        docker-buildx-plugin \
        docker-compose-plugin
    
    # 配置Docker镜像拉取镜像源
    if [[ -n "$REGISTRY_MIRRORS" ]]; then
        log_info "配置Docker容器镜像拉取镜像源..."
        $SUDO_CMD mkdir -p /etc/docker
        $SUDO_CMD tee /etc/docker/daemon.json > /dev/null <<EOF
{
  "registry-mirrors": $REGISTRY_MIRRORS,
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "3"
  },
  "storage-driver": "overlay2"
}
EOF
        log_success "Docker镜像源配置完成"
    fi
    
    # 启动Docker服务
    log_info "启动Docker服务..."
    $SUDO_CMD systemctl start docker
    $SUDO_CMD systemctl enable docker
    
    # 如果配置了镜像源，重启Docker服务
    if [[ -n "$REGISTRY_MIRRORS" ]]; then
        log_info "重启Docker服务以应用镜像源配置..."
        $SUDO_CMD systemctl restart docker
    fi
    
    # 配置用户权限
    if [[ $EUID -ne 0 ]]; then
        CURRENT_USER=$(whoami)
        log_info "为用户 '$CURRENT_USER' 配置Docker权限..."
        $SUDO_CMD usermod -aG docker "$CURRENT_USER"
        log_warning "请注意：需要重新登录或运行 'newgrp docker' 使权限生效"
    fi
    
    # 验证安装
    sleep 3
    if docker info > /dev/null 2>&1; then
        DOCKER_VERSION=$(docker --version)
        log_success "Docker安装成功: $DOCKER_VERSION"
        
        # 测试hello-world
        log_info "运行Docker hello-world测试..."
        if $SUDO_CMD docker run --rm hello-world >/dev/null 2>&1; then
            log_success "Docker安装验证通过"
        else
            log_warning "Docker hello-world测试失败，但Docker已正常安装"
        fi
    else
        log_error "Docker安装后验证失败"
        return 1
    fi
}

# 安装Docker主函数
install_docker() {
    if [[ "$SKIP_DOCKER_INSTALL" == "true" ]]; then
        log_info "跳过Docker安装"
        return 0
    fi
    
    log_step "开始Docker安装流程..."
    
    # 检查权限
    check_privileges
    
    # 检测操作系统
    detect_operating_system
    
    # 配置镜像源
    configure_docker_mirror
    
    # 根据操作系统安装Docker
    case $OS_ID in
        "ubuntu"|"debian")
            install_docker_ubuntu
            ;;
        *)
            log_error "不支持的操作系统：$OS_ID"
            log_info "请手动安装Docker"
            exit 1
            ;;
    esac
}

# ============================================================================
# 内存检查和虚拟内存配置功能
# ============================================================================

# 检查系统内存配置
check_memory_configuration() {
    if [[ "$SKIP_SWAP_CHECK" == "true" ]]; then
        log_info "跳过内存检查"
        return 0
    fi
    
    log_step "检查系统内存配置..."
    
    # 获取内存信息
    TOTAL_MEM_MB=$(free -m | awk '/^Mem:/ {print $2}')
    TOTAL_MEM_GB=$((TOTAL_MEM_MB / 1024))
    AVAILABLE_MEM_MB=$(free -m | awk '/^Mem:/ {print $7}')
    CURRENT_SWAP_MB=$(free -m | awk '/^Swap:/ {print $2}')
    CURRENT_SWAP_GB=$((CURRENT_SWAP_MB / 1024))
    
    # 计算推荐的虚拟内存大小
    if [[ $TOTAL_MEM_MB -le 2048 ]]; then
        RECOMMENDED_SWAP_GB=6
        MEMORY_STATUS="低"
    elif [[ $TOTAL_MEM_MB -le 4096 ]]; then
        RECOMMENDED_SWAP_GB=4
        MEMORY_STATUS="中等"
    elif [[ $TOTAL_MEM_MB -le 8192 ]]; then
        RECOMMENDED_SWAP_GB=2
        MEMORY_STATUS="良好"
    else
        RECOMMENDED_SWAP_GB=0
        MEMORY_STATUS="充足"
    fi
    
    # 显示内存状态
    echo ""
    echo "🖥️  系统内存状态:"
    echo "   物理内存: ${TOTAL_MEM_GB}GB (${TOTAL_MEM_MB}MB)"
    echo "   可用内存: $((AVAILABLE_MEM_MB / 1024))GB (${AVAILABLE_MEM_MB}MB)"
    echo "   当前Swap: ${CURRENT_SWAP_GB}GB (${CURRENT_SWAP_MB}MB)"
    echo "   内存状态: ${MEMORY_STATUS}"
    echo ""
    
    # 判断是否需要配置虚拟内存
    if [[ $TOTAL_MEM_MB -le 4096 ]] && [[ $CURRENT_SWAP_MB -lt $((RECOMMENDED_SWAP_GB * 1024)) ]]; then
        log_warning "检测到内存可能不足，运行量化框架时可能出现内存溢出"
        echo ""
        echo "⚠️  内存不足风险:"
        echo "   - 量化框架通常需要较多内存来处理数据"
        echo "   - 当前内存配置可能导致容器被系统终止"
        echo "   - 建议配置虚拟内存来缓解内存压力"
        echo ""
        echo "💡 推荐配置:"
        echo "   - 建议Swap大小: ${RECOMMENDED_SWAP_GB}GB"
        echo "   - 配置后总虚拟内存: $((TOTAL_MEM_GB + RECOMMENDED_SWAP_GB))GB"
        
        if [[ "$AUTO_SETUP_SWAP" == "true" ]]; then
            log_info "自动配置模式：开始设置虚拟内存..."
            setup_swap_automatically
        else
            echo ""
            read -p "是否现在配置虚拟内存？(y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                setup_swap_interactively
            else
                log_warning "跳过虚拟内存配置，请注意监控内存使用情况"
                echo ""
                echo "📋 手动配置虚拟内存的命令:"
                echo "   sudo fallocate -l ${RECOMMENDED_SWAP_GB}G /swapfile"
                echo "   sudo chmod 600 /swapfile"
                echo "   sudo mkswap /swapfile"
                echo "   sudo swapon /swapfile"
                echo "   echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab"
            fi
        fi
    else
        log_success "当前内存配置良好，无需额外配置虚拟内存"
    fi
}

# 自动设置虚拟内存
setup_swap_automatically() {
    log_step "自动配置虚拟内存..."
    
    # 直接内置虚拟内存配置功能
    log_info "开始配置 ${RECOMMENDED_SWAP_GB}GB 虚拟内存..."
    
    local swap_size_gb=$RECOMMENDED_SWAP_GB
    local swap_file="/swapfile"
    
    # 检查是否已有足够的swap空间
    local current_swap_gb=$((CURRENT_SWAP_MB / 1024))
    if [[ $current_swap_gb -ge $swap_size_gb ]]; then
        log_success "已有足够的虚拟内存 (${current_swap_gb}GB >= ${swap_size_gb}GB)"
        return 0
    fi
    
    # 检查磁盘空间
    log_info "检查磁盘空间..."
    local available_space_gb=$(df / | awk 'NR==2 {printf "%.0f", $4/1024/1024}')
    local required_space_gb=$((swap_size_gb + 1))  # 额外1GB空间作为缓冲
    
    if [[ $available_space_gb -lt $required_space_gb ]]; then
        log_error "磁盘空间不足！需要至少 ${required_space_gb}GB，可用 ${available_space_gb}GB"
        return 1
    fi
    
    log_info "磁盘空间检查通过：可用 ${available_space_gb}GB，需要 ${required_space_gb}GB"
    
    # 检查是否存在现有的swapfile
    if [[ -f "$swap_file" ]]; then
        log_warning "发现现有的swap文件，先关闭..."
        $SUDO_CMD swapoff "$swap_file" 2>/dev/null || true
        $SUDO_CMD rm -f "$swap_file"
    fi
    
    # 创建swap文件
    log_info "创建 ${swap_size_gb}GB swap文件..."
    if ! $SUDO_CMD fallocate -l "${swap_size_gb}G" "$swap_file" 2>/dev/null; then
        log_warning "fallocate失败，使用dd命令创建swap文件..."
        if ! $SUDO_CMD dd if=/dev/zero of="$swap_file" bs=1M count=$((swap_size_gb * 1024)) status=progress; then
            log_error "创建swap文件失败"
            return 1
        fi
    fi
    
    # 设置swap文件权限
    log_info "设置swap文件权限..."
    $SUDO_CMD chmod 600 "$swap_file"
    
    # 创建swap格式
    log_info "格式化swap文件..."
    if ! $SUDO_CMD mkswap "$swap_file"; then
        log_error "格式化swap文件失败"
        return 1
    fi
    
    # 启用swap
    log_info "启用swap文件..."
    if ! $SUDO_CMD swapon "$swap_file"; then
        log_error "启用swap文件失败"
        return 1
    fi
    
    # 添加到fstab以便持久化
    log_info "配置开机自动挂载..."
    if ! grep -q "$swap_file" /etc/fstab 2>/dev/null; then
        echo "$swap_file none swap sw 0 0" | $SUDO_CMD tee -a /etc/fstab > /dev/null
        log_info "已添加到 /etc/fstab"
    else
        log_info "已存在于 /etc/fstab 中"
    fi
    
    # 优化swappiness值
    log_info "优化虚拟内存参数..."
    echo "vm.swappiness=10" | $SUDO_CMD tee /etc/sysctl.d/99-qronos-swap.conf > /dev/null
    $SUDO_CMD sysctl vm.swappiness=10 > /dev/null
    
    # 验证配置结果
    sleep 2
    local new_swap_mb=$(free -m | awk '/^Swap:/ {print $2}')
    local new_swap_gb=$((new_swap_mb / 1024))
    
    if [[ $new_swap_gb -ge $swap_size_gb ]]; then
        log_success "虚拟内存配置成功！"
        
        # 显示最终配置
        echo ""
        echo "✨ 虚拟内存配置结果:"
        echo "   虚拟内存文件: $swap_file"
        echo "   虚拟内存大小: ${new_swap_gb}GB"
        echo "   Swappiness: 10 (已优化)"
        echo "   总可用内存: $((TOTAL_MEM_GB + new_swap_gb))GB"
        echo "   持久化配置: 已启用"
        return 0
    else
        log_error "虚拟内存配置验证失败"
        return 1
    fi
}

# 交互式设置虚拟内存
setup_swap_interactively() {
    log_step "交互式配置虚拟内存..."
    
    echo ""
    echo "📋 虚拟内存配置选项:"
    echo "   1. 推荐配置: ${RECOMMENDED_SWAP_GB}GB (推荐)"
    echo "   2. 自定义大小"
    echo "   3. 跳过配置"
    echo ""
    
    read -p "请选择配置选项 (1-3): " -n 1 -r
    echo
    
    local swap_size_gb
    case $REPLY in
        1)
            swap_size_gb=$RECOMMENDED_SWAP_GB
            ;;
        2)
            read -p "请输入Swap大小（GB）: " swap_size_gb
            # 验证输入
            if ! [[ "$swap_size_gb" =~ ^[0-9]+$ ]] || [[ $swap_size_gb -lt 1 ]] || [[ $swap_size_gb -gt 32 ]]; then
                log_error "无效的大小，使用推荐值: ${RECOMMENDED_SWAP_GB}GB"
                swap_size_gb=$RECOMMENDED_SWAP_GB
            fi
            ;;
        3)
            log_info "跳过虚拟内存配置"
            return 0
            ;;
        *)
            log_warning "无效选择，使用推荐配置: ${RECOMMENDED_SWAP_GB}GB"
            swap_size_gb=$RECOMMENDED_SWAP_GB
            ;;
    esac
    
    # 使用内置函数配置虚拟内存
    RECOMMENDED_SWAP_GB=$swap_size_gb  # 临时修改推荐值
    setup_swap_automatically
}

# ============================================================================
# 框架部署功能
# ============================================================================

# 获取本地IP地址函数
get_local_ip() {
    local ip=""
    
    # 方法1: 尝试获取主要网络接口的IP
    if command -v ip >/dev/null 2>&1; then
        # Linux系统使用ip命令
        ip=$(ip route get 8.8.8.8 2>/dev/null | grep -oP 'src \K[0-9.]+' | head -1)
    elif command -v route >/dev/null 2>&1; then
        # macOS/BSD系统使用route命令
        ip=$(route get default 2>/dev/null | grep interface | awk '{print $2}' | xargs ifconfig 2>/dev/null | grep 'inet ' | grep -v '127.0.0.1' | awk '{print $2}' | head -1)
    fi
    
    # 方法2: 如果上面失败，尝试使用ifconfig
    if [[ -z "$ip" ]] && command -v ifconfig >/dev/null 2>&1; then
        # 获取第一个非回环网络接口的IP
        ip=$(ifconfig 2>/dev/null | grep 'inet ' | grep -v '127.0.0.1' | awk '{print $2}' | head -1)
    fi
    
    # 方法3: 备用方案，使用hostname命令
    if [[ -z "$ip" ]] && command -v hostname >/dev/null 2>&1; then
        ip=$(hostname -I 2>/dev/null | awk '{print $1}')
    fi
    
    # 如果仍然无法获取，使用localhost作为备用
    if [[ -z "$ip" ]]; then
        ip="localhost"
    fi
    
    echo "$ip"
}

# 获取公网IP地址函数
get_public_ip() {
    local ip=""
    
    if command -v curl >/dev/null 2>&1; then
        # 尝试多个公网IP查询服务
        local services=(
            "ipinfo.io/ip"
            "ifconfig.me"
            "icanhazip.com"
            "ipecho.net/plain"
            "checkip.amazonaws.com"
            "httpbin.org/ip"
        )
        
        for service in "${services[@]}"; do
            if [[ "$service" == "httpbin.org/ip" ]]; then
                # httpbin返回JSON格式，需要解析
                ip=$(curl -s --connect-timeout 5 --max-time 10 "https://$service" 2>/dev/null | grep -o '"origin":"[^"]*"' | cut -d'"' -f4 | cut -d',' -f1)
            else
                ip=$(curl -s --connect-timeout 5 --max-time 10 "https://$service" 2>/dev/null | tr -d '\n\r' | grep -E '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$')
            fi
            
            # 验证IP格式
            if [[ "$ip" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
                break
            else
                ip=""
            fi
        done
    fi
    
    echo "$ip"
}

# 环境权限检查和提示
check_deployment_environment() {
    log_step "检查部署环境..."
    
    # 获取IP地址信息
    LOCAL_IP=$(get_local_ip)
    PUBLIC_IP=$(get_public_ip)
    
    # 检查运行环境并给出权限提示
    if [[ "$(uname)" == "Linux" ]]; then
        if [[ "$EUID" -eq 0 ]] && [[ -z "$SUDO_USER" ]]; then
            log_warning "检测到以root用户直接运行脚本"
            log_warning "建议以普通用户身份运行: sudo $0 $@"
        elif [[ "$EUID" -eq 0 ]] && [[ -n "$SUDO_USER" ]]; then
            log_info "检测到通过sudo运行脚本，用户: $SUDO_USER"
        else
            log_info "检测到以普通用户运行脚本，用户: $(whoami)"
            log_warning "如果遇到权限问题，请使用: sudo $0 $@"
        fi
    fi
    
    echo "=========================================="
    echo "量化交易框架管理系统 - 一键部署"
    echo "Docker Hub镜像: ${DOCKER_HUB_IMAGE}"
    echo "版本: ${VERSION}"
    echo "容器名: ${CONTAINER_NAME}"
    echo "完整镜像名: ${DOCKER_HUB_IMAGE}:${VERSION}"
    echo "本地IP: ${LOCAL_IP}"
    if [[ -n "$PUBLIC_IP" ]]; then
        echo "公网IP: ${PUBLIC_IP}"
    else
        echo "公网IP: 无法获取"
    fi
    echo "=========================================="
}

# 设置数据目录权限
setup_data_directories() {
    log_step "设置数据目录..."
    
    # 创建必要的数据目录
    log_info "创建数据目录..."
    mkdir -p ./data/qronos/data ./data/qronos/logs ./data/firm ./data/.pm2
    
    # 检测操作系统并设置权限
    log_info "设置目录权限..."
    if [[ "$(uname)" == "Linux" ]]; then
        # 获取真实用户的UID和GID（即使在sudo环境下）
        if [[ -n "$SUDO_UID" ]] && [[ -n "$SUDO_GID" ]]; then
            # 在sudo环境下，使用SUDO_UID和SUDO_GID
            REAL_UID="$SUDO_UID"
            REAL_GID="$SUDO_GID"
            REAL_USER="$SUDO_USER"
            log_info "检测到sudo环境，真实用户: $REAL_USER (UID: $REAL_UID, GID: $REAL_GID)"
        else
            # 非sudo环境，使用当前用户
            REAL_UID=$(id -u)
            REAL_GID=$(id -g)
            REAL_USER=$(whoami)
            log_info "非sudo环境，当前用户: $REAL_USER (UID: $REAL_UID, GID: $REAL_GID)"
        fi
        
        # 创建数据目录并设置所有者为真实用户
        log_info "设置数据目录所有者为真实用户..."
        chown -R ${REAL_UID}:${REAL_GID} ./data/
        # 设置适当权限：用户读写执行，组读写执行，其他用户读执行
        chmod -R 775 ./data/
        log_info "Linux系统：已设置数据目录所有者为 ${REAL_USER}(${REAL_UID}:${REAL_GID})，权限为775"
        
        CURRENT_UID="$REAL_UID"
        CURRENT_GID="$REAL_GID"
    else
        # macOS/其他系统通常权限处理更宽松
        chmod -R 755 ./data/
        log_info "非Linux系统：已设置数据目录权限为755"
        CURRENT_UID=""
        CURRENT_GID=""
    fi
}

# 拉取镜像
pull_docker_image() {
    log_step "拉取Docker镜像..."
    
    # 确保变量已正确初始化
    if [[ -z "$DOCKER_HUB_IMAGE" ]]; then
        DOCKER_HUB_IMAGE="xbxtempleton/qronos-trading-framework"
        log_info "使用默认镜像名: $DOCKER_HUB_IMAGE"
    fi
    
    if [[ -z "$VERSION" ]]; then
        VERSION="latest"
        log_info "使用默认版本: $VERSION"
    fi
    
    # 显示即将拉取的镜像信息
    log_info "准备拉取镜像: ${DOCKER_HUB_IMAGE}:${VERSION}"
    
    # 拉取最新镜像
    log_info "从Docker Hub拉取镜像..."
    if ! docker pull "${DOCKER_HUB_IMAGE}:${VERSION}"; then
        log_error "镜像拉取失败，请检查："
        echo "   1. 镜像名称是否正确: ${DOCKER_HUB_IMAGE}"
        echo "   2. 版本标签是否存在: ${VERSION}"
        echo "   3. 网络连接是否正常"
        echo "   4. Docker Hub是否可访问"
        echo ""
        echo "   可以尝试："
        echo "   - 使用官方镜像源：$0 --docker-mirror official"
        echo "   - 检查网络连接：ping docker.io"
        echo "   - 手动拉取测试：docker pull hello-world"
        exit 1
    fi
    
    log_success "镜像拉取成功: ${DOCKER_HUB_IMAGE}:${VERSION}"
}

# 生成配置文件
generate_configurations() {
    log_step "生成/检查配置文件..."
    
    # 预生成随机配置（如果不存在）
    if [[ ! -f ./data/qronos/data/port.txt ]]; then
        # 生成随机端口 (8000-30000)
        if command -v jot >/dev/null 2>&1; then
            # macOS
            RANDOM_PORT=$(jot -r 1 8000 30000)
        elif command -v shuf >/dev/null 2>&1; then
            # Linux
            RANDOM_PORT=$(shuf -i 8000-30000 -n 1)
        else
            # 备用方案
            RANDOM_PORT=$((8000 + RANDOM % 22000))
        fi
        echo "${RANDOM_PORT}" > ./data/qronos/data/port.txt
        echo "生成随机端口配置: ${RANDOM_PORT}"
    else
        RANDOM_PORT=$(cat ./data/qronos/data/port.txt)
        echo "使用现有端口配置: ${RANDOM_PORT}"
    fi
    
    if [[ ! -f ./data/qronos/data/prefix.txt ]]; then
        RANDOM_PREFIX=$(openssl rand -base64 24 | tr '+/' '-_' | cut -c1-32)
        echo "${RANDOM_PREFIX}" > ./data/qronos/data/prefix.txt
        echo "生成随机API前缀配置: ${RANDOM_PREFIX}"
    else
        RANDOM_PREFIX=$(cat ./data/qronos/data/prefix.txt)
        echo "使用现有API前缀配置: ${RANDOM_PREFIX}"
    fi
    
    # 显示配置信息
    echo ""
    echo "📋 系统配置信息:"
    echo "🔗 API端口: ${RANDOM_PORT}"
    echo "🔗 API前缀: /${RANDOM_PREFIX}"
    echo "🌐 本地访问: http://localhost:${RANDOM_PORT}/${RANDOM_PREFIX}/"
    if [[ -n "$LOCAL_IP" ]] && [[ "$LOCAL_IP" != "localhost" ]]; then
        echo "🏠 局域网访问: http://${LOCAL_IP}:${RANDOM_PORT}/${RANDOM_PREFIX}/"
    fi
    if [[ -n "$PUBLIC_IP" ]]; then
        echo "🌍 公网访问: http://${PUBLIC_IP}:${RANDOM_PORT}/${RANDOM_PREFIX}/"
    fi
    echo "📁 数据目录: $(pwd)/data"
    echo ""
}

# 部署容器
deploy_container() {
    log_step "部署容器..."
    
    # 停止并删除现有容器
    log_info "清理现有容器..."
    docker stop ${CONTAINER_NAME} 2>/dev/null || true
    docker rm ${CONTAINER_NAME} 2>/dev/null || true
    
    # 启动容器
    log_info "启动容器..."
    
    # 构建Docker运行命令
    DOCKER_RUN_CMD="docker run -d \
        --name ${CONTAINER_NAME} \
        -p ${RANDOM_PORT}:80 \
        -v $(pwd)/data/qronos/data:/app/qronos/data \
        -v $(pwd)/data/qronos/logs:/app/qronos/logs \
        -v $(pwd)/data/firm:/app/firm \
        -v $(pwd)/data/.pm2:/app/.pm2"
    
    # 在Linux系统上添加用户权限配置
    if [[ "$(uname)" == "Linux" ]] && [[ -n "$CURRENT_UID" ]]; then
        # 方案1: 使用 --user 参数（如果容器支持非root用户）
        # DOCKER_RUN_CMD="${DOCKER_RUN_CMD} --user ${CURRENT_UID}:${CURRENT_GID}"
        
        # 方案2: 使用环境变量传递用户信息给容器
        DOCKER_RUN_CMD="${DOCKER_RUN_CMD} -e HOST_UID=${CURRENT_UID} -e HOST_GID=${CURRENT_GID}"
        log_info "Linux系统：已配置用户权限映射 (UID: ${CURRENT_UID}, GID: ${CURRENT_GID})"
    fi
    
    # 添加其他参数并执行
    DOCKER_RUN_CMD="${DOCKER_RUN_CMD} \
        --restart=unless-stopped \
        \"${DOCKER_HUB_IMAGE}:${VERSION}\""
    
    log_info "执行容器启动命令..."
    eval $DOCKER_RUN_CMD
    
    if [[ $? -ne 0 ]]; then
        log_error "容器启动失败"
        exit 1
    fi
    
    # 等待容器启动
    log_info "等待容器启动完成..."
    sleep 10
    
    # 检查并修复权限问题（仅在Linux上）
    if [[ "$(uname)" == "Linux" ]]; then
        log_info "检查和修复文件权限..."
        
        # 等待容器完全启动并可能创建文件
        sleep 5
        
        # 获取真实用户信息
        if [[ -n "$SUDO_UID" ]] && [[ -n "$SUDO_GID" ]]; then
            REAL_UID="$SUDO_UID"
            REAL_GID="$SUDO_GID"
            REAL_USER="$SUDO_USER"
        else
            REAL_UID=$(id -u)
            REAL_GID=$(id -g)
            REAL_USER=$(whoami)
        fi
        
        # 修复可能由容器创建的文件权限
        log_info "修复容器创建文件的权限..."
        chown -R ${REAL_UID}:${REAL_GID} ./data/ 2>/dev/null || {
            log_warning "无法修复权限，请确保有足够的权限"
        }
        
        # 确保目录权限正确
        chmod -R 775 ./data/ 2>/dev/null || {
            log_warning "无法设置目录权限"
        }
        
        # 特别检查关键目录的权限
        for dir in "./data/qronos/data" "./data/qronos/logs" "./data/firm" "./data/.pm2"; do
            if [[ -d "$dir" ]]; then
                if [[ ! -w "$dir" ]]; then
                    log_warning "目录 $dir 权限不足，尝试修复..."
                    chown -R ${REAL_UID}:${REAL_GID} "$dir" 2>/dev/null
                    chmod -R 775 "$dir" 2>/dev/null
                fi
            fi
        done
        
        # 显示权限信息
        log_info "当前权限状态:"
        ls -la ./data/ | head -5
        echo ""
        log_info "关键目录详细权限:"
        for dir in "./data/qronos/data" "./data/qronos/logs" "./data/firm" "./data/.pm2"; do
            if [[ -d "$dir" ]]; then
                ls -ld "$dir"
            fi
        done
    fi
}

# 验证部署
verify_deployment() {
    log_step "验证部署状态..."
    
    # 检查容器状态
    log_info "检查容器状态..."
    docker ps --filter "name=${CONTAINER_NAME}" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}\t{{.Image}}"
    
    # 检查容器健康状态
    echo ""
    log_info "检查服务健康状态..."
    sleep 5
    
    # 尝试健康检查
    if command -v curl >/dev/null 2>&1; then
        # 优先本地检查
        HEALTH_CHECK_LOCAL="http://localhost:${RANDOM_PORT}/health"
        if curl -f -s "${HEALTH_CHECK_LOCAL}" >/dev/null; then
            log_success "本地健康检查通过"
        else
            log_warning "本地健康检查失败"
        fi
        
        # 检查局域网IP
        if [[ -n "$LOCAL_IP" ]] && [[ "$LOCAL_IP" != "localhost" ]]; then
            HEALTH_CHECK_LAN="http://${LOCAL_IP}:${RANDOM_PORT}/health"
            if curl -f -s "${HEALTH_CHECK_LAN}" >/dev/null; then
                log_success "局域网健康检查通过"
            else
                log_warning "局域网健康检查失败"
            fi
        fi
        
        # 检查公网IP（可选，因为可能被防火墙阻止）
        if [[ -n "$PUBLIC_IP" ]]; then
            log_info "公网IP健康检查需要确保防火墙开放端口 ${RANDOM_PORT}"
        fi
    else
        log_warning "curl未安装，无法进行健康检查"
    fi
}

# 显示部署结果
show_deployment_result() {
    # 显示访问信息
    echo ""
    echo "🎉 容器启动完成!"
    echo ""
    echo "📋 访问信息:"
    echo "🏠 本地访问: http://localhost:${RANDOM_PORT}/${RANDOM_PREFIX}/"
    if [[ -n "$LOCAL_IP" ]] && [[ "$LOCAL_IP" != "localhost" ]]; then
        echo "🏠 局域网访问: http://${LOCAL_IP}:${RANDOM_PORT}/${RANDOM_PREFIX}/"
    fi
    if [[ -n "$PUBLIC_IP" ]]; then
        echo "🌍 公网访问: http://${PUBLIC_IP}:${RANDOM_PORT}/${RANDOM_PREFIX}/"
    fi
    echo ""
    echo "🔍 健康检查地址:"
    echo "❤️  本地: http://localhost:${RANDOM_PORT}/health"
    if [[ -n "$LOCAL_IP" ]] && [[ "$LOCAL_IP" != "localhost" ]]; then
        echo "❤️  局域网: http://${LOCAL_IP}:${RANDOM_PORT}/health"
    fi
    if [[ -n "$PUBLIC_IP" ]]; then
        echo "❤️  公网: http://${PUBLIC_IP}:${RANDOM_PORT}/health"
    fi
    echo ""
    echo "🔗 配置信息:"
    echo "• 外部端口: ${RANDOM_PORT}"
    echo "• API前缀: /${RANDOM_PREFIX}"
    echo ""
    
    # 显示管理命令
    echo "📝 管理命令:"
    echo "查看日志: docker logs -f ${CONTAINER_NAME}"
    echo "查看实时日志: docker logs -f --tail 100 ${CONTAINER_NAME}"
    echo "进入容器: docker exec -it ${CONTAINER_NAME} bash"
    echo "查看PM2状态: docker exec -it ${CONTAINER_NAME} pm2 list"
    echo "查看PM2日志: docker exec -it ${CONTAINER_NAME} pm2 logs"
    echo "重启容器: docker restart ${CONTAINER_NAME}"
    echo "停止容器: docker stop ${CONTAINER_NAME}"
    echo "删除容器: docker stop ${CONTAINER_NAME} && docker rm ${CONTAINER_NAME}"
    echo ""
    
    # 显示数据目录信息
    echo "📁 数据目录说明:"
    echo "配置文件: $(pwd)/data/qronos/data/"
    echo "日志文件: $(pwd)/data/qronos/logs/"
    echo "量化框架: $(pwd)/data/firm/"
    echo "PM2配置: $(pwd)/data/.pm2/"
    echo ""
    
    # 显示网络访问提示
    echo "🌐 网络访问提示:"
    if [[ -n "$LOCAL_IP" ]] && [[ "$LOCAL_IP" != "localhost" ]]; then
        echo "• 局域网用户可通过以下地址访问:"
        echo "  http://${LOCAL_IP}:${RANDOM_PORT}/${RANDOM_PREFIX}/"
    fi
    
    if [[ -n "$PUBLIC_IP" ]]; then
        echo "• 公网用户可通过以下地址访问:"
        echo "  http://${PUBLIC_IP}:${RANDOM_PORT}/${RANDOM_PREFIX}/"
        echo "• ⚠️  公网访问需要确保："
        echo "  - 服务器防火墙开放端口 ${RANDOM_PORT}"
        echo "  - 云服务器安全组允许入站规则"
        echo "  - 路由器端口转发配置（如果在内网）"
    else
        echo "• 无法获取公网IP，可能原因："
        echo "  - 位于内网环境（需要端口转发）"
        echo "  - 防火墙阻止外部IP查询"
        echo "  - 网络连接问题"
    fi
    
    log_success "部署完成！容器正在后台运行中..."
}

# 验证必需变量
validate_required_variables() {
    log_step "验证配置参数..."
    
    # 检查并修复关键变量
    if [[ -z "$DOCKER_HUB_IMAGE" ]]; then
        DOCKER_HUB_IMAGE="xbxtempleton/qronos-trading-framework"
        log_warning "镜像名称为空，使用默认值: $DOCKER_HUB_IMAGE"
    fi
    
    if [[ -z "$VERSION" ]]; then
        VERSION="latest"
        log_warning "版本标签为空，使用默认值: $VERSION"
    fi
    
    if [[ -z "$CONTAINER_NAME" ]]; then
        CONTAINER_NAME="qronos-app"
        log_warning "容器名称为空，使用默认值: $CONTAINER_NAME"
    fi
    
    # 验证变量格式
    if [[ ! "$DOCKER_HUB_IMAGE" =~ ^[a-zA-Z0-9._/-]+$ ]]; then
        log_error "无效的镜像名称格式: $DOCKER_HUB_IMAGE"
        exit 1
    fi
    
    if [[ ! "$VERSION" =~ ^[a-zA-Z0-9._-]+$ ]]; then
        log_error "无效的版本标签格式: $VERSION"
        exit 1
    fi
    
    if [[ ! "$CONTAINER_NAME" =~ ^[a-zA-Z0-9._-]+$ ]]; then
        log_error "无效的容器名称格式: $CONTAINER_NAME"
        exit 1
    fi
    
    log_success "配置参数验证通过"
    log_info "✓ 镜像: $DOCKER_HUB_IMAGE:$VERSION"
    log_info "✓ 容器: $CONTAINER_NAME"
}

# 显示内存监控信息
show_memory_status() {
    if [[ "$(uname)" != "Linux" ]]; then
        return 0
    fi
    
    log_step "系统内存状态监控..."
    
    # 获取详细内存信息
    local total_mem_mb=$(free -m | awk '/^Mem:/ {print $2}')
    local used_mem_mb=$(free -m | awk '/^Mem:/ {print $3}')
    local available_mem_mb=$(free -m | awk '/^Mem:/ {print $7}')
    local total_swap_mb=$(free -m | awk '/^Swap:/ {print $2}')
    local used_swap_mb=$(free -m | awk '/^Swap:/ {print $3}')
    
    # 计算使用百分比
    local mem_usage_percent=$((used_mem_mb * 100 / total_mem_mb))
    local swap_usage_percent=0
    if [[ $total_swap_mb -gt 0 ]]; then
        swap_usage_percent=$((used_swap_mb * 100 / total_swap_mb))
    fi
    
    echo ""
    echo "🖥️  当前内存状态:"
    echo "   物理内存: ${used_mem_mb}MB / ${total_mem_mb}MB (${mem_usage_percent}%)"
    echo "   可用内存: ${available_mem_mb}MB"
    if [[ $total_swap_mb -gt 0 ]]; then
        echo "   虚拟内存: ${used_swap_mb}MB / ${total_swap_mb}MB (${swap_usage_percent}%)"
        echo "   总可用内存: $((total_mem_mb + total_swap_mb - used_mem_mb - used_swap_mb))MB"
    else
        echo "   虚拟内存: 未配置"
    fi
    
    # 内存使用警告
    if [[ $mem_usage_percent -gt 85 ]]; then
        log_warning "物理内存使用率较高 (${mem_usage_percent}%)，建议监控容器内存使用"
    elif [[ $mem_usage_percent -gt 70 ]]; then
        log_info "物理内存使用率: ${mem_usage_percent}% (正常范围)"
    else
        log_success "物理内存使用率: ${mem_usage_percent}% (良好)"
    fi
    
    if [[ $total_swap_mb -gt 0 ]] && [[ $swap_usage_percent -gt 50 ]]; then
        log_warning "虚拟内存使用率较高 (${swap_usage_percent}%)，可能影响性能"
    fi
}

# ============================================================================
# 主函数
# ============================================================================

main() {
    # 解析命令行参数
    parse_arguments "$@"
    
    # 最终验证关键变量
    validate_required_variables
    
    # 检查Docker是否已安装
    if ! check_docker_installation; then
        log_warning "Docker未安装或未运行，开始安装..."
        install_docker
        
        # Docker安装后重新验证关键变量（防止安装过程中变量被覆盖）
        validate_required_variables
    else
        log_success "Docker已可用，跳过安装步骤"
    fi
    
    # 检查Docker是否可用
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker 未运行或无法访问"
        log_info "请检查Docker服务状态："
        echo "  sudo systemctl status docker"
        echo "  sudo systemctl start docker"
        exit 1
    fi
    
    # 检查内存配置（仅在Linux系统上）
    if [[ "$(uname)" == "Linux" ]]; then
        check_memory_configuration
    else
        log_info "非Linux系统，跳过内存检查"
    fi
    
    # 环境检查
    check_deployment_environment
    
    # 设置数据目录
    setup_data_directories
    
    # 拉取镜像
    pull_docker_image
    
    # 生成配置
    generate_configurations
    
    # 部署容器
    deploy_container
    
    # 验证部署
    verify_deployment
    
    # 显示结果
    show_deployment_result
    
    # 显示内存监控信息
    show_memory_status
}

# 执行主函数
main "$@"
