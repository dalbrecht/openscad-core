// SPDX-License-Identifier: GPL-2.0-or-later
// One request per process deliberately isolates upstream parser globals and caches.
#include <filesystem>
#include <fstream>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include "openscad.h"
#include "core/Builtins.h"
#include "core/BuiltinContext.h"
#include "core/Context.h"
#include "core/EvaluationSession.h"
#include "core/RenderVariables.h"
#include "core/SourceFile.h"
#include "core/Tree.h"
#include "core/CSGTreeEvaluator.h"
#include "core/parsersettings.h"
#include "geometry/GeometryEvaluator.h"
#include "geometry/PolySet.h"
#include "geometry/PolySetUtils.h"
#include "platform/PlatformUtils.h"
#include "ext/json/json.hpp"
#include "utils/printutils.h"
using nlohmann::json;
namespace {
constexpr size_t maxSource = 4 * 1024 * 1024;
constexpr size_t maxTriangles = 100000;
json leaves = json::array(), nodes = json::array();
size_t triangleCount = 0;
int encode(const std::shared_ptr<CSGNode>& node)
{
  if (!node || node->isEmptySet()) return -1;
  if (nodes.size() >= 127) throw std::runtime_error("Preview exceeds 127 CSG nodes");
  if (const auto leaf = std::dynamic_pointer_cast<CSGLeaf>(node)) {
    if (leaves.size() >= 64) throw std::runtime_error("Preview exceeds 64 leaves");
    if (leaf->polyset->getDimension() != 3) throw std::runtime_error("2D preview is not yet supported");
    auto mesh = PolySetUtils::tessellate_faces(*leaf->polyset);
    json triangles = json::array();
    for (const auto& face : mesh->indices) {
      if (face.size() != 3) throw std::runtime_error("Non-triangular tessellation");
      if (++triangleCount > maxTriangles) throw std::runtime_error("Preview triangle quota exceeded");
      json triangle = json::array();
      for (auto index : face) {
        const Vector3d point = leaf->matrix * mesh->vertices.at(index);
        for (int axis = 0; axis < 3; ++axis) {
          if (!std::isfinite(point[axis]) || std::abs(point[axis]) > 1e12)
            throw std::runtime_error("Non-finite or out-of-range preview coordinate");
          triangle.push_back(point[axis]);
        }
      }
      triangles.push_back(std::move(triangle));
    }
    json color = json::array();
    for (int i = 0; i < 4; ++i)
      color.push_back(leaf->color.toVector4f()[i] < 0 ? (i == 3 ? 1.0 : (i == 2 ? 0.15 : 0.95))
                                                      : leaf->color.toVector4f()[i]);
    const int index = leaves.size();
    leaves.push_back({{"triangles", std::move(triangles)}, {"color", color}});
    nodes.push_back({{"op", 0}, {"left", index}, {"right", -1}});
  } else if (const auto operation = std::dynamic_pointer_cast<CSGOperation>(node)) {
    const int left = encode(operation->left()), right = encode(operation->right());
    int op = 1;
    if (operation->getType() == OpenSCADOperator::INTERSECTION) op = 2;
    else if (operation->getType() == OpenSCADOperator::DIFFERENCE) op = 3;
    nodes.push_back({{"op", op}, {"left", left}, {"right", right}});
  } else throw std::runtime_error("Unsupported CSG node");
  if (nodes.size() > 127) throw std::runtime_error("Preview exceeds 127 CSG nodes");
  return nodes.size() - 1;
}
}  // namespace
int main(int argc, char **argv)
{
  try {
    if (argc != 2 && argc != 3) throw std::runtime_error("Usage: openscad-preview-worker source.scad");
    const auto path = std::filesystem::absolute(argc == 3 ? argv[2] : argv[1]);
    const auto snapshot = std::filesystem::absolute(argv[1]);
    if (std::filesystem::file_size(snapshot) > maxSource)
      throw std::runtime_error("Source exceeds 4 MiB");
    std::ifstream input(snapshot);
    if (!input) throw std::runtime_error("Cannot open source");
    std::string text(maxSource + 1, '\0');
    input.read(text.data(), static_cast<std::streamsize>(text.size()));
    text.resize(static_cast<size_t>(input.gcount()));
    if (text.size() > maxSource) throw std::runtime_error("Source exceeds 4 MiB");
    if (text.find('\0') != std::string::npos) throw std::runtime_error("NUL byte in source");
    std::vector<std::string> diagnostics;
    set_output_handler(
      [](const Message& message, void *context) {
        std::cerr << message.msg << '\n';
        auto& messages = *static_cast<std::vector<std::string> *>(context);
        if (messages.size() < 128) messages.push_back(message.msg.substr(0, 8192));
      },
      nullptr, &diagnostics);
    PlatformUtils::registerApplicationPath(std::filesystem::absolute(argv[0]).parent_path().string());
    Builtins::initialize();
    parser_init();
    SourceFile *parsed = nullptr;
    const bool valid = parse(parsed, text, path.string(), path.string(), false);
    std::unique_ptr<SourceFile> source(parsed);
    if (!valid || !source) throw std::runtime_error("OpenSCAD parse failed");
    source->handleDependencies();
    EvaluationSession session{path.parent_path().string()};
    ContextHandle<BuiltinContext> context{Context::create<BuiltinContext>(&session)};
    RenderVariables variables{};
    variables.preview = true;
    variables.applyToContext(context);
    std::shared_ptr<const FileContext> fileContext;
    auto absoluteRoot = source->instantiate(*context, &fileContext);
    const Location *nextLocation = nullptr;
    auto root = find_root_tag(absoluteRoot, &nextLocation);
    if (!root) root = absoluteRoot;
    Tree tree(root, path.parent_path().string());
    GeometryEvaluator geometry(tree);
    CSGTreeEvaluator evaluator(tree, &geometry);
    const auto csg = evaluator.buildCSGTree(*root);
    const int rootIndex = encode(csg);
    json highlights = json::array(), backgrounds = json::array();
    for (const auto& node : evaluator.getHighlightNodes()) highlights.push_back(encode(node));
    for (const auto& node : evaluator.getBackgroundNodes()) backgrounds.push_back(encode(node));
    std::cout << json{{"version", 1},
                      {"leaves", leaves},
                      {"nodes", nodes},
                      {"root", rootIndex},
                      {"highlights", highlights},
                      {"backgrounds", backgrounds},
                      {"diagnostics", diagnostics}}
                   .dump()
              << '\n';
    return 0;
  } catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
  } catch (...) {
    std::cerr << "Unknown native evaluation failure\n";
    return 2;
  }
}
