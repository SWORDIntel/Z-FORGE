#!/bin/bash
# Z-FORGE HPC Build System Integration Script
# Automatically integrates HPC capabilities into the main Z-FORGE build system

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
BUILD_PY="$PROJECT_ROOT/build.py"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_stage() {
    echo -e "\n${PURPLE}=== $1 ===${NC}"
}

# Check if build.py exists
check_build_system() {
    log_stage "Checking Z-FORGE Build System"
    
    if [[ ! -f "$BUILD_PY" ]]; then
        log_error "Main build.py not found at: $BUILD_PY"
        return 1
    fi
    
    log_success "Found main build system: $BUILD_PY"
    
    # Check if HPC integration is already present
    if grep -q "hpc_build_integration" "$BUILD_PY" 2>/dev/null; then
        log_info "HPC integration already present in build.py"
        return 0
    else
        log_info "HPC integration not yet integrated"
        return 2
    fi
}

# Create HPC build launcher script
create_hpc_build_launcher() {
    log_stage "Creating HPC Build Launcher"
    
    local hpc_launcher="$PROJECT_ROOT/build_hpc.py"
    
    cat > "$hpc_launcher" << 'EOF'
#!/usr/bin/env python3
"""
Z-FORGE HPC Build Launcher
Enhanced build launcher with integrated HPC capabilities
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Add project root and HPC scripts to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "scripts" / "hpc"))

try:
    from scripts.hpc.hpc_build_integration import HPCBuildIntegration
    HPC_INTEGRATION_AVAILABLE = True
except ImportError as e:
    print(f"Warning: HPC integration not available: {e}")
    HPC_INTEGRATION_AVAILABLE = False

# Import original build functionality
try:
    import build
    ORIGINAL_BUILD_AVAILABLE = True
except ImportError:
    try:
        # Try importing from builder.core
        sys.path.insert(0, str(project_root / "builder"))
        from core.builder import BuildOrchestrator
        ORIGINAL_BUILD_AVAILABLE = True
    except ImportError as e:
        print(f"Error: Could not import build system: {e}")
        ORIGINAL_BUILD_AVAILABLE = False


def setup_logging(debug: bool = False) -> logging.Logger:
    """Setup logging for HPC build launcher"""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='[%(levelname)s] %(message)s'
    )
    return logging.getLogger(__name__)


def main():
    """Main HPC build launcher"""
    parser = argparse.ArgumentParser(description="Z-FORGE HPC Build Launcher")
    parser.add_argument("--spec", required=True, help="Build specification file")
    parser.add_argument("--workspace", help="Build workspace directory")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--hpc-only", action="store_true", help="HPC preparation only")
    parser.add_argument("--no-hpc", action="store_true", help="Skip HPC integration")
    parser.add_argument("--validate-only", action="store_true", help="HPC validation only")
    
    args = parser.parse_args()
    
    logger = setup_logging(args.debug)
    
    if not ORIGINAL_BUILD_AVAILABLE and not args.hpc_only and not args.validate_only:
        logger.error("Original build system not available")
        return 1
        
    if not HPC_INTEGRATION_AVAILABLE:
        if args.hpc_only or args.validate_only:
            logger.error("HPC integration not available")
            return 1
        logger.warning("HPC integration not available, running standard build")
        args.no_hpc = True
    
    # Initialize HPC integration
    hpc_integration = None
    if HPC_INTEGRATION_AVAILABLE and not args.no_hpc:
        hpc_integration = HPCBuildIntegration(project_root, logger)
    
    spec_file = Path(args.spec)
    if not spec_file.exists():
        # Try relative to build_specs directory
        spec_file = project_root / "build_specs" / args.spec
        if not spec_file.exists():
            logger.error(f"Build specification not found: {args.spec}")
            return 1
    
    # Check if this is an HPC build
    is_hpc_build = False
    if hpc_integration:
        is_hpc_build = hpc_integration.is_hpc_build_spec(spec_file)
        if is_hpc_build:
            logger.info(f"Detected HPC build specification: {spec_file.name}")
        else:
            logger.info(f"Standard build specification: {spec_file.name}")
    
    # HPC validation only mode
    if args.validate_only:
        if not hpc_integration:
            logger.error("HPC integration required for validation")
            return 1
            
        logger.info("Running HPC performance validation...")
        validation_results = hpc_integration.run_hpc_validation()
        
        if validation_results.get("status") == "completed":
            logger.info("HPC validation completed successfully")
            return 0
        else:
            logger.error("HPC validation failed or incomplete")
            return 1
    
    # HPC preparation
    hpc_env = {}
    if hpc_integration and is_hpc_build:
        logger.info("Running HPC preparation...")
        
        if not hpc_integration.run_hpc_preparation(spec_file):
            logger.error("HPC preparation failed")
            return 1
            
        # Get HPC environment variables
        hpc_env = hpc_integration.prepare_hpc_environment(spec_file)
        for key, value in hpc_env.items():
            os.environ[key] = value
            logger.debug(f"Set HPC environment: {key}={value}")
    
    # HPC preparation only mode
    if args.hpc_only:
        logger.info("HPC preparation completed (preparation-only mode)")
        return 0
    
    # Run main build
    logger.info("Starting main build process...")
    
    try:
        # Set workspace if provided
        if args.workspace:
            os.environ['WORKSPACE'] = args.workspace
        elif 'HPC_WORKSPACE' in hpc_env:
            os.environ['WORKSPACE'] = hpc_env['HPC_WORKSPACE']
            
        # Try to run original build system
        build_args = ['--spec', str(spec_file)]
        if args.workspace:
            build_args.extend(['--workspace', args.workspace])
        if args.debug:
            build_args.append('--debug')
            
        # Import and run original build
        if hasattr(build, 'main'):
            # build.py has main function
            sys.argv = ['build.py'] + build_args
            build.main()
        else:
            # Try using BuildOrchestrator directly
            from builder.core.builder import BuildOrchestrator
            orchestrator = BuildOrchestrator(spec_file, logger=logger)
            result = orchestrator.run_build()
            if not result.get('success', False):
                raise RuntimeError("Build failed")
                
        logger.info("Main build completed successfully")
        
    except Exception as e:
        logger.error(f"Build failed: {e}")
        return 1
    
    # Post-build HPC validation
    if hpc_integration and is_hpc_build:
        logger.info("Running post-build HPC validation...")
        
        validation_results = hpc_integration.run_hpc_validation()
        
        if validation_results.get("status") == "completed":
            logger.info("Post-build HPC validation completed successfully")
            
            # Display key performance metrics
            if "performance_summary" in validation_results:
                perf_summary = validation_results["performance_summary"]
                logger.info(f"HPC Readiness: {perf_summary.get('hpc_readiness', 'Unknown')}")
                logger.info(f"Overall Status: {perf_summary.get('overall_status', 'Unknown')}")
                
        else:
            logger.warning("Post-build HPC validation failed or incomplete")
            logger.warning("Build succeeded but HPC performance may be suboptimal")
    
    logger.info("HPC build process completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
EOF
    
    chmod +x "$hpc_launcher"
    log_success "Created HPC build launcher: $hpc_launcher"
}

# Create HPC build wrapper for existing build.py
create_build_py_wrapper() {
    log_stage "Creating build.py HPC Wrapper"
    
    # Backup original build.py
    if [[ -f "$BUILD_PY" ]]; then
        local backup_file="${BUILD_PY}.pre-hpc-$(date +%Y%m%d_%H%M%S)"
        cp "$BUILD_PY" "$backup_file"
        log_info "Backed up original build.py to: $backup_file"
    fi
    
    # Create new build.py that includes HPC integration
    cat > "$BUILD_PY" << 'EOF'
#!/usr/bin/env python3
"""
Z-FORGE Build Launcher with HPC Integration
Enhanced build system with automatic HPC detection and integration
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "scripts" / "hpc"))

# Import HPC integration if available
try:
    from scripts.hpc.hpc_build_integration import HPCBuildIntegration
    HPC_AVAILABLE = True
except ImportError:
    HPC_AVAILABLE = False
    print("Warning: HPC integration not available")

# Import original build functionality
try:
    # Try to import original build functions
    sys.path.insert(0, str(project_root / "builder"))
    from core.builder import BuildOrchestrator
    BUILDER_AVAILABLE = True
except ImportError:
    BUILDER_AVAILABLE = False
    print("Error: Core build system not available")


def main():
    """Enhanced main function with HPC integration"""
    parser = argparse.ArgumentParser(description="Z-FORGE Build System with HPC Integration")
    parser.add_argument("--spec", required=True, help="Build specification file")
    parser.add_argument("--workspace", help="Build workspace directory")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--hpc-detect", action="store_true", help="Detect and recommend HPC configuration")
    parser.add_argument("--force-hpc", action="store_true", help="Force HPC build even for non-HPC specs")
    parser.add_argument("--no-hpc", action="store_true", help="Disable HPC integration")
    
    args = parser.parse_args()
    
    # Setup logging
    level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=level, format='[%(levelname)s] %(message)s')
    logger = logging.getLogger(__name__)
    
    if not BUILDER_AVAILABLE:
        logger.error("Core build system not available")
        return 1
    
    # HPC detection mode
    if args.hpc_detect:
        if not HPC_AVAILABLE:
            logger.error("HPC integration not available for detection")
            return 1
            
        hpc_integration = HPCBuildIntegration(project_root, logger)
        hardware_info = hpc_integration.detect_hpc_hardware()
        
        if hardware_info['hpc_capable']:
            recommended_spec = hpc_integration.recommend_hpc_spec(hardware_info)
            if recommended_spec:
                print(f"Recommended HPC build specification: {recommended_spec.name}")
                print("Run with: python3 build.py --spec " + recommended_spec.name)
            else:
                print("HPC hardware detected but no suitable build specification found")
        else:
            print("No HPC hardware detected")
            
        return 0
    
    # Resolve spec file path
    spec_file = Path(args.spec)
    if not spec_file.exists():
        spec_file = project_root / "build_specs" / args.spec
        if not spec_file.exists():
            logger.error(f"Build specification not found: {args.spec}")
            return 1
    
    # HPC integration logic
    use_hpc = False
    hpc_integration = None
    
    if HPC_AVAILABLE and not args.no_hpc:
        hpc_integration = HPCBuildIntegration(project_root, logger)
        
        # Check if this should be an HPC build
        is_hpc_spec = hpc_integration.is_hpc_build_spec(spec_file)
        
        if args.force_hpc or is_hpc_spec:
            use_hpc = True
            logger.info("Using HPC build integration")
            
            # Run HPC preparation
            if not hpc_integration.run_hpc_preparation(spec_file):
                logger.error("HPC preparation failed")
                return 1
                
            # Set HPC environment
            hpc_env = hpc_integration.prepare_hpc_environment(spec_file)
            for key, value in hpc_env.items():
                os.environ[key] = value
        else:
            logger.info("Using standard build (non-HPC specification)")
    
    # Set workspace
    if args.workspace:
        os.environ['WORKSPACE'] = args.workspace
    elif use_hpc and 'HPC_WORKSPACE' in os.environ:
        os.environ['WORKSPACE'] = os.environ['HPC_WORKSPACE']
    
    # Run build
    try:
        logger.info(f"Starting build with specification: {spec_file.name}")
        
        orchestrator = BuildOrchestrator(spec_file, logger=logger)
        result = orchestrator.run_build()
        
        if not result.get('success', False):
            logger.error("Build failed")
            return 1
            
        logger.info("Build completed successfully")
        
    except Exception as e:
        logger.error(f"Build error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1
    
    # Post-build HPC validation
    if use_hpc and hpc_integration:
        logger.info("Running post-build HPC validation...")
        validation_results = hpc_integration.run_hpc_validation()
        
        if validation_results.get("status") == "completed":
            logger.info("HPC validation completed successfully")
        else:
            logger.warning("HPC validation incomplete - performance may be suboptimal")
    
    logger.info("Build process completed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
EOF
    
    chmod +x "$BUILD_PY"
    log_success "Enhanced build.py with HPC integration"
}

# Make HPC scripts executable
make_hpc_scripts_executable() {
    log_stage "Making HPC Scripts Executable"
    
    local hpc_scripts=(
        "prepare-hpc-compilation.sh"
        "scripts/hpc/compile_cuda_hpc.sh"
        "scripts/hpc/compile_intel_phi_hpc.sh"
        "scripts/hpc/compile_scientific_libs_hpc.sh"
        "scripts/hpc/validate_hpc_performance.sh"
        "scripts/hpc/hpc_build_integration.py"
        "scripts/hpc/integrate_hpc_build_system.sh"
    )
    
    for script in "${hpc_scripts[@]}"; do
        local script_path="$PROJECT_ROOT/$script"
        if [[ -f "$script_path" ]]; then
            chmod +x "$script_path"
            log_success "Made executable: $script"
        else
            log_warn "Script not found: $script"
        fi
    done
}

# Create HPC quick command shortcuts
create_hpc_shortcuts() {
    log_stage "Creating HPC Command Shortcuts"
    
    # Create hpc-build command
    cat > "$PROJECT_ROOT/hpc-build" << EOF
#!/bin/bash
# Z-FORGE HPC Build Shortcut
# Quick launcher for HPC builds with automatic hardware detection

cd "\$(dirname "\$0")"

# Auto-detect HPC hardware and recommend specification
if [[ "\$1" == "--auto" ]] || [[ "\$1" == "--detect" ]]; then
    echo "Detecting HPC hardware..."
    python3 scripts/hpc/hpc_build_integration.py --recommend
    exit 0
fi

# HPC preparation only
if [[ "\$1" == "--prepare" ]]; then
    if [[ -z "\$2" ]]; then
        echo "Usage: ./hpc-build --prepare <spec_file>"
        exit 1
    fi
    echo "Running HPC preparation for \$2..."
    python3 scripts/hpc/hpc_build_integration.py --prepare "\$2"
    exit \$?
fi

# HPC validation only
if [[ "\$1" == "--validate" ]]; then
    echo "Running HPC performance validation..."
    python3 scripts/hpc/hpc_build_integration.py --validate
    exit \$?
fi

# Full HPC build
if [[ -z "\$1" ]]; then
    echo "Z-FORGE HPC Build System"
    echo "Usage:"
    echo "  ./hpc-build <spec_file>     - Run HPC build"
    echo "  ./hpc-build --auto          - Auto-detect and recommend HPC spec"
    echo "  ./hpc-build --prepare <spec> - Run HPC preparation only"
    echo "  ./hpc-build --validate      - Run HPC validation only"
    echo ""
    echo "Available HPC specifications:"
    python3 scripts/hpc/hpc_build_integration.py --list-specs
    exit 0
fi

# Run HPC build
echo "Starting HPC build with specification: \$1"
python3 build_hpc.py --spec "\$1"
EOF
    
    chmod +x "$PROJECT_ROOT/hpc-build"
    log_success "Created HPC build shortcut: ./hpc-build"
    
    # Create hpc-status command
    cat > "$PROJECT_ROOT/hpc-status" << EOF
#!/bin/bash
# Z-FORGE HPC Status Checker
cd "\$(dirname "\$0")"
echo "Z-FORGE HPC System Status"
echo "========================="
python3 scripts/hpc/hpc_build_integration.py --summary
EOF
    
    chmod +x "$PROJECT_ROOT/hpc-status"
    log_success "Created HPC status checker: ./hpc-status"
}

# Validate HPC integration
validate_hpc_integration() {
    log_stage "Validating HPC Integration"
    
    # Check required files
    local required_files=(
        "prepare-hpc-compilation.sh"
        "build_hpc.py"
        "hpc-build"
        "hpc-status"
        "scripts/hpc/hpc_build_integration.py"
        "scripts/hpc/validate_hpc_performance.sh"
        "build_specs/build_spec_hpc_tesla.yml"
        "build_specs/build_spec_hpc_phi.yml"
        "build_specs/build_spec_hpc_dell_t30.yml"
        "build_specs/build_spec_hpc_combined.yml"
    )
    
    local missing_files=()
    for file in "${required_files[@]}"; do
        if [[ ! -f "$PROJECT_ROOT/$file" ]]; then
            missing_files+=("$file")
        fi
    done
    
    if [[ ${#missing_files[@]} -gt 0 ]]; then
        log_error "Missing required files:"
        for file in "${missing_files[@]}"; do
            log_error "  - $file"
        done
        return 1
    fi
    
    # Test HPC integration import
    if python3 -c "
import sys; 
sys.path.insert(0, '$PROJECT_ROOT/scripts/hpc'); 
from hpc_build_integration import HPCBuildIntegration;
print('HPC integration import successful')
" 2>/dev/null; then
        log_success "HPC integration import test passed"
    else
        log_error "HPC integration import test failed"
        return 1
    fi
    
    # Test HPC detection
    if python3 "$PROJECT_ROOT/scripts/hpc/hpc_build_integration.py" --summary >/dev/null 2>&1; then
        log_success "HPC detection test passed"
    else
        log_error "HPC detection test failed"
        return 1
    fi
    
    log_success "HPC integration validation completed successfully"
    return 0
}

# Display integration summary
show_integration_summary() {
    log_stage "HPC Integration Summary"
    
    echo -e "\n${GREEN}Z-FORGE HPC Integration Completed Successfully!${NC}\n"
    
    echo -e "${BLUE}New Commands Available:${NC}"
    echo -e "  ${CYAN}./hpc-build --auto${NC}          - Auto-detect HPC hardware and recommend build"
    echo -e "  ${CYAN}./hpc-build <spec>${NC}          - Run HPC-optimized build"
    echo -e "  ${CYAN}./hpc-build --validate${NC}      - Run HPC performance validation"
    echo -e "  ${CYAN}./hpc-status${NC}                - Show HPC system status"
    echo -e "  ${CYAN}python3 build.py --hpc-detect${NC} - Detect HPC hardware via main build"
    
    echo -e "\n${BLUE}HPC Build Specifications:${NC}"
    echo -e "  ${CYAN}build_spec_hpc_tesla.yml${NC}    - Tesla K40/K80 optimized"
    echo -e "  ${CYAN}build_spec_hpc_phi.yml${NC}      - Intel Xeon Phi optimized"
    echo -e "  ${CYAN}build_spec_hpc_dell_t30.yml${NC} - Dell PowerEdge T30 optimized"
    echo -e "  ${CYAN}build_spec_hpc_combined.yml${NC} - Combined 64GB enterprise build"
    
    echo -e "\n${BLUE}Example Usage:${NC}"
    echo -e "  ${YELLOW}# Auto-detect hardware and get recommendation${NC}"
    echo -e "  ./hpc-build --auto"
    echo -e ""
    echo -e "  ${YELLOW}# Run Tesla-optimized HPC build${NC}"
    echo -e "  ./hpc-build build_spec_hpc_tesla.yml"
    echo -e ""
    echo -e "  ${YELLOW}# Check HPC system status${NC}"
    echo -e "  ./hpc-status"
    echo -e ""
    echo -e "  ${YELLOW}# Run HPC preparation only${NC}"
    echo -e "  ./hpc-build --prepare build_spec_hpc_tesla.yml"
    
    echo -e "\n${BLUE}Integration Features:${NC}"
    echo -e "  ✓ Automatic HPC hardware detection"
    echo -e "  ✓ HPC build specification routing"
    echo -e "  ✓ Tesla K40/K80 CUDA optimization"
    echo -e "  ✓ Intel Xeon Phi many-core optimization"
    echo -e "  ✓ Scientific libraries compilation"
    echo -e "  ✓ Performance validation suite"
    echo -e "  ✓ Dell PowerEdge T30 optimization"
    echo -e "  ✓ Automatic environment configuration"
    
    echo -e "\n${GREEN}HPC integration ready for production use!${NC}"
}

# Main integration workflow
main() {
    log_stage "Z-FORGE HPC Build System Integration"
    
    log_info "Project root: $PROJECT_ROOT"
    
    # Check build system
    check_build_system
    local build_check_result=$?
    
    if [[ $build_check_result -eq 1 ]]; then
        log_error "Build system check failed"
        exit 1
    fi
    
    # Create HPC components
    create_hpc_build_launcher
    create_build_py_wrapper
    make_hpc_scripts_executable
    create_hpc_shortcuts
    
    # Validate integration
    if validate_hpc_integration; then
        show_integration_summary
        log_success "HPC build system integration completed successfully!"
        return 0
    else
        log_error "HPC integration validation failed"
        return 1
    fi
}

# Execute main function
main "$@"