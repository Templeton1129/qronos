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
    echo "  --help, -h              显示此帮助信息"
    echo ""
    echo "Docker镜像源说明:"
    echo "  official         Docker官方源"
    echo "  china           中科大镜像源 (推荐)"
    echo "  tencent         腾讯云镜像源"
    echo "  aliyun          阿里云镜像源"
    echo "  ustc            中科大镜像源"
    echo ""
    echo "镜像版本检查说明:"
    echo "  脚本会自动检查远程和本地镜像版本是否一致："
    echo "    - 如果版本一致：直接使用本地镜像启动容器"
    echo "    - 如果版本不一致：删除本地镜像，重新拉取最新版本"
    echo "    - 如果本地镜像不存在：直接拉取最新版本"
    echo "    - 如果网络检查失败：提示用户选择强制更新或使用本地镜像"
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
    echo "  $0 myuser/qronos latest qronos --docker-mirror official    # 完整参数示例"
    echo ""
    echo "注意事项:"
    echo "  - 镜像版本检查需要网络连接到Docker Hub"
    echo "  - 版本检查失败时会提示用户选择处理方式"
    echo "  - 强制更新会删除本地镜像，需要重新下载完整镜像"
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
                ip=$(curl -s --connect-timeout 5 --max-time 10 "https://$service" 2>/dev/null | grep -o '"origin":[[:space:]]*"[^"]*"' | sed 's/.*"origin":[[:space:]]*"\([^"]*\)".*/\1/' | cut -d',' -f1)
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
    mkdir -p ./data/qronos/data ./data/qronos/logs ./data/firm ./data/.pm2-runtime
    
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

# 检查本地镜像是否存在
check_local_image_exists() {
    local image_name="$1"
    docker image inspect "${image_name}" >/dev/null 2>&1
}

# 获取远程镜像ID
get_remote_image_id() {
    local image_name="$1"
    log_info "获取远程镜像信息: ${image_name}" >&2
    
    # 首先尝试使用docker pull --dry-run（如果支持）来获取最新的digest
    # 这是最可靠的方法，因为它会返回实际会被拉取的镜像digest
    local remote_digest=""
    
    # 检查是否支持 --dry-run（较新版本的Docker支持）
    if docker pull --help 2>&1 | grep -q -- --dry-run; then
        log_info "使用 docker pull --dry-run 检查远程镜像..." >&2
        local pull_output=$(docker pull --dry-run "${image_name}" 2>&1)
        if [[ $? -eq 0 ]]; then
            # 从输出中提取digest
            remote_digest=$(echo "$pull_output" | grep -o 'Digest: sha256:[^[:space:]]*' | sed 's/Digest: //' | head -1)
        fi
    fi
    
    # 如果上述方法失败，尝试使用manifest inspect
    if [[ -z "$remote_digest" ]]; then
        log_info "使用docker manifest方式获取远程镜像信息..." >&2
        local manifest_output=$(docker manifest inspect "${image_name}" 2>/dev/null)
        
        if [[ -n "$manifest_output" ]]; then
            # 检查是否是多架构镜像（manifest list）
            if echo "$manifest_output" | grep -q '"mediaType".*manifest.list\|image.index'; then
                # 多架构镜像，需要获取当前架构的digest
                local current_arch=$(uname -m)
                local docker_arch="amd64"  # 默认
                
                if [[ "$current_arch" == "x86_64" ]]; then
                    docker_arch="amd64"
                elif [[ "$current_arch" == "aarch64" ]] || [[ "$current_arch" == "arm64" ]]; then
                    docker_arch="arm64"
                fi
                
                log_info "检测到多架构镜像，获取 $docker_arch 架构的digest..." >&2
                
                # 获取特定架构的镜像digest
                # 注意：我们需要的是镜像层的digest，而不是manifest的digest
                # 但是为了比较，我们使用manifest digest
                remote_digest=$(echo "$manifest_output" | grep -A 5 "\"architecture\":[[:space:]]*\"$docker_arch\"" | grep '"digest"' | grep -o '"sha256:[^"]*"' | tr -d '"' | head -1)
            else
                # 单架构镜像，直接获取digest
                remote_digest=$(echo "$manifest_output" | grep -o '"digest":[[:space:]]*"sha256:[^"]*"' | sed 's/.*"sha256:\([^"]*\)".*/sha256:\1/' | head -1)
            fi
        fi
    fi
    
    # 如果还是失败，尝试使用Docker Hub API
    if [[ -z "$remote_digest" ]] && command -v curl >/dev/null 2>&1; then
        log_info "使用Docker Hub API获取远程镜像信息..." >&2
        local repo_name="${image_name}"
        if [[ "$repo_name" != *"/"* ]]; then
            repo_name="library/${repo_name}"
        fi
        
        # 提取用户名和仓库名
        local user_repo="${repo_name%:*}"
        local tag="${image_name##*:}"
        if [[ "$tag" == "$image_name" ]]; then
            tag="latest"
        fi
        
        # 获取认证token
        local token=$(curl -s "https://auth.docker.io/token?service=registry.docker.io&scope=repository:${user_repo}:pull" 2>/dev/null | grep -o '"token":[[:space:]]*"[^"]*"' | sed 's/.*"token":[[:space:]]*"\([^"]*\)".*/\1/')
        
        if [[ -n "$token" ]]; then
            # 获取manifest
            remote_digest=$(curl -s -H "Authorization: Bearer $token" \
                -H "Accept: application/vnd.docker.distribution.manifest.v2+json" \
                "https://registry-1.docker.io/v2/${user_repo}/manifests/${tag}" 2>/dev/null | \
                grep -o '"digest":[[:space:]]*"sha256:[^"]*"' | sed 's/.*"sha256:\([^"]*\)".*/sha256:\1/' | head -1)
        fi
    fi
    
    echo "$remote_digest"
}

# 获取本地镜像ID
get_local_image_id() {
    local image_name="$1"
    docker image inspect "${image_name}" --format '{{.Id}}' 2>/dev/null | cut -d':' -f2 | head -c12
}

# 获取本地镜像RepoDigests
get_local_image_digest() {
    local image_name="$1"
    # 获取RepoDigests中的digest部分（不包含仓库名）
    docker image inspect "${image_name}" --format '{{range .RepoDigests}}{{.}}{{"\n"}}{{end}}' 2>/dev/null | grep -o '@sha256:[^[:space:]]*' | sed 's/@//' | head -1
}

# 清理无标签镜像
cleanup_dangling_images() {
    log_info "清理无标签镜像（dangling images）..."
    
    # 获取所有无标签镜像
    local dangling_images=$(docker images -f "dangling=true" -q 2>/dev/null)
    
    if [[ -z "$dangling_images" ]]; then
        log_info "没有发现无标签镜像，无需清理"
        return 0
    fi
    
    # 统计数量
    local count=$(echo "$dangling_images" | wc -l)
    log_info "发现 $count 个无标签镜像，开始清理..."
    
    # 显示要删除的镜像信息
    echo ""
    echo "🗑️  准备删除的无标签镜像:"
    docker images -f "dangling=true" --format "table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.CreatedSince}}\t{{.Size}}" 2>/dev/null || {
        docker images -f "dangling=true" 2>/dev/null
    }
    echo ""
    
    # 停止所有使用无标签镜像的容器
    log_info "检查并停止使用无标签镜像的容器..."
    
    # 使用数组避免子shell问题
    local dangling_array=()
    while IFS= read -r image_id; do
        [[ -n "$image_id" ]] && dangling_array+=("$image_id")
    done <<< "$dangling_images"
    
    # 停止使用无标签镜像的容器
    for image_id in "${dangling_array[@]}"; do
        local containers=$(docker ps -a --filter "ancestor=${image_id}" --format "{{.Names}}" 2>/dev/null)
        if [[ -n "$containers" ]]; then
            while IFS= read -r container_name; do
                if [[ -n "$container_name" ]]; then
                    log_info "停止容器: $container_name (使用镜像: $image_id)"
                    docker stop "$container_name" 2>/dev/null || true
                    docker rm "$container_name" 2>/dev/null || true
                fi
            done <<< "$containers"
        fi
    done
    
    # 删除无标签镜像（改进版本）
    local deleted_count=0
    local failed_count=0
    
    # 使用for循环避免子shell问题
    for image_id in "${dangling_array[@]}"; do
        # 首先尝试普通删除
        if docker rmi "$image_id" >/dev/null 2>&1; then
            log_info "✅ 删除成功: $image_id"
            deleted_count=$((deleted_count + 1))
        else
            # 普通删除失败，尝试强制删除
            log_info "尝试强制删除: $image_id"
            if docker rmi -f "$image_id" >/dev/null 2>&1; then
                log_info "✅ 强制删除成功: $image_id"
                deleted_count=$((deleted_count + 1))
            else
                # 获取详细的错误信息
                local error_msg=$(docker rmi "$image_id" 2>&1 || true)
                log_warning "❌ 删除失败: $image_id"
                log_info "错误详情: $error_msg"
                failed_count=$((failed_count + 1))
                
                # 显示哪些容器或镜像可能在使用这个镜像
                local dependent_containers=$(docker ps -a --filter "ancestor=${image_id}" --format "{{.Names}}" 2>/dev/null)
                if [[ -n "$dependent_containers" ]]; then
                    log_info "使用此镜像的容器: $dependent_containers"
                fi
                
                # 检查镜像依赖关系  
                local dependent_images=$(docker images --filter "reference=*:*" --format "{{.Repository}}:{{.Tag}}" | xargs -I {} docker image inspect {} --format "{{.Id}} {{.RepoTags}}" 2>/dev/null | grep "$image_id" | head -3 || true)
                if [[ -n "$dependent_images" ]]; then
                    log_info "可能的依赖镜像: $dependent_images"
                fi
            fi
        fi
    done
    
    # 显示清理进度
    log_info "第一轮清理完成：成功删除 $deleted_count 个，失败 $failed_count 个"
    
    # 使用 docker image prune 作为补充清理
    log_info "执行系统级镜像清理..."
    local prune_result=""
    
    # 先尝试清理悬空镜像
    prune_result=$(docker image prune -f 2>/dev/null || echo "No images to remove")
    if echo "$prune_result" | grep -q "deleted\|reclaimed"; then
        local reclaimed_space=$(echo "$prune_result" | grep "reclaimed" | sed 's/.*reclaimed //' || echo "未知大小")
        log_success "系统清理完成，回收空间: $reclaimed_space"
    else
        log_info "系统清理完成，没有额外空间回收"
    fi
    
    # 再次尝试清理残留的无标签镜像
    local remaining_dangling=$(docker images -f "dangling=true" -q 2>/dev/null || true)
    if [[ -n "$remaining_dangling" ]]; then
        log_info "发现残留无标签镜像，尝试批量清理..."
        
        # 将结果转换为数组进行批量清理
        local remaining_array=()
        while IFS= read -r image_id; do
            [[ -n "$image_id" ]] && remaining_array+=("$image_id")
        done <<< "$remaining_dangling"
        
        # 批量强制删除（如果仍有残留）
        for image_id in "${remaining_array[@]}"; do
            log_info "尝试批量删除: $image_id"
            if docker rmi -f "$image_id" >/dev/null 2>&1; then
                log_info "✅ 批量删除成功: $image_id"
            else
                log_info "⚠️  批量删除失败: $image_id (将尝试系统清理)"
            fi
        done
    fi
    
    # 显示最终清理结果
    local final_dangling_count=$(docker images -f "dangling=true" -q 2>/dev/null | wc -l || echo "0")
    final_dangling_count=${final_dangling_count:-0}
    
    if [[ "$final_dangling_count" -eq 0 ]]; then
        log_success "✅ 无标签镜像清理完成，系统中无残留镜像"
    else
        log_warning "⚠️  仍有 $final_dangling_count 个无标签镜像未能删除"
        echo ""
        echo "📋 残留镜像信息："
        docker images -f "dangling=true" --format "   {{.ID}} ({{.CreatedSince}}, {{.Size}})" 2>/dev/null || {
            docker images -f "dangling=true" 2>/dev/null || echo "   无法获取镜像详情"
        }
        echo ""
        echo "💡 这些镜像可能："
        echo "   - 被其他正在运行的容器使用"
        echo "   - 与正在运行的镜像共享文件系统层"
        echo "   - 被Docker内部进程锁定"
        echo ""
        echo "🛠️  手动清理命令："
        echo "   docker images -f dangling=true  # 查看无标签镜像"
        echo "   docker system prune -a -f       # 强制清理所有未使用资源"
        echo "   docker container prune -f       # 清理停止的容器"
        echo ""
        log_info "残留的无标签镜像不会影响系统正常运行"
    fi
    
    log_info "无标签镜像清理流程已完成，继续后续部署步骤..."
}

# 比较镜像版本
compare_image_versions() {
    local image_name="$1"
    
    log_step "检查镜像版本更新..."
    
    # 检查本地镜像是否存在
    if ! check_local_image_exists "${image_name}"; then
        log_info "本地镜像不存在，需要拉取: ${image_name}"
        return 2  # 需要拉取
    fi
    
    log_info "本地镜像已存在，检查版本差异..."
    
    # 获取本地镜像信息
    local local_image_id=$(get_local_image_id "${image_name}")
    local local_digest=$(get_local_image_digest "${image_name}")
    
    log_info "本地镜像ID: ${local_image_id:-未知}"
    log_info "本地镜像Digest: ${local_digest:-未知}"
    
    # 获取远程镜像信息
    local remote_digest=$(get_remote_image_id "${image_name}")
    
    if [[ -z "$remote_digest" ]]; then
        log_warning "无法获取远程镜像信息，跳过版本检查"
        log_info "可能的原因："
        echo "   - 网络连接问题"
        echo "   - Docker Hub API限制"
        echo "   - 镜像名称不正确"
        echo "   - 镜像仓库访问限制"
        return 3  # 网络检查失败，需要用户选择
    fi
    
    log_info "远程镜像Digest: ${remote_digest}"
    
    # 比较digest
    if [[ -n "$local_digest" ]] && [[ -n "$remote_digest" ]]; then
        if [[ "$local_digest" == "$remote_digest" ]]; then
            log_success "本地镜像版本是最新的，无需更新"
            return 0  # 版本一致
        else
            # 对于多架构镜像，digest可能不匹配是正常的
            # 我们可以尝试通过 docker pull 来让Docker自己判断
            log_info "检测到digest不一致，尝试让Docker判断是否需要更新..."
            
            # 使用docker pull检查（不实际拉取）
            local pull_check=$(docker pull "${image_name}" 2>&1)
            if echo "$pull_check" | grep -q "Status: Image is up to date\|already exists"; then
                log_success "Docker确认本地镜像已是最新版本"
                return 0  # 版本一致
            else
                log_warning "检测到镜像版本不一致，需要更新"
                echo ""
                echo "📊 版本对比:"
                echo "   本地版本: ${local_digest:-未知}"
                echo "   远程版本: ${remote_digest:-未知}"
                echo "   本地镜像ID: ${local_image_id:-未知}"
                return 1  # 版本不一致，需要更新
            fi
        fi
    elif [[ -z "$remote_digest" ]]; then
        # 无法获取远程digest，但这对于多架构镜像是常见的
        log_info "无法精确比较版本（多架构镜像），将使用Docker的判断"
        return 3  # 需要用户选择
    else
        log_warning "检测到镜像版本信息不完整"
        echo ""
        echo "📊 版本信息:"
        echo "   本地版本: ${local_digest:-未知}"
        echo "   远程版本: ${remote_digest:-未知}"
        echo "   本地镜像ID: ${local_image_id:-未知}"
        return 1  # 假设需要更新
    fi
}

# 删除本地镜像
remove_local_image() {
    local image_name="$1"
    
    log_info "删除本地镜像: ${image_name}"
    
    # 获取镜像ID，用于后续验证
    local image_id=$(get_local_image_id "${image_name}")
    log_info "目标删除镜像ID: ${image_id}"
    
    # 检查是否有容器使用该镜像
    local containers_using_image=$(docker ps -a --filter "ancestor=${image_name}" --format "{{.Names}}" 2>/dev/null)
    
    if [[ -n "$containers_using_image" ]]; then
        log_info "发现使用该镜像的容器，先停止并删除..."
        echo "$containers_using_image" | while read -r container_name; do
            if [[ -n "$container_name" ]]; then
                log_info "停止容器: $container_name"
                docker stop "$container_name" 2>/dev/null || true
                log_info "删除容器: $container_name"
                docker rm "$container_name" 2>/dev/null || true
            fi
        done
    fi
    
    # 删除镜像标签
    if docker rmi "${image_name}" 2>/dev/null; then
        log_success "镜像标签删除成功: ${image_name}"
    else
        log_warning "删除镜像标签失败，尝试强制删除..."
        # 尝试强制删除
        if docker rmi -f "${image_name}" 2>/dev/null; then
            log_success "强制删除镜像标签成功: ${image_name}"
        else
            log_error "无法删除镜像标签，请手动处理"
            return 1
        fi
    fi
    
    # 验证镜像是否还存在（可能变成无标签镜像）
    if [[ -n "$image_id" ]]; then
        if docker image inspect "$image_id" >/dev/null 2>&1; then
            log_info "检测到镜像 $image_id 仍然存在（可能为无标签镜像），尝试删除..."
            if docker rmi "$image_id" 2>/dev/null; then
                log_success "成功删除镜像: $image_id"
            else
                log_warning "无法删除镜像 $image_id，可能被其他镜像层共享"
            fi
        else
            log_success "镜像已完全删除: $image_id"
        fi
    fi
}

# 拉取或更新镜像
pull_or_update_docker_image() {
    log_step "检查和更新Docker镜像..."
    
    # 确保变量已正确初始化
    if [[ -z "$DOCKER_HUB_IMAGE" ]]; then
        DOCKER_HUB_IMAGE="xbxtempleton/qronos-trading-framework"
        log_info "使用默认镜像名: $DOCKER_HUB_IMAGE"
    fi
    
    if [[ -z "$VERSION" ]]; then
        VERSION="latest"
        log_info "使用默认版本: $VERSION"
    fi
    
    local full_image_name="${DOCKER_HUB_IMAGE}:${VERSION}"
    log_info "目标镜像: ${full_image_name}"
    
    # 检查镜像版本
    # 比较镜像版本
    # 暂时关闭 set -e 以处理返回值
    set +e
    compare_image_versions "${full_image_name}"
    local version_check_result=$?
    set -e
    
    case $version_check_result in
        0)
            # 版本一致，无需更新
            log_success "使用现有本地镜像: ${full_image_name}"
            return 0
            ;;
        1)
            # 版本不一致，需要更新
            log_step "更新镜像到最新版本..."
            
            # 删除本地镜像
            if ! remove_local_image "${full_image_name}"; then
                log_error "删除本地镜像失败"
                return 1
            fi
            
            # 拉取新镜像
            log_info "拉取最新镜像: ${full_image_name}"
            ;;
        2)
            # 本地镜像不存在，需要拉取
            log_info "拉取镜像: ${full_image_name}"
            ;;
        3)
            # 网络检查失败，需要用户选择
            log_step "网络检查失败，无法验证镜像版本..."
            echo ""
            echo "🤔 镜像版本检查失败，您希望如何处理？"
            echo ""
            echo "📋 可选操作："
            echo "   1. 强制更新镜像 - 删除本地镜像并重新拉取最新版本"
            echo "   2. 使用本地镜像 - 直接使用现有本地镜像启动容器"
            echo ""
            log_warning "注意：强制更新会删除本地镜像，重新下载可能需要几分钟"
            echo ""
            
            # 检查是否在自动化模式下
            if [[ -n "${CI:-}" ]] || [[ -n "${AUTOMATED:-}" ]]; then
                log_info "检测到自动化模式，默认使用本地镜像..."
                log_success "使用现有本地镜像: ${full_image_name}"
                return 0
            fi
            
            # 交互式选择
            while true; do
                read -p "请选择操作 [1-强制更新/2-使用本地]: " -r choice
                case $choice in
                    1|y|Y|yes|YES)
                        log_step "用户选择：强制更新镜像"
                        log_info "开始删除本地镜像并重新拉取..."
                        
                        # 删除本地镜像
                        if ! remove_local_image "${full_image_name}"; then
                            log_error "删除本地镜像失败"
                            return 1
                        fi
                        
                        log_info "强制拉取最新镜像: ${full_image_name}"
                        break
                        ;;
                    2|n|N|no|NO|"")
                        log_step "用户选择：使用本地镜像"
                        log_success "使用现有本地镜像: ${full_image_name}"
                        return 0
                        ;;
                    *)
                        echo "无效选择，请输入 1（强制更新）或 2（使用本地）"
                        ;;
                esac
            done
            ;;
        *)
            log_error "镜像版本检查异常"
            return 1
            ;;
    esac
    
    # 执行镜像拉取
    log_info "从Docker Hub拉取镜像: ${full_image_name}"
    log_info "注意：镜像拉取可能需要几分钟时间，请耐心等待..."
    
    # 添加超时和详细错误处理
    if command -v timeout >/dev/null 2>&1; then
        # 使用30分钟超时
        log_info "设置30分钟拉取超时..."
        if timeout 1800 docker pull "${full_image_name}"; then
            log_success "镜像拉取成功"
        else
            local exit_code=$?
            if [[ $exit_code -eq 124 ]]; then
                log_error "镜像拉取超时（30分钟），可能网络连接较慢"
            else
                log_error "镜像拉取失败，退出码: $exit_code"
            fi
            
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
            return 1
        fi
    else
        # 没有timeout命令，直接拉取
        log_warning "系统没有timeout命令，无法设置拉取超时"
        if ! docker pull "${full_image_name}"; then
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
            return 1
        fi
    fi
    
    # 验证拉取结果
    if check_local_image_exists "${full_image_name}"; then
        local new_image_id=$(get_local_image_id "${full_image_name}")
        local new_digest=$(get_local_image_digest "${full_image_name}")
        
        log_success "镜像拉取成功: ${full_image_name}"
        echo "📊 新镜像信息:"
        echo "   镜像ID: ${new_image_id:-未知}"
        echo "   Digest: ${new_digest:-未知}"
        
        # 显示镜像大小信息
        local image_size=$(docker image inspect "${full_image_name}" --format '{{.Size}}' 2>/dev/null)
        if [[ -n "$image_size" ]]; then
            local size_mb=$((image_size / 1024 / 1024))
            echo "   大小: ${size_mb}MB"
        fi
        
        # 清理无标签的镜像（防止镜像积累）
        cleanup_dangling_images
    else
        log_error "镜像拉取验证失败"
        return 1
    fi
}

# 保持向后兼容的拉取镜像函数
pull_docker_image() {
    pull_or_update_docker_image
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
        -v $(pwd)/data/.pm2-runtime:/app/.pm2-runtime"
    
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
    echo "🧹 系统清理命令:"
    echo "查看所有镜像: docker images"
    echo "清理无标签镜像: docker image prune -f"
    echo "清理所有未使用镜像: docker image prune -a -f"
    echo "清理所有未使用资源: docker system prune -f"
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
    # 错误处理函数
    handle_deployment_error() {
        local exit_code=$?
        local line_number=$1
        log_error "部署过程在第 $line_number 行出现错误，退出码: $exit_code"
        log_error "最后执行的命令: $BASH_COMMAND"
        echo ""
        echo "🔍 调试信息："
        echo "   - 当前目录: $(pwd)"
        echo "   - 用户: $(whoami)"
        echo "   - Docker状态: $(docker info > /dev/null 2>&1 && echo "正常" || echo "异常")"
        echo "   - 网络连接: $(ping -c 1 8.8.8.8 > /dev/null 2>&1 && echo "正常" || echo "异常")"
        echo ""
        echo "💡 快速解决方案："
        echo "   1. 重新运行: sudo $0 $@"
        echo "   2. 检查Docker状态: docker info"
        echo "   3. 检查网络连接: ping docker.io"
        exit $exit_code
    }
    
    # 设置错误处理（仅在不是已有trap的情况下）
    if ! trap -p ERR | grep -q handle_deployment_error; then
        trap 'handle_deployment_error $LINENO' ERR
    fi
    
    log_step "开始部署流程..."
    
    # 解析命令行参数
    log_info "解析命令行参数..."
    parse_arguments "$@"
    
    # 最终验证关键变量
    log_info "验证配置参数..."
    validate_required_variables
    
    # 检查Docker是否已安装
    log_info "检查Docker安装状态..."
    if ! check_docker_installation; then
        log_warning "Docker未安装或未运行，开始安装..."
        install_docker
        
        # Docker安装后重新验证关键变量（防止安装过程中变量被覆盖）
        validate_required_variables
    else
        log_success "Docker已可用，跳过安装步骤"
    fi
    
    # 检查Docker是否可用
    log_info "验证Docker服务状态..."
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
    
    # 拉取或更新镜像
    log_info "准备拉取/更新Docker镜像..."
    pull_or_update_docker_image
    
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
 