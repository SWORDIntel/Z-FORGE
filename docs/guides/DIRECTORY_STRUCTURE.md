# Z-FORGE Directory Structure

## Root Directory Files
- `Makefile` - Main build system
- `build_spec.yml` - Primary build configuration
- `build_spec_r730xd.yml` - Hardware-specific config
- `README.md` - Project documentation (TODO: create if missing)

## Key Directories
- `builder/` - Core build system
- `calamares/` - Installer modules
- `config/` - Configuration files
- `docs/` - Documentation
- `scripts/` - Organized scripts
  - `build/` - Build scripts
  - `fix/` - Fix and patch scripts
  - `test/` - Test scripts
  - `download/` - Download scripts
  - `agents/` - UltraThink agents
- `tests/` - Test suite
- `logs/` - Build logs
- `proxmox_integration/` - Proxmox VE integration
- `bootloaders/` - Boot configuration
- `archive/` - Archived files

## Important Files
- Main build: `make build`
- Clean: `make clean`
- Help: `make help`
