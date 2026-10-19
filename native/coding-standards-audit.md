# Standards integration

Both repositories pin c65llc/coding-standards at
20ebe761ab14a2f7aa0e523d2058cd2345068cd7, matching the inspected Dust3D integration.
The actual config assembler generates AGENTS.md; setup hooks/global configuration
are unnecessary. Project authorization supersedes suggest-mode repeated approvals
and automatic merging. C++/Swift supplements below resolve shared guidance gaps.

Preserve inherited formatting and identifiers. New worker code uses RAII, checked
indices, finite-coordinate validation and exception containment. No STL or native
pointers cross the process boundary. Swift uses immutable Sendable scene snapshots,
Swift 6 actors and main-actor UI/Metal state. A process is the cancellation boundary.

Coverage must distinguish new scene validation/worker orchestration, adapter code,
legacy OpenSCAD and GPU/UI. Shared 100%/95% goals are not claims about inherited code.
Run real evaluator fixtures and malformed input tests; do not add meaningless tests
to meet coverage. Linux/Windows and adversarial workspace memory remain unverified.
