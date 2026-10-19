import json, pathlib, subprocess, sys, tempfile, unittest
WORKER = str(pathlib.Path(sys.argv.pop()).resolve())
class PreviewTests(unittest.TestCase):
    def compile(self, source):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / 'input.scad'
            path.write_text(source)
            return subprocess.run([WORKER, str(path)], capture_output=True, text=True)
    def test_difference_retains_two_leaves_and_operation(self):
        result = self.compile('difference(){cube(10);translate([5,5,-1]) cylinder(h=12,r=2,$fn=16);}')
        self.assertEqual(result.returncode, 0, result.stderr)
        scene = json.loads(result.stdout)
        self.assertEqual(len(scene['leaves']), 2)
        self.assertEqual(scene['nodes'][-1]['op'], 3)
        self.assertTrue(all(len(t)==9 for leaf in scene['leaves'] for t in leaf['triangles']))
    def test_preview_variable_is_true(self):
        result = self.compile('if ($preview) cube(1); else sphere(3);')
        self.assertEqual(len(json.loads(result.stdout)['leaves'][0]['triangles']),12)
    def test_syntax_error_is_failure(self):
        self.assertNotEqual(self.compile('cube( ;').returncode, 0)
    def test_empty_is_success(self):
        self.assertEqual(json.loads(self.compile('').stdout)['leaves'], [])
    def test_loop_and_module_use_real_evaluator(self):
        result = self.compile('module a(x){translate([x,0,0]) cube(1);} for(i=[0:2]) a(i);')
        self.assertEqual(len(json.loads(result.stdout)['leaves']), 3)
    def test_success_retains_warning_diagnostics(self):
        result = self.compile('missing_native_module(); cube(1);')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue(any('missing_native_module' in line for line in json.loads(result.stdout)['diagnostics']))
    def test_relative_include_uses_logical_document_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            base = pathlib.Path(directory)
            (base/'module.scad').write_text('module shape(){cube(2);}')
            (base/'input.scad').write_text('include <module.scad> shape();')
            result = subprocess.run([WORKER,str(base/'input.scad')],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(len(json.loads(result.stdout)['leaves']),1)
    def test_nul_source_is_rejected(self):
        self.assertNotEqual(self.compile('cube(1);\0sphere(2);').returncode, 0)
    def test_source_quota(self):
        self.assertNotEqual(self.compile(' '*(4*1024*1024+1)).returncode, 0)
    def test_leaf_quota(self):
        result = self.compile('for(i=[0:64]) translate([i*2,0,0]) cube(1);')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Preview exceeds', result.stderr)
    def test_intersection_retains_operator(self):
        scene = json.loads(self.compile('intersection(){cube(4);sphere(3);}').stdout)
        self.assertEqual(scene['nodes'][-1]['op'], 2)
    def test_modifiers_preserve_layers(self):
        scene = json.loads(self.compile('cube(1); #translate([3,0,0]) cube(1); %sphere(1);').stdout)
        self.assertTrue(scene['highlights'])
        self.assertTrue(scene['backgrounds'])
    def test_owned_output_survives_later_requests(self):
        first = self.compile('cube(1);').stdout
        self.compile('sphere(9);')
        self.assertEqual(len(json.loads(first)['leaves'][0]['triangles']),12)
    def test_concurrent_processes_have_independent_evaluators(self):
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(self.compile, ['cube(1);', 'sphere(2);']*4))
        self.assertTrue(all(result.returncode == 0 for result in results))
    def test_two_dimensional_preview_fails_explicitly(self):
        result = self.compile('square(2);')
        self.assertNotEqual(result.returncode,0)
        self.assertIn('2D preview',result.stderr)
    def test_out_of_range_transformed_coordinate_is_rejected(self):
        result = self.compile('translate([1e15,0,0]) cube(1);')
        self.assertNotEqual(result.returncode,0)
        self.assertIn('out-of-range',result.stderr)
    def test_triangle_quota(self):
        result = self.compile('sphere(10,$fn=500);')
        self.assertNotEqual(result.returncode,0)
        self.assertIn('triangle quota',result.stderr)
    def test_render_node_remains_upstream_evaluated_geometry(self):
        result = self.compile('color("yellow") render() difference(){cube(4,center=true);cylinder(h=8,r=1,center=true,$fn=12);}')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(len(json.loads(result.stdout)['leaves']),1)
    def test_root_and_disable_modifiers_follow_upstream(self):
        result = self.compile('cube(2); !sphere(1,$fn=8); *cube(100);')
        self.assertEqual(result.returncode,0,result.stderr)
        scene = json.loads(result.stdout)
        self.assertEqual(len(scene['leaves']),1)
        values = [value for triangle in scene['leaves'][0]['triangles'] for value in triangle]
        self.assertLessEqual(max(values),1)
    def test_missing_file_and_usage_return_failure(self):
        self.assertNotEqual(subprocess.run([WORKER],capture_output=True).returncode,0)
        self.assertNotEqual(subprocess.run([WORKER,'/missing/native-model.scad'],capture_output=True).returncode,0)
    def test_evaluation_error_never_returns_partial_success(self):
        result = self.compile('cube(1); assert(false); sphere(2);')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '')
    def test_reflection_preserves_outward_winding(self):
        def volume(source):
            scene = json.loads(self.compile(source).stdout)
            total = 0
            for leaf in scene['leaves']:
                for t in leaf['triangles']:
                    a,b,c = t[:3],t[3:6],t[6:]
                    total += sum(a[i]*(b[(i+1)%3]*c[(i+2)%3]-b[(i+2)%3]*c[(i+1)%3]) for i in range(3))/6
            return total
        self.assertGreater(volume('cube(2);') * volume('mirror([1,0,0]) cube(2);'), 0)
    def test_nonfinite_color_is_rejected(self):
        result = self.compile('color([1e100,0,0]) cube(1);')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '')
    def test_deep_union_receives_quota_error_instead_of_stack_failure(self):
        result = self.compile('for(i=[0:9999]) translate([i*2,0,0]) cube(1);')
        self.assertGreater(result.returncode, 0)
        self.assertIn('Preview exceeds', result.stderr)
    def test_geometry_error_never_returns_partial_success(self):
        with tempfile.TemporaryDirectory() as directory:
            mesh = pathlib.Path(directory) / 'bad.stl'
            mesh.write_text('not a valid STL mesh')
            result = self.compile(f'cube(1); import("{mesh}");')
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, '')
    def test_long_unicode_diagnostics_remain_valid_utf8(self):
        for offset in range(3):
            result = self.compile('echo("' + 'a' * (8185 + offset) + '€€€€€"); cube(1);')
            self.assertEqual(result.returncode, 0, result.stderr[-300:])
            scene = json.loads(result.stdout)
            self.assertTrue(all(len(message.encode('utf8')) <= 8192 for message in scene['diagnostics']))
    def test_colored_import_fails_explicitly_without_color_override(self):
        with tempfile.TemporaryDirectory() as directory:
            mesh = pathlib.Path(directory) / 'colored.off'
            mesh.write_text('OFF\n4 4 0\n0 0 0\n1 0 0\n0 1 0\n0 0 1\n3 0 2 1 255 0 0\n3 0 1 3 0 255 0\n3 0 3 2 0 0 255\n3 1 2 3 255 255 0\n')
            result = self.compile(f'import("{mesh}");')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('face colors', result.stderr)
            override = self.compile(f'color("red") import("{mesh}");')
            self.assertEqual(override.returncode, 0, override.stderr)
    def test_highlight_reuses_main_scene_nodes_and_quota(self):
        result = self.compile('#union(){for(i=[0:32]) translate([i*2,0,0]) cube(1);}')
        self.assertEqual(result.returncode, 0, result.stderr)
        scene = json.loads(result.stdout)
        self.assertEqual(len(scene['leaves']),33)
        self.assertEqual(scene['root'],scene['highlights'][0])
    def test_control_z_cannot_hide_nul_suffix(self):
        result = self.compile('cube(1);\x1a\0sphere(2);')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '')
    def test_render_materials_require_explicit_override_until_protocol_v2(self):
        result = self.compile('render() difference(){cube(4,center=true);cylinder(h=8,r=1,center=true,$fn=12);}')
        self.assertNotEqual(result.returncode,0)
        self.assertIn('face colors',result.stderr)
        self.assertEqual(result.stdout,'')
if __name__ == '__main__': unittest.main()
