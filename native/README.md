# Portable native preview worker

Build with CMake using HEADLESS=ON, NULLGL=ON, ENABLE_NATIVE_PREVIEW=ON.
The worker links the upstream C++17 parser/evaluator without Qt or OpenGL.
Run `openscad-preview-worker snapshot.scad [logical-document.scad]`.
The second path supplies include/import context while bytes come from the snapshot.
Success emits one owned UTF-8 JSON object to stdout; diagnostics stay on stderr.
Failure returns nonzero and no successful scene. One request per process.

Protocol v1 has leaves (world-space triangles and RGBA), postorder nodes
(op 0=leaf, 1=union, 2=intersection, 3=difference), root, highlights and backgrounds.
Missing/empty roots use -1. Leaf nodes index leaves through left; operation children
index earlier nodes. Consumers must validate version, limits, coordinates and topology.
No native pointers, allocator or borrowed lifetime crosses this boundary. Keep the
response bytes or copy them before replacing a scene. Separate workers may run
concurrently; no engine state is shared. In-process concurrent use is not promised.

Limits: 4 MiB source, 64 leaves, 127 nodes, 100,000 triangles; client bounds response
size and wall time. Terminating a worker cancels its request and isolates native
faults. Workspace memory is not hard bounded and local file access is retained.
This is an embedding spike, not a stable C ABI or security sandbox.

Tests: `python3 native/tests/test_preview.py build-native/openscad-preview-worker`.
Upstream tests and sources are retained unchanged. New boundary coverage is separate
from legacy engine coverage. Native Apple acceptance and renderer live in
https://github.com/dalbrecht/openscad-apple .

Error-level parser, evaluation and geometry diagnostics fail the request before
any scene is written to stdout. Successful warnings remain bounded diagnostics.
Diagnostic truncation preserves UTF-8 boundaries. Native boundary regressions
include malformed imports alongside valid geometry and long Unicode echo text.
