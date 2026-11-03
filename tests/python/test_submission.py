"""Archive/hash binding tests with synthetic files, never PDF layout or FPGA proof."""
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import export_submission


class SubmissionDatasheetTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.pdf = self.root / 'current.pdf'
        self.pdf.write_bytes(b'%PDF-1.4\n% SYNTHETIC BINDING TEST ONLY\n')
        self.current = {'sha256': 'a' * 64, 'buildId': 0xaaaaaaaa}
        self.record = {'schema': 'member-b-datasheet-generation-v1', 'status': 'PASS', 'pages': 1,
                       'sha256': hashlib.sha256(self.pdf.read_bytes()).hexdigest(),
                       'indexSha256': 'b' * 64, 'sourceSha256': self.current['sha256'],
                       'buildId': self.current['buildId']}
        self.writeRecord()

    def writeRecord(self):
        self.pdf.with_suffix('.pdf.json').write_text(json.dumps(self.record), encoding='utf-8')

    def testCurrentExplicitPdfRetainsSourceAndIndexHashes(self):
        result = export_submission.datasheetBinding(self.pdf, self.current)
        self.assertEqual(result['sourceSha256'], self.current['sha256'])
        self.assertEqual(result['indexSha256'], 'b' * 64)
        self.assertEqual(result['sha256'], self.record['sha256'])

    def testChangedPdfIsRejected(self):
        self.pdf.write_bytes(self.pdf.read_bytes() + b'changed')
        with self.assertRaisesRegex(ValueError, 'does not match'):
            export_submission.datasheetBinding(self.pdf, self.current)

    def testMissingSidecarCannotBeAssumedCurrent(self):
        self.pdf.with_suffix('.pdf.json').unlink()
        with self.assertRaises(FileNotFoundError):
            export_submission.datasheetBinding(self.pdf, self.current)

    def testStaleSourceBuildWrongPagesOrIncompleteRecordIsRejected(self):
        original = dict(self.record)
        for name, value in (('sourceSha256', 'c' * 64), ('buildId', 3), ('pages', 2),
                            ('schema', 'unknown'), ('status', 'FAIL'), ('indexSha256', '')):
            with self.subTest(field=name):
                self.record = {**original, name: value}
                self.writeRecord()
                with self.assertRaisesRegex(ValueError, 'does not match'):
                    export_submission.datasheetBinding(self.pdf, self.current)

    def runExport(self, includeDatasheet):
        source = self.root / ('source_with_pdf' if includeDatasheet else 'source_without_pdf')
        source.mkdir()
        work = source / 'build/member_b'
        work.mkdir(parents=True)
        sof = work / 'PartBDebug.sof'
        sof.write_bytes(b'synthetic sof; never programmed')
        build = {'status': 'PASS', 'source': self.current,
                 'sof': {'path': str(sof), 'sha256': hashlib.sha256(sof.read_bytes()).hexdigest()}}
        (work / 'last_build.json').write_text(json.dumps(build), encoding='utf-8')
        for name in ('README.md', 'VERSION_README.md', 'OWNERS.md', 'requirements.txt',
                     'run_all_tests.sh', '.gitignore', '.gitattributes', '.editorconfig'):
            (source / name).write_text('synthetic export fixture\n', encoding='utf-8')
        for name in ('evidence/old.log', 'member_b_review_pack/old.txt', 'docs/old.md'):
            path = source / name
            path.parent.mkdir(exist_ok=True)
            path.write_text('must not be archived', encoding='utf-8')
        output = self.root / ('with_pdf.zip' if includeDatasheet else 'without_pdf.zip')
        arguments = ['export_submission.py', '--out', str(output)]
        if includeDatasheet:
            arguments += ['--datasheet', str(self.pdf)]
        with patch.object(export_submission.echo7, 'ROOT', source), \
             patch.object(export_submission.echo7, 'WORK', work), \
             patch.object(export_submission.echo7, 'sourceIdentity', return_value=self.current), \
             patch.object(sys, 'argv', arguments), redirect_stdout(io.StringIO()):
            export_submission.main()
        return output

    def testArchiveContainsExplicitPdfAndBindingButNoOldEvidence(self):
        with zipfile.ZipFile(self.runExport(True)) as archive:
            self.assertEqual(archive.read('member_b_datasheet.pdf'), self.pdf.read_bytes())
            record = json.loads(archive.read('verified/manifest.json'))
            self.assertEqual(record['datasheet']['sourceSha256'], self.current['sha256'])
            self.assertEqual(record['files']['member_b_datasheet.pdf'], self.record['sha256'])
            self.assertFalse(any(name.startswith(('evidence/', 'member_b_review_pack/')) for name in archive.namelist()))
            self.assertNotIn('docs/old.md', archive.namelist())

    def testNoDatasheetArgumentNeverCollectsAnExistingPdf(self):
        with zipfile.ZipFile(self.runExport(False)) as archive:
            self.assertNotIn('member_b_datasheet.pdf', archive.namelist())
            self.assertNotIn('datasheet', json.loads(archive.read('verified/manifest.json')))


if __name__ == '__main__':
    unittest.main()
