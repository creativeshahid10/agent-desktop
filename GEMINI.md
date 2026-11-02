# GEMINI.md - agent-desktop Workspace Configuration

This configuration guides Antigravity and AI agents working in this repository (`agent-desktop`).

## Project Overview
`agent-desktop` is a high-performance Rust CLI, C library, and Node package developed for computer use by AI agents. It reads native OS accessibility trees (Windows UI Automation, macOS AX API, Linux AT-SPI) and returns structured JSON with ref-based element IDs.

## Operating Standards & Invariants
- **Host Packages (Windows)**:
  `$HOST_PKGS = @("-p", "agent-desktop-core", "-p", "agent-desktop-windows", "-p", "agent-desktop", "-p", "agent-desktop-ffi")`
- **Build & Test**:
  - Debug build: `cargo build $HOST_PKGS`
  - Release build: `cargo build --release -p agent-desktop`
  - Library tests: `cargo test $HOST_PKGS --lib`
  - Clippy: `cargo clippy $HOST_PKGS --all-targets -- -D warnings`
- **Coding Rules**:
  - Max 400 lines per hand-written `.rs` file.
  - No inline comments (only `///` doc comments for public items and `//!` module docs).
  - Use Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, etc.).
  - Never add AI attribution footers or Co-Authored-By lines.

## Available Workspace Skills
AI agents in this workspace have access to the following skills in `.agents/skills/`:
1. **`arena`** (`.agents/skills/arena/SKILL.md`): Multi-agent competitive tournament solver for difficult coding tasks and architectural decisions.
2. **`security-audit`** (`.agents/skills/security-audit/SKILL.md`): Cloudflare 6-phase vulnerability assessment and source-first security audit engine.
3. **`architecture-diagram`** (`.agents/skills/architecture-diagram/SKILL.md`): Generates standalone SVG/HTML architecture diagrams for docs.
4. **`technical-writer`** (`.agents/skills/technical-writer/SKILL.md`): Standard for documentation, changelogs, and commit messages.
