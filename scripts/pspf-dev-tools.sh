#!/bin/bash
set -euo pipefail

# PSPF Developer Tools Collection
# A comprehensive toolkit for PSPF development workflows

VERSION="0.1.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
DEFAULT_EXAMPLES_DIR="$BASE_DIR/docs/examples"
DEFAULT_BUILD_DIR="$BASE_DIR/build"
DEFAULT_CACHE_DIR="$HOME/.cache/flavor-dev"

show_help() {
    cat << 'EOF'
🛠️  PSPF Developer Tools v0.1.0
==================================

A comprehensive toolkit for PSPF development workflows.

USAGE:
    flavor-dev-tools <COMMAND> [OPTIONS]

COMMANDS:
    init            Initialize new PSPF provider project
    build           Build PSPF packages with smart defaults
    test            Run comprehensive test suites
    benchmark       Performance benchmarking and profiling
    validate        Validate packages and configurations
    release         Release management and automation
    examples        Manage and run example projects
    doctor          Diagnose development environment issues
    clean           Clean build artifacts and caches

GLOBAL OPTIONS:
    --verbose, -v   Enable verbose output
    --quiet, -q     Suppress non-error output
    --help, -h      Show help information
    --version       Show version information

EXAMPLES:
    # Initialize a new provider
    flavor-dev-tools init my-provider --template aws

    # Build all examples
    flavor-dev-tools examples build

    # Run performance benchmarks
    flavor-dev-tools benchmark --compare-versions

    # Validate a package
    flavor-dev-tools validate ./dist/my-provider

    # Clean everything
    flavor-dev-tools clean --all

ENVIRONMENT VARIABLES:
    FLAVOR_DEV_EXAMPLES_DIR    Directory containing examples (default: docs/examples)
    FLAVOR_DEV_BUILD_DIR       Build output directory (default: build)
    FLAVOR_DEV_CACHE_DIR       Cache directory (default: ~/.cache/flavor-dev)
    FLAVOR_DEV_VERBOSE         Enable verbose output (1 or true)

For detailed help on a specific command:
    flavor-dev-tools <COMMAND> --help

GitHub: https://github.com/your-org/flavor
Documentation: https://github.com/your-org/flavor/docs
EOF
}

log_info() {
    if [[ "${QUIET:-}" != "true" ]]; then
        echo -e "${BLUE}ℹ️  $1${NC}" >&2
    fi
}

log_success() {
    if [[ "${QUIET:-}" != "true" ]]; then
        echo -e "${GREEN}✅ $1${NC}" >&2
    fi
}

log_warning() {
    if [[ "${QUIET:-}" != "true" ]]; then
        echo -e "${YELLOW}⚠️  $1${NC}" >&2
    fi
}

log_error() {
    echo -e "${RED}❌ $1${NC}" >&2
}

log_verbose() {
    if [[ "${VERBOSE:-}" == "true" ]]; then
        echo -e "${PURPLE}🔍 $1${NC}" >&2
    fi
}

check_dependencies() {
    log_verbose "Checking dependencies..."
    
    local missing_deps=()
    
    # Check required tools
    if ! command -v flavor-packager &> /dev/null; then
        missing_deps+=("flavor-packager")
    fi
    
    if ! command -v flavor-launcher &> /dev/null; then
        missing_deps+=("flavor-launcher")
    fi
    
    if ! command -v python3 &> /dev/null; then
        missing_deps+=("python3")
    fi
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_error "Missing required dependencies: ${missing_deps[*]}"
        log_info "Please install PSPF tools and Python 3.8+"
        log_info "See: https://github.com/your-org/flavor/docs/installation.md"
        return 1
    fi
    
    log_verbose "All dependencies satisfied"
    return 0
}

init_project() {
    local project_name="$1"
    local template="${2:-simple}"
    local output_dir="${3:-$project_name}"
    
    log_info "Initializing PSPF provider project: $project_name"
    log_verbose "Template: $template, Output: $output_dir"
    
    # Create project structure
    mkdir -p "$output_dir"/{src,tests/{unit,integration},terraform-examples,keys,dist}
    
    # Copy template files based on template type
    case "$template" in
        "simple")
            log_info "Creating simple provider template..."
            cp -r "$DEFAULT_EXAMPLES_DIR/simple-provider/src/"* "$output_dir/src/"
            cp -r "$DEFAULT_EXAMPLES_DIR/simple-provider/terraform-test" "$output_dir/terraform-examples/basic"
            ;;
        "aws")
            log_info "Creating AWS provider template..."
            if [[ -d "$DEFAULT_EXAMPLES_DIR/aws-resources" ]]; then
                cp -r "$DEFAULT_EXAMPLES_DIR/aws-resources/src/"* "$output_dir/src/"
                cp -r "$DEFAULT_EXAMPLES_DIR/aws-resources/terraform-examples/"* "$output_dir/terraform-examples/"
            else
                log_warning "AWS template not found, using simple template"
                cp -r "$DEFAULT_EXAMPLES_DIR/simple-provider/src/"* "$output_dir/src/"
            fi
            ;;
        "database")
            log_info "Creating database provider template..."
            if [[ -d "$DEFAULT_EXAMPLES_DIR/database-provider" ]]; then
                cp -r "$DEFAULT_EXAMPLES_DIR/database-provider/src/"* "$output_dir/src/"
                cp -r "$DEFAULT_EXAMPLES_DIR/database-provider/terraform-examples/"* "$output_dir/terraform-examples/"
                cp "$DEFAULT_EXAMPLES_DIR/database-provider/docker-compose.yml" "$output_dir/"
            else
                log_warning "Database template not found, using simple template"
                cp -r "$DEFAULT_EXAMPLES_DIR/simple-provider/src/"* "$output_dir/src/"
            fi
            ;;
        *)
            log_error "Unknown template: $template"
            log_info "Available templates: simple, aws, database"
            return 1
            ;;
    esac
    
    # Create build and test scripts
    cat > "$output_dir/build.sh" << 'EOF'
#!/bin/bash
set -euo pipefail

# Build script generated by flavor-dev-tools
flavor-dev-tools build --project-dir .
EOF
    chmod +x "$output_dir/build.sh"
    
    cat > "$output_dir/test.sh" << 'EOF'
#!/bin/bash
set -euo pipefail

# Test script generated by flavor-dev-tools
flavor-dev-tools test --project-dir .
EOF
    chmod +x "$output_dir/test.sh"
    
    # Create project configuration
    cat > "$output_dir/flavor-project.yml" << EOF
name: "$project_name"
version: "1.0.0"
description: "PSPF provider created with flavor-dev-tools"
template: "$template"
created: "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

build:
  source_dir: "./src"
  output_dir: "./dist"
  
test:
  unit_dir: "./tests/unit"
  integration_dir: "./tests/integration"
  
signing:
  keys_dir: "./keys"
  
examples:
  terraform_dir: "./terraform-examples"
EOF
    
    # Create README
    cat > "$output_dir/README.md" << EOF
# $project_name

PSPF Terraform provider created with flavor-dev-tools.

## Quick Start

\`\`\`bash
# Build the provider
./build.sh

# Run tests
./test.sh

# Try examples
cd terraform-examples/basic
terraform init
terraform plan
\`\`\`

## Development

This project was generated using the **$template** template.

- **Source code**: \`src/\`
- **Tests**: \`tests/\`
- **Examples**: \`terraform-examples/\`
- **Configuration**: \`flavor-project.yml\`

## Commands

\`\`\`bash
# Full development workflow
flavor-dev-tools build --project-dir .
flavor-dev-tools test --project-dir .
flavor-dev-tools validate dist/terraform-provider-*

# Release workflow
flavor-dev-tools release --project-dir . --version v1.0.0
\`\`\`

## Learn More

- [PSPF Documentation](https://github.com/your-org/flavor/docs)
- [Examples](https://github.com/your-org/flavor/docs/examples)
- [CLI Reference](https://github.com/your-org/flavor/docs/cli-reference.md)
EOF
    
    log_success "Project created successfully: $output_dir"
    log_info "Next steps:"
    log_info "  cd $output_dir"
    log_info "  ./build.sh"
    log_info "  ./test.sh"
}

build_project() {
    local project_dir="${1:-.}"
    local output_name="$2"
    local version="${3:-dev}"
    
    log_info "Building PSPF project in: $project_dir"
    
    cd "$project_dir"
    
    # Load project configuration if it exists
    local project_config="flavor-project.yml"
    local project_name="terraform-provider-example"
    
    if [[ -f "$project_config" ]]; then
        if command -v yq &> /dev/null; then
            project_name=$(yq e '.name' "$project_config" 2>/dev/null || echo "terraform-provider-example")
            version=$(yq e '.version' "$project_config" 2>/dev/null || echo "$version")
        fi
    fi
    
    # Use provided output name or derive from project
    if [[ -z "$output_name" ]]; then
        output_name="${project_name}_${version}"
    fi
    
    log_info "Building package: $output_name"
    log_verbose "Version: $version"
    
    # Ensure directories exist
    mkdir -p keys dist
    
    # Generate keys if they don't exist
    if [[ ! -f "keys/provider-private.key" ]]; then
        log_info "Generating signing keys..."
        flavor-packager keygen --out-dir keys
    fi
    
    # Build the package
    log_info "Building PSPF package..."
    flavor-packager build \
        --out "dist/$output_name" \
        --payload-dir ./src \
        --package-key ./keys/provider-private.key \
        --public-key ./keys/provider-public.key \
        --launcher-bin "$(which flavor-launcher)"
    
    # Verify the package
    log_info "Verifying package..."
    flavor-packager verify "dist/$output_name"
    
    # Test basic functionality
    log_info "Testing package functionality..."
    chmod +x "dist/$output_name"
    "dist/$output_name" --version
    "dist/$output_name" --help > /dev/null
    
    log_success "Build completed: dist/$output_name"
    log_info "Package size: $(du -h "dist/$output_name" | cut -f1)"
}

test_project() {
    local project_dir="${1:-.}"
    local test_type="${2:-all}"
    
    log_info "Running tests for project in: $project_dir"
    
    cd "$project_dir"
    
    case "$test_type" in
        "unit")
            log_info "Running unit tests..."
            if [[ -d "tests/unit" ]]; then
                python3 -m pytest tests/unit/ -v
            else
                log_warning "No unit tests found"
            fi
            ;;
        "integration")
            log_info "Running integration tests..."
            if [[ -d "tests/integration" ]]; then
                python3 -m pytest tests/integration/ -v
            else
                log_warning "No integration tests found"
            fi
            ;;
        "terraform")
            log_info "Running Terraform integration tests..."
            if [[ -d "terraform-examples" ]]; then
                for example_dir in terraform-examples/*/; do
                    if [[ -d "$example_dir" ]]; then
                        log_info "Testing example: $(basename "$example_dir")"
                        (cd "$example_dir" && terraform init && terraform validate && terraform plan)
                    fi
                done
            else
                log_warning "No Terraform examples found"
            fi
            ;;
        "all"|*)
            log_info "Running all tests..."
            test_project "$project_dir" "unit"
            test_project "$project_dir" "integration"
            test_project "$project_dir" "terraform"
            ;;
    esac
    
    log_success "Tests completed"
}

benchmark_project() {
    local project_dir="${1:-.}"
    local package_path="$2"
    local compare_versions="${3:-false}"
    
    log_info "Running performance benchmarks..."
    
    cd "$project_dir"
    
    # Find package if not specified
    if [[ -z "$package_path" ]]; then
        package_path=$(find dist/ -name "terraform-provider-*" -type f | head -1)
    fi
    
    if [[ ! -f "$package_path" ]]; then
        log_error "Package not found: $package_path"
        return 1
    fi
    
    chmod +x "$package_path"
    
    log_info "Benchmarking package: $package_path"
    
    # Check if hyperfine is available
    if command -v hyperfine &> /dev/null; then
        log_info "Running startup time benchmark..."
        hyperfine --warmup 3 --min-runs 10 "$package_path --version"
        
        log_info "Running help command benchmark..."
        hyperfine --warmup 2 --min-runs 5 "$package_path --help"
        
        if "$package_path" --schema &> /dev/null; then
            log_info "Running schema generation benchmark..."
            hyperfine --warmup 2 --min-runs 5 "$package_path --schema"
        fi
    else
        log_warning "hyperfine not found, using basic timing..."
        
        log_info "Startup time:"
        time "$package_path" --version
        
        log_info "Help command time:"
        time "$package_path" --help > /dev/null
    fi
    
    # Memory usage
    if command -v /usr/bin/time &> /dev/null; then
        log_info "Memory usage:"
        /usr/bin/time -v "$package_path" --version 2>&1 | grep -E "(Maximum resident set size|Peak memory)"
    fi
    
    # Package size analysis
    log_info "Package size: $(du -h "$package_path" | cut -f1)"
    log_info "Package info:"
    flavor-packager info "$package_path" | head -20
    
    log_success "Benchmarking completed"
}

validate_package() {
    local package_path="$1"
    
    log_info "Validating PSPF package: $package_path"
    
    if [[ ! -f "$package_path" ]]; then
        log_error "Package not found: $package_path"
        return 1
    fi
    
    # PSPF format validation
    log_info "Checking PSPF format integrity..."
    if flavor-packager verify "$package_path"; then
        log_success "PSPF format validation passed"
    else
        log_error "PSPF format validation failed"
        return 1
    fi
    
    # Functional validation
    log_info "Testing package functionality..."
    chmod +x "$package_path"
    
    if "$package_path" --version > /dev/null 2>&1; then
        log_success "Version command works"
    else
        log_error "Version command failed"
        return 1
    fi
    
    if "$package_path" --help > /dev/null 2>&1; then
        log_success "Help command works"
    else
        log_error "Help command failed"
        return 1
    fi
    
    # Schema validation (if supported)
    if "$package_path" --schema > /dev/null 2>&1; then
        log_info "Validating schema output..."
        if "$package_path" --schema | python3 -m json.tool > /dev/null 2>&1; then
            log_success "Schema output is valid JSON"
        else
            log_warning "Schema output is not valid JSON"
        fi
    fi
    
    # Security validation
    log_info "Checking security properties..."
    
    # Check file permissions
    local perms=$(stat -c %a "$package_path" 2>/dev/null || stat -f %A "$package_path" 2>/dev/null || echo "755")
    if [[ "$perms" == "755" ]] || [[ "$perms" == "0755" ]]; then
        log_success "File permissions are correct"
    else
        log_warning "File permissions are $perms (expected 755)"
    fi
    
    log_success "Package validation completed"
}

examples_command() {
    local subcommand="$1"
    local example_name="${2:-}"
    
    case "$subcommand" in
        "list")
            log_info "Available examples:"
            if [[ -d "$DEFAULT_EXAMPLES_DIR" ]]; then
                for example in "$DEFAULT_EXAMPLES_DIR"/*/; do
                    if [[ -d "$example" ]]; then
                        local name=$(basename "$example")
                        local readme="$example/README.md"
                        if [[ -f "$readme" ]]; then
                            local desc=$(head -10 "$readme" | grep -E "^#.*Example" | sed 's/^# *//' | head -1)
                            echo -e "  ${GREEN}$name${NC}: $desc"
                        else
                            echo -e "  ${GREEN}$name${NC}"
                        fi
                    fi
                done
            fi
            ;;
        "build")
            if [[ -n "$example_name" ]]; then
                log_info "Building example: $example_name"
                local example_dir="$DEFAULT_EXAMPLES_DIR/$example_name"
                if [[ -d "$example_dir" ]]; then
                    (cd "$example_dir" && bash build.sh)
                else
                    log_error "Example not found: $example_name"
                    return 1
                fi
            else
                log_info "Building all examples..."
                for example in "$DEFAULT_EXAMPLES_DIR"/*/; do
                    if [[ -d "$example" && -f "$example/build.sh" ]]; then
                        local name=$(basename "$example")
                        log_info "Building $name..."
                        (cd "$example" && bash build.sh)
                    fi
                done
            fi
            ;;
        "test")
            if [[ -n "$example_name" ]]; then
                log_info "Testing example: $example_name"
                local example_dir="$DEFAULT_EXAMPLES_DIR/$example_name"
                if [[ -d "$example_dir" ]]; then
                    (cd "$example_dir" && bash test.sh)
                else
                    log_error "Example not found: $example_name"
                    return 1
                fi
            else
                log_info "Testing all examples..."
                for example in "$DEFAULT_EXAMPLES_DIR"/*/; do
                    if [[ -d "$example" && -f "$example/test.sh" ]]; then
                        local name=$(basename "$example")
                        log_info "Testing $name..."
                        (cd "$example" && bash test.sh)
                    fi
                done
            fi
            ;;
        *)
            log_error "Unknown examples subcommand: $subcommand"
            log_info "Available subcommands: list, build, test"
            return 1
            ;;
    esac
}

doctor_check() {
    log_info "Running PSPF development environment diagnostics..."
    
    local issues=0
    
    # Check PSPF tools
    log_info "Checking PSPF tools..."
    if command -v flavor-packager &> /dev/null; then
        local version=$(flavor-packager --version 2>/dev/null || echo "unknown")
        log_success "flavor-packager found: $version"
    else
        log_error "flavor-packager not found"
        ((issues++))
    fi
    
    if command -v flavor-launcher &> /dev/null; then
        local version=$(flavor-launcher --version 2>/dev/null || echo "unknown")
        log_success "flavor-launcher found: $version"
    else
        log_error "flavor-launcher not found"
        ((issues++))
    fi
    
    # Check Python
    log_info "Checking Python environment..."
    if command -v python3 &> /dev/null; then
        local python_version=$(python3 --version)
        log_success "Python found: $python_version"
        
        # Check if we can import pytest
        if python3 -c "import pytest" 2>/dev/null; then
            log_success "pytest available"
        else
            log_warning "pytest not found (needed for testing)"
        fi
    else
        log_error "python3 not found"
        ((issues++))
    fi
    
    # Check Terraform
    log_info "Checking Terraform..."
    if command -v terraform &> /dev/null; then
        local tf_version=$(terraform version | head -1)
        log_success "Terraform found: $tf_version"
    else
        log_warning "terraform not found (needed for integration testing)"
    fi
    
    # Check Docker
    log_info "Checking Docker..."
    if command -v docker &> /dev/null && docker info &> /dev/null; then
        local docker_version=$(docker --version)
        log_success "Docker found and running: $docker_version"
    else
        log_warning "docker not found or not running (needed for some examples)"
    fi
    
    # Check optional tools
    log_info "Checking optional tools..."
    
    local optional_tools=("hyperfine" "jq" "yq" "cosign")
    for tool in "${optional_tools[@]}"; do
        if command -v "$tool" &> /dev/null; then
            log_success "$tool available"
        else
            log_warning "$tool not found (optional but recommended)"
        fi
    done
    
    # Check examples directory
    log_info "Checking examples directory..."
    if [[ -d "$DEFAULT_EXAMPLES_DIR" ]]; then
        local example_count=$(find "$DEFAULT_EXAMPLES_DIR" -mindepth 1 -maxdepth 1 -type d | wc -l)
        log_success "Examples directory found with $example_count examples"
    else
        log_warning "Examples directory not found: $DEFAULT_EXAMPLES_DIR"
    fi
    
    # Summary
    echo ""
    if [[ $issues -eq 0 ]]; then
        log_success "Environment check passed! Ready for PSPF development."
    else
        log_error "Found $issues critical issues. Please resolve them before continuing."
        log_info "Installation guide: https://github.com/your-org/flavor/docs/installation.md"
        return 1
    fi
}

clean_artifacts() {
    local clean_type="${1:-build}"
    local project_dir="${2:-.}"
    
    cd "$project_dir"
    
    case "$clean_type" in
        "build")
            log_info "Cleaning build artifacts..."
            rm -rf dist/ build/
            log_success "Build artifacts cleaned"
            ;;
        "cache")
            log_info "Cleaning caches..."
            rm -rf "$DEFAULT_CACHE_DIR"
            rm -rf .pytest_cache/ __pycache__/ .coverage
            find . -name "*.pyc" -delete
            find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
            log_success "Cache cleaned"
            ;;
        "terraform")
            log_info "Cleaning Terraform artifacts..."
            find . -name ".terraform" -type d -exec rm -rf {} + 2>/dev/null || true
            find . -name ".terraform.lock.hcl" -delete 2>/dev/null || true
            find . -name "terraform.tfstate*" -delete 2>/dev/null || true
            log_success "Terraform artifacts cleaned"
            ;;
        "all")
            clean_artifacts "build" "$project_dir"
            clean_artifacts "cache" "$project_dir"
            clean_artifacts "terraform" "$project_dir"
            ;;
        *)
            log_error "Unknown clean type: $clean_type"
            log_info "Available types: build, cache, terraform, all"
            return 1
            ;;
    esac
}

# Parse global options and command
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --verbose|-v)
                export VERBOSE=true
                shift
                ;;
            --quiet|-q)
                export QUIET=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            --version)
                echo "flavor-dev-tools $VERSION"
                exit 0
                ;;
            *)
                break
                ;;
        esac
    done
    
    if [[ $# -eq 0 ]]; then
        show_help
        exit 0
    fi
    
    # Load environment variables
    EXAMPLES_DIR="${FLAVOR_DEV_EXAMPLES_DIR:-$DEFAULT_EXAMPLES_DIR}"
    BUILD_DIR="${FLAVOR_DEV_BUILD_DIR:-$DEFAULT_BUILD_DIR}"
    CACHE_DIR="${FLAVOR_DEV_CACHE_DIR:-$DEFAULT_CACHE_DIR}"
    
    if [[ "${FLAVOR_DEV_VERBOSE:-}" == "1" ]] || [[ "${FLAVOR_DEV_VERBOSE:-}" == "true" ]]; then
        export VERBOSE=true
    fi
    
    # Execute command
    local command="$1"
    shift
    
    case "$command" in
        "init")
            if [[ $# -eq 0 ]]; then
                log_error "Project name required"
                log_info "Usage: flavor-dev-tools init <PROJECT_NAME> [--template TEMPLATE] [--output DIR]"
                exit 1
            fi
            
            local project_name="$1"
            local template="simple"
            local output_dir="$project_name"
            
            shift
            while [[ $# -gt 0 ]]; do
                case $1 in
                    --template)
                        template="$2"
                        shift 2
                        ;;
                    --output)
                        output_dir="$2"
                        shift 2
                        ;;
                    *)
                        log_error "Unknown option: $1"
                        exit 1
                        ;;
                esac
            done
            
            check_dependencies
            init_project "$project_name" "$template" "$output_dir"
            ;;
        "build")
            local project_dir="."
            local output_name=""
            local version="dev"
            
            while [[ $# -gt 0 ]]; do
                case $1 in
                    --project-dir)
                        project_dir="$2"
                        shift 2
                        ;;
                    --output)
                        output_name="$2"
                        shift 2
                        ;;
                    --version)
                        version="$2"
                        shift 2
                        ;;
                    *)
                        log_error "Unknown option: $1"
                        exit 1
                        ;;
                esac
            done
            
            check_dependencies
            build_project "$project_dir" "$output_name" "$version"
            ;;
        "test")
            local project_dir="."
            local test_type="all"
            
            while [[ $# -gt 0 ]]; do
                case $1 in
                    --project-dir)
                        project_dir="$2"
                        shift 2
                        ;;
                    --type)
                        test_type="$2"
                        shift 2
                        ;;
                    *)
                        log_error "Unknown option: $1"
                        exit 1
                        ;;
                esac
            done
            
            test_project "$project_dir" "$test_type"
            ;;
        "benchmark")
            local project_dir="."
            local package_path=""
            local compare_versions="false"
            
            while [[ $# -gt 0 ]]; do
                case $1 in
                    --project-dir)
                        project_dir="$2"
                        shift 2
                        ;;
                    --package)
                        package_path="$2"
                        shift 2
                        ;;
                    --compare-versions)
                        compare_versions="true"
                        shift
                        ;;
                    *)
                        log_error "Unknown option: $1"
                        exit 1
                        ;;
                esac
            done
            
            benchmark_project "$project_dir" "$package_path" "$compare_versions"
            ;;
        "validate")
            if [[ $# -eq 0 ]]; then
                log_error "Package path required"
                log_info "Usage: flavor-dev-tools validate <PACKAGE_PATH>"
                exit 1
            fi
            
            validate_package "$1"
            ;;
        "examples")
            if [[ $# -eq 0 ]]; then
                examples_command "list"
            else
                examples_command "$@"
            fi
            ;;
        "doctor")
            doctor_check
            ;;
        "clean")
            local clean_type="build"
            local project_dir="."
            
            while [[ $# -gt 0 ]]; do
                case $1 in
                    --type)
                        clean_type="$2"
                        shift 2
                        ;;
                    --project-dir)
                        project_dir="$2"
                        shift 2
                        ;;
                    --all)
                        clean_type="all"
                        shift
                        ;;
                    *)
                        log_error "Unknown option: $1"
                        exit 1
                        ;;
                esac
            done
            
            clean_artifacts "$clean_type" "$project_dir"
            ;;
        *)
            log_error "Unknown command: $command"
            log_info "Available commands: init, build, test, benchmark, validate, examples, doctor, clean"
            log_info "Run 'flavor-dev-tools --help' for more information"
            exit 1
            ;;
    esac
}

# Main execution
main() {
    parse_args "$@"
}

# Only run main if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi


# 📦🍜📄🪄
