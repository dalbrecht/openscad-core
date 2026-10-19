# C++ supplement

Retain upstream CMake language level, .clang-format, two-space style and reference
sources. Format only new files. Own parse results with RAII. Check topology,
coordinates, sizes and indices before serialization. Catch all exceptions at the
worker main boundary and keep diagnostics on stderr. Each process handles one
request; do not claim inherited globals are thread-safe. Preserve all upstream and
vendored licenses and regression data. Worker protocol changes require a version
change and compatibility tests. Never silently substitute a final evaluated mesh
for preview leaves/operations. Keep new boundary coverage separate from upstream.
