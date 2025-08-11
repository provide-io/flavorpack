#!/bin/bash
set -euo pipefail

# PSPF Development Tools Installer
# Installs flavor-dev-tools and related utilities system-wide or locally

VERSION="0.1.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
INSTALL_DIR_GLOBAL="/usr/local/bin"
INSTALL_DIR_LOCAL="$HOME/bin"
CONFIG_DIR="$HOME/.config/flavor"
DEFAULT_INSTALL_TYPE="local"

show_help() {
    cat << 'EOF'
🛠️  PSPF Development Tools Installer
===================================

Install flavor-dev-tools and related development utilities.

USAGE:
    install-dev-tools.sh [OPTIONS]

OPTIONS:
    --global        Install system-wide to /usr/local/bin (requires sudo)
    --local         Install to ~/bin (default)
    --install-dir   Specify custom installation directory
    --config-dir    Specify custom configuration directory (default: ~/.config/flavor)
    --no-config     Skip creating configuration files
    --no-examples   Skip installing example templates
    --force         Force overwrite existing files
    --uninstall     Remove installed files
    --help, -h      Show this help message

EXAMPLES:
    # Install locally (default)
    ./install-dev-tools.sh

    # Install system-wide
    ./install-dev-tools.sh --global

    # Install to custom directory
    ./install-dev-tools.sh --install-dir ~/.local/bin

    # Uninstall
    ./install-dev-tools.sh --uninstall

WHAT GETS INSTALLED:
    - flavor-dev-tools: Main development toolkit
    - Configuration files and templates
    - Shell completions (if supported)
    - Example project templates
    - Documentation links

ENVIRONMENT:
    After installation, add the installation directory to your PATH:
    export PATH="$HOME/bin:$PATH"  # For --local
    export PATH="/usr/local/bin:$PATH"  # For --global (usually already in PATH)
EOF
}

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}" >&2
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}" >&2
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}" >&2
}

log_error() {
    echo -e "${RED}❌ $1${NC}" >&2
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check bash version
    if [[ ${BASH_VERSION%%.*} -lt 4 ]]; then
        log_error "Bash 4.0+ required (found: $BASH_VERSION)"
        return 1
    fi
    
    # Check basic tools
    local missing_tools=()
    for tool in curl tar mkdir chmod; do
        if ! command -v "$tool" &> /dev/null; then
            missing_tools+=("$tool")
        fi
    done
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        return 1
    fi
    
    log_success "Prerequisites satisfied"
}

install_main_script() {
    local install_dir="$1"
    local force="$2"
    
    log_info "Installing flavor-dev-tools to $install_dir"
    
    # Create install directory if it doesn't exist
    if [[ ! -d "$install_dir" ]]; then
        mkdir -p "$install_dir"
        log_info "Created directory: $install_dir"
    fi
    
    local target="$install_dir/flavor-dev-tools"
    
    # Check if already exists
    if [[ -f "$target" && "$force" != "true" ]]; then
        log_error "flavor-dev-tools already exists at $target"
        log_info "Use --force to overwrite"
        return 1
    fi
    
    # Copy and make executable
    cp "$SCRIPT_DIR/flavor-dev-tools.sh" "$target"
    chmod +x "$target"
    
    log_success "Installed flavor-dev-tools to $target"
}

create_config_files() {
    local config_dir="$1"
    local force="$2"
    
    log_info "Creating configuration files in $config_dir"
    
    mkdir -p "$config_dir"
    
    # Main configuration file
    local config_file="$config_dir/config.yml"
    if [[ ! -f "$config_file" || "$force" == "true" ]]; then
        cat > "$config_file" << EOF
# PSPF Development Tools Configuration
# Generated on $(date)

# Default settings
defaults:
  examples_dir: "$BASE_DIR/docs/examples"
  build_dir: "./build"
  cache_dir: "$HOME/.cache/flavor-dev"
  verbose: false

# Project templates
templates:
  simple:
    description: "Basic PSPF provider template"
    source: "simple-provider"
    
  aws:
    description: "AWS resources provider template"
    source: "aws-resources"
    
  database:
    description: "Database provider template"
    source: "database-provider"

# Build settings
build:
  default_version: "dev"
  sign_packages: true
  verify_packages: true
  
# Test settings
test:
  run_unit_tests: true
  run_integration_tests: true
  run_terraform_tests: true
  
# Performance settings
benchmark:
  warmup_runs: 3
  min_runs: 10
  compare_versions: false
EOF
        log_success "Created configuration: $config_file"
    else
        log_info "Configuration already exists: $config_file"
    fi
    
    # Environment setup script
    local env_file="$config_dir/env.sh"
    if [[ ! -f "$env_file" || "$force" == "true" ]]; then
        cat > "$env_file" << EOF
#!/bin/bash
# PSPF Development Environment Setup
# Source this file to set up your PSPF development environment

# Set PSPF development variables
export FLAVOR_DEV_CONFIG_DIR="$config_dir"
export FLAVOR_DEV_EXAMPLES_DIR="$BASE_DIR/docs/examples"
export FLAVOR_DEV_CACHE_DIR="\$HOME/.cache/flavor-dev"

# Add flavor-dev-tools to PATH if not already present
if [[ ":\$PATH:" != *":$HOME/bin:"* ]]; then
    export PATH="\$HOME/bin:\$PATH"
fi

# Helpful aliases
alias flavor-init='flavor-dev-tools init'
alias flavor-build='flavor-dev-tools build'
alias flavor-test='flavor-dev-tools test'
alias flavor-validate='flavor-dev-tools validate'
alias flavor-examples='flavor-dev-tools examples'
alias flavor-doctor='flavor-dev-tools doctor'
alias flavor-clean='flavor-dev-tools clean'

# Function to quickly create and cd into a new PSPF project
flavor-new() {
    local name="\$1"
    local template="\${2:-simple}"
    
    if [[ -z "\$name" ]]; then
        echo "Usage: flavor-new <PROJECT_NAME> [TEMPLATE]"
        echo "Templates: simple, aws, database"
        return 1
    fi
    
    flavor-dev-tools init "\$name" --template "\$template"
    cd "\$name"
}

echo "🛠️  PSPF development environment loaded"
echo "Use 'flavor-dev-tools --help' to get started"
EOF
        chmod +x "$env_file"
        log_success "Created environment setup: $env_file"
    else
        log_info "Environment setup already exists: $env_file"
    fi
}

install_shell_completions() {
    local install_dir="$1"
    local config_dir="$2"
    
    # Only install if bash-completion is available
    if ! command -v bash &> /dev/null; then
        return 0
    fi
    
    log_info "Installing shell completions..."
    
    # Create bash completion
    local completion_dir="$config_dir/completions"
    mkdir -p "$completion_dir"
    
    cat > "$completion_dir/flavor-dev-tools-completion.bash" << 'EOF'
# Bash completion for flavor-dev-tools

_pspf_dev_tools_completion() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    
    # Main commands
    local commands="init build test benchmark validate examples doctor clean"
    
    # Global options
    local global_opts="--verbose --quiet --help --version"
    
    case "${prev}" in
        flavor-dev-tools)
            COMPREPLY=($(compgen -W "${commands} ${global_opts}" -- ${cur}))
            return 0
            ;;
        init)
            local init_opts="--template --output"
            COMPREPLY=($(compgen -W "${init_opts}" -- ${cur}))
            return 0
            ;;
        --template)
            COMPREPLY=($(compgen -W "simple aws database" -- ${cur}))
            return 0
            ;;
        build)
            local build_opts="--project-dir --output --version"
            COMPREPLY=($(compgen -W "${build_opts}" -- ${cur}))
            return 0
            ;;
        test)
            local test_opts="--project-dir --type"
            COMPREPLY=($(compgen -W "${test_opts}" -- ${cur}))
            return 0
            ;;
        --type)
            COMPREPLY=($(compgen -W "unit integration terraform all" -- ${cur}))
            return 0
            ;;
        examples)
            COMPREPLY=($(compgen -W "list build test" -- ${cur}))
            return 0
            ;;
        clean)
            local clean_opts="--type --project-dir --all"
            COMPREPLY=($(compgen -W "${clean_opts}" -- ${cur}))
            return 0
            ;;
        --project-dir|--output)
            COMPREPLY=($(compgen -d -- ${cur}))
            return 0
            ;;
    esac
    
    COMPREPLY=($(compgen -W "${global_opts}" -- ${cur}))
}

complete -F _pspf_dev_tools_completion flavor-dev-tools
EOF
    
    log_success "Created bash completion: $completion_dir/flavor-dev-tools-completion.bash"
    
    # Add to bashrc if possible
    local bashrc_file="$HOME/.bashrc"
    local bash_profile_file="$HOME/.bash_profile"
    
    local completion_source="source \"$completion_dir/flavor-dev-tools-completion.bash\""
    
    for rc_file in "$bashrc_file" "$bash_profile_file"; do
        if [[ -f "$rc_file" ]]; then
            if ! grep -q "flavor-dev-tools-completion.bash" "$rc_file"; then
                echo "" >> "$rc_file"
                echo "# PSPF development tools completion" >> "$rc_file"
                echo "$completion_source" >> "$rc_file"
                log_info "Added completion to $rc_file"
                break
            fi
        fi
    done
}

install_examples() {
    local config_dir="$1"
    local force="$2"
    
    # Skip if examples don't exist
    if [[ ! -d "$BASE_DIR/docs/examples" ]]; then
        log_warning "Examples directory not found, skipping..."
        return 0
    fi
    
    log_info "Installing example templates..."
    
    local templates_dir="$config_dir/templates"
    mkdir -p "$templates_dir"
    
    # Copy example templates
    for example in "$BASE_DIR/docs/examples"/*; do
        if [[ -d "$example" ]]; then
            local example_name=$(basename "$example")
            local target_dir="$templates_dir/$example_name"
            
            if [[ ! -d "$target_dir" || "$force" == "true" ]]; then
                cp -r "$example" "$target_dir"
                log_success "Installed template: $example_name"
            else
                log_info "Template already exists: $example_name"
            fi
        fi
    done
}

uninstall_tools() {
    local install_dir="$1"
    local config_dir="$2"
    
    log_info "Uninstalling PSPF development tools..."
    
    # Remove main script
    local main_script="$install_dir/flavor-dev-tools"
    if [[ -f "$main_script" ]]; then
        rm "$main_script"
        log_success "Removed: $main_script"
    fi
    
    # Optionally remove config directory
    if [[ -d "$config_dir" ]]; then
        echo ""
        read -p "Remove configuration directory $config_dir? [y/N]: " -r
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$config_dir"
            log_success "Removed: $config_dir"
        else
            log_info "Kept configuration directory"
        fi
    fi
    
    # Remove from shell RC files
    for rc_file in "$HOME/.bashrc" "$HOME/.bash_profile" "$HOME/.zshrc"; do
        if [[ -f "$rc_file" ]] && grep -q "flavor-dev-tools" "$rc_file"; then
            # Create backup
            cp "$rc_file" "${rc_file}.backup-$(date +%s)"
            
            # Remove PSPF lines
            sed -i.tmp '/# PSPF development tools/,+1d' "$rc_file"
            sed -i.tmp '/flavor-dev-tools-completion/d' "$rc_file"
            rm "${rc_file}.tmp"
            
            log_success "Cleaned up $rc_file (backup created)"
        fi
    done
    
    log_success "Uninstallation completed"
}

add_to_shell_rc() {
    local config_dir="$1"
    local install_dir="$2"
    
    log_info "Adding PSPF environment to shell configuration..."
    
    local env_source="source \"$config_dir/env.sh\""
    local path_export="export PATH=\"$install_dir:\$PATH\""
    
    # Determine which RC file to use
    local rc_files=("$HOME/.bashrc" "$HOME/.bash_profile" "$HOME/.zshrc")
    local target_rc=""
    
    for rc_file in "${rc_files[@]}"; do
        if [[ -f "$rc_file" ]]; then
            target_rc="$rc_file"
            break
        fi
    done
    
    # Create .bashrc if no RC file exists
    if [[ -z "$target_rc" ]]; then
        target_rc="$HOME/.bashrc"
        touch "$target_rc"
    fi
    
    # Add environment setup if not already present
    if ! grep -q "flavor.*env.sh" "$target_rc"; then
        echo "" >> "$target_rc"
        echo "# PSPF Development Environment" >> "$target_rc"
        echo "$env_source" >> "$target_rc"
        log_success "Added environment setup to $target_rc"
    fi
    
    # Add to PATH if install_dir is not standard
    if [[ "$install_dir" != "/usr/local/bin" && "$install_dir" != "/usr/bin" ]]; then
        if ! grep -q "$install_dir" "$target_rc"; then
            echo "$path_export" >> "$target_rc"
            log_success "Added $install_dir to PATH in $target_rc"
        fi
    fi
}

show_installation_summary() {
    local install_dir="$1"
    local config_dir="$2"
    
    echo ""
    log_success "🎉 PSPF Development Tools installation completed!"
    echo ""
    echo "📍 Installation Summary:"
    echo "  Main tool: $install_dir/flavor-dev-tools"
    echo "  Configuration: $config_dir/"
    echo "  Templates: $config_dir/templates/"
    echo ""
    echo "🚀 Quick Start:"
    echo "  # Reload your shell or run:"
    echo "  source $config_dir/env.sh"
    echo ""
    echo "  # Check installation:"
    echo "  flavor-dev-tools doctor"
    echo ""
    echo "  # Create your first project:"
    echo "  flavor-dev-tools init my-provider"
    echo ""
    echo "🔧 Available Commands:"
    echo "  flavor-dev-tools --help         # Show all commands"
    echo "  flavor-dev-tools examples list  # List available examples"
    echo "  flavor-dev-tools doctor         # Check environment"
    echo ""
    echo "📚 Documentation:"
    echo "  https://github.com/your-org/flavor/docs"
    echo ""
}

main() {
    local install_type="$DEFAULT_INSTALL_TYPE"
    local install_dir=""
    local config_dir="$CONFIG_DIR"
    local force="false"
    local no_config="false"
    local no_examples="false"
    local uninstall="false"
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --global)
                install_type="global"
                shift
                ;;
            --local)
                install_type="local"
                shift
                ;;
            --install-dir)
                install_dir="$2"
                install_type="custom"
                shift 2
                ;;
            --config-dir)
                config_dir="$2"
                shift 2
                ;;
            --no-config)
                no_config="true"
                shift
                ;;
            --no-examples)
                no_examples="true"
                shift
                ;;
            --force)
                force="true"
                shift
                ;;
            --uninstall)
                uninstall="true"
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Determine install directory
    if [[ -z "$install_dir" ]]; then
        case "$install_type" in
            "global")
                install_dir="$INSTALL_DIR_GLOBAL"
                ;;
            "local")
                install_dir="$INSTALL_DIR_LOCAL"
                ;;
        esac
    fi
    
    # Handle uninstall
    if [[ "$uninstall" == "true" ]]; then
        uninstall_tools "$install_dir" "$config_dir"
        exit 0
    fi
    
    # Check prerequisites
    check_prerequisites
    
    # Check permissions for global install
    if [[ "$install_type" == "global" || "$install_dir" == "/usr/local/bin" ]]; then
        if [[ $EUID -ne 0 && ! -w "$install_dir" ]]; then
            log_error "Global installation requires sudo privileges"
            log_info "Run: sudo $0 --global"
            log_info "Or use: $0 --local"
            exit 1
        fi
    fi
    
    # Install main script
    install_main_script "$install_dir" "$force"
    
    # Create configuration files
    if [[ "$no_config" != "true" ]]; then
        create_config_files "$config_dir" "$force"
        install_shell_completions "$install_dir" "$config_dir"
        add_to_shell_rc "$config_dir" "$install_dir"
    fi
    
    # Install example templates
    if [[ "$no_examples" != "true" ]]; then
        install_examples "$config_dir" "$force"
    fi
    
    # Show summary
    show_installation_summary "$install_dir" "$config_dir"
}

# Run main function
main "$@"


# 📦🍜📄🪄
