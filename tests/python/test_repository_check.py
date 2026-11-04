"""Real Git/CLI structural checks on synthetic trees, never FPGA validation."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import check_repository


def gitFingerprint(root):
    return {path.relative_to(root).as_posix():hashlib.sha256(path.read_bytes()).hexdigest()
            for path in root.rglob('*') if path.is_file()}


class RepositoryCheckTests(unittest.TestCase):
    def setUp(self):
        self.scratch=tempfile.TemporaryDirectory(prefix='repository_check_')
        self.addCleanup(self.scratch.cleanup)
        self.directory=Path(self.scratch.name)

    def project(self, root):
        """Minimal structural fixture; placeholder PDFs are not rendered data."""
        root.mkdir(parents=True)
        for name in ('README.md','VERSION_README.md','OWNERS.md','quartus/PartBDebug.qpf',
                     'docs/Major_Project_Brief_2026.pdf','assets/markers/marker_spec.json',
                     'assets/markers/scene_manifest.json','assets/markers/ECHO7_All_Markers_A4_v2.pdf'):
            path=root/name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text('synthetic structural fixture\n',encoding='utf-8')
        pins=('AB12','AC12','AF9','AF10','AD11','AD12','AE11','AC9','AD10','AE12')
        assignments=['set_global_assignment -name TOP_LEVEL_ENTITY echo7IntegratedTop',
                     'set_global_assignment -name DEVICE 5CSEMA5F31C6']
        for index,pin in enumerate(pins):
            assignments += [f'set_location_assignment PIN_{pin} -to SW[{index}]',
                            f'set_instance_assignment -name IO_STANDARD "3.3-V LVTTL" -to SW[{index}]']
        (root/'quartus/PartBDebug.qsf').write_text('\n'.join(assignments)+'\n',encoding='utf-8')
        for name,value in (('tests/rtl/manifest.json',{'tests':[]}),
                           ('tests/fixtures/camera/manifest.json',{'files':[]})):
            path=root/name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(json.dumps(value),encoding='utf-8')
        (root/'tools').mkdir()
        shutil.copyfile(ROOT/'tools/check_repository.py',root/'tools/check_repository.py')
        shutil.copyfile(ROOT/'.gitignore',root/'.gitignore')
        return root

    def runCheck(self, root, environment=None):
        process=subprocess.run([sys.executable,str(root/'tools/check_repository.py')],cwd=root,
            env=environment,capture_output=True,text=True,timeout=30)
        return process,json.loads(process.stdout)

    def initialiseGit(self, root):
        result=subprocess.run(['git','init','--quiet',str(root)],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)

    def testExistingGitMetadataIsNeverChanged(self):
        root=self.project(self.directory/'tracked')
        self.initialiseGit(root)
        # Local metadata exclusions are deliberately not repository .gitignore.
        (root/'.git/info/exclude').write_text('*.png\n',encoding='utf-8')
        before=gitFingerprint(root/'.git')
        process,result=self.runCheck(root)
        self.assertEqual(process.returncode,0,result)
        self.assertEqual(result['status'],'PASS')
        self.assertEqual(gitFingerprint(root/'.git'),before)

    def testZipStyleTreeWithoutGitStillChecksIgnoreRules(self):
        root=self.project(self.directory/'zip tree')
        self.assertFalse((root/'.git').exists())
        process,result=self.runCheck(root)
        self.assertEqual(process.returncode,0,result)
        self.assertFalse((root/'.git').exists())

    def testExportUnderIgnoredParentBuildUsesItsOwnRules(self):
        parent=self.directory/'parent'
        parent.mkdir()
        self.initialiseGit(parent)
        (parent/'.gitignore').write_text('/build/\n',encoding='utf-8')
        root=self.project(parent/'build/package')
        inherited=subprocess.run(['git','check-ignore','--no-index','--quiet',
                                  'build/package/assets/markers/ECHO7_All_Markers_A4_v2.pdf'],
                                 cwd=parent,capture_output=True,text=True,timeout=10)
        self.assertEqual(inherited.returncode,0,'fixture must actually be ignored by its parent')
        before=gitFingerprint(parent/'.git')
        process,result=self.runCheck(root)
        self.assertEqual(process.returncode,0,result)
        self.assertFalse((root/'.git').exists())
        self.assertEqual(gitFingerprint(parent/'.git'),before)

    def testIncorrectIgnoreRulesRemainNonzero(self):
        root=self.project(self.directory/'wrong rules')
        (root/'.gitignore').write_text('*.png\n',encoding='utf-8')
        process,result=self.runCheck(root)
        self.assertEqual(process.returncode,1)
        self.assertEqual(result['status'],'FAIL')
        self.assertTrue(any('build/example.log' in error for error in result['errors']))
        self.assertTrue(any('frame30158/frame.png' in error for error in result['errors']))

    def testMissingGitExecutableIsFailureNotUnignored(self):
        root=self.project(self.directory/'missing git')
        environment={key:value for key,value in os.environ.items() if key.upper()!='PATH'}
        environment['PATH']=str(self.directory/'empty path')
        process,result=self.runCheck(root,environment)
        self.assertEqual(process.returncode,1)
        self.assertTrue(any('Git ignore validation unavailable' in error for error in result['errors']))

    def testFatalGitExitCannotMasqueradeAsNotIgnored(self):
        root=self.project(self.directory/'fatal git')
        success=subprocess.CompletedProcess(['git'],0,'','')
        failure=subprocess.CompletedProcess(['git'],128,'','synthetic fatal Git result')
        with patch.object(check_repository.subprocess,'run',side_effect=[success,failure]):
            errors=check_repository.checkIgnoreRules(root,[('kept.png',False)])
        self.assertEqual(len(errors),1)
        self.assertIn('exit 128',errors[0])


if __name__=='__main__':
    unittest.main()
