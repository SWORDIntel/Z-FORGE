# Workspace Directory Fixes Summary

## Issue
Several modules were trying to write to `/tmp/zforge_workspace/` before the WorkspaceSetup module created it, causing build failures.

## Root Cause
The new optimization modules run in Phase 0 (before WorkspaceSetup in Phase 1) but were trying to save files to the workspace directory.

## Fixed Modules

### 1. **MirrorSelector** (`mirror_selector.py`)
- **Original**: Saved to `workspace/selected_mirrors.txt`
- **Fixed**: Now saves to `~/.cache/zforge/selected_mirrors.txt`
- **Benefit**: Mirror selection persists across builds

### 2. **BuildOptimizer** (`build_optimizer.py`)
- **Original**: Saved to `workspace/build_optimizations.conf`
- **Fixed**: Now saves to `~/.cache/zforge/build_optimizations.conf`
- **Also**: Copies to workspace after WorkspaceSetup if workspace exists
- **Benefit**: Optimizations available immediately and persist

### 3. **ProgressMonitor** (`progress_monitor.py`)
- **Original**: Saved to `workspace/build_progress_monitor.json` and `workspace.parent/build_history.json`
- **Fixed**: Now saves to `~/.cache/zforge/build_progress_monitor.json` and `~/.cache/zforge/build_history.json`
- **Benefit**: Progress tracking persists across builds for better ETAs

## Modules Already Correct

### 4. **BuildCache** (`build_cache.py`)
- Already used `~/.cache/zforge/` from the start
- No changes needed

### 5. **SystemPrerequisites** (`system_prerequisites.py`)
- Doesn't write any files
- No changes needed

### 6. **AutoInstallDeps** (`auto_install_deps.py`)
- Doesn't write any files
- No changes needed

### 7. **ModuleVerifier** (`module_verifier.py`)
- Uses relative paths from module location
- Creates stub files in the modules directory (not workspace)
- No changes needed

### 8. **CleanupHandler** (`cleanup_handler.py`)
- Runs in Phase 7 (after workspace exists)
- Needs workspace to exist for cleanup operations
- No changes needed

## Architecture Decision

All build metadata and cache files are now stored in `~/.cache/zforge/` which:
- Survives workspace cleanup
- Enables faster subsequent builds
- Allows Phase 0 modules to run before workspace creation
- Provides persistent storage for optimization data

## Module Execution Order

```
Phase 0: Pre-Build (no workspace yet)
  - SystemPrerequisites
  - AutoInstallDeps
  - MirrorSelector      → ~/.cache/zforge/
  - BuildCache          → ~/.cache/zforge/
  - BuildOptimizer      → ~/.cache/zforge/
  - ModuleVerifier
  - ProgressMonitor     → ~/.cache/zforge/

Phase 1: Base System Setup
  - WorkspaceSetup      ← Creates /tmp/zforge_workspace/
  - Debootstrap
  - NonInteractiveFixes
  
... rest of build ...
```