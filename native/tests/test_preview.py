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
if __name__ == '__main__': unittest.main()
