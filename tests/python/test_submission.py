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
from export_ai_transcript import exportTranscript


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

    def runExport(self, includeDatasheet, transcriptManifest=None):
        suffix = '_ai' if transcriptManifest else ''
        source = self.root / (('source_with_pdf' if includeDatasheet else 'source_without_pdf') + suffix)
        source.mkdir(exist_ok=True)
        work = source / 'build/member_b'
        work.mkdir(parents=True, exist_ok=True)
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
        output = self.root / (('with_pdf' if includeDatasheet else 'without_pdf') + suffix + '.zip')
        arguments = ['export_submission.py', '--out', str(output)]
        if includeDatasheet:
            arguments += ['--datasheet', str(self.pdf)]
        if transcriptManifest:
            arguments += ['--ai-transcript-manifest', str(transcriptManifest)]
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

    def makeTranscript(self):
        """Use the real exporter on a clearly synthetic, single-session source."""
        session = '00000000-0000-4000-8000-000000000001'
        workspace = self.root / 'source_without_pdf_ai'
        source = self.root / f'rollout-2026-11-03T01-00-00-{session}.jsonl'
        rows = [
            {'type': 'session_meta', 'timestamp': '2026-11-03T01:00:00Z',
             'payload': {'id': session, 'cwd': str(workspace), 'timestamp': '2026-11-03T01:00:00Z'}},
            {'type': 'event_msg', 'timestamp': '2026-11-03T01:00:01Z',
             'payload': {'type': 'user_message', 'message': 'SYNTHETIC visible transcript test, not real hardware evidence.'}},
            {'type': 'response_item', 'timestamp': '2026-11-03T01:00:02Z',
             'payload': {'type': 'reasoning', 'content': 'PRIVATE_SYNTHETIC_REASONING_MUST_NOT_EXPORT'}},
        ]
        source.write_text(''.join(json.dumps(row) + '\n' for row in rows), encoding='utf8')
        output = workspace / 'build/member_b/transcript'
        exportTranscript(source, session, output, workspace)
        (output / 'extra_private.txt').write_text('Do not collect unlisted files', encoding='utf8')
        return output / 'ai_transcript_manifest.json', workspace

    def testExplicitTranscriptIncludesExactlyThreeReviewedCourseFiles(self):
        path, workspace = self.makeTranscript()
        with zipfile.ZipFile(self.runExport(False, path)) as archive:
            courseFiles = {name for name in archive.namelist() if name.startswith('course/')}
            self.assertEqual(courseFiles, {'course/ai_transcript.txt', 'course/ai_transcript.json',
                                          'course/ai_transcript_manifest.json'})
            for name in courseFiles:
                self.assertEqual(archive.read(name), (path.parent / Path(name).name).read_bytes())
            record = json.loads(archive.read('verified/manifest.json'))
            self.assertEqual(record['aiTranscript']['status'], 'PASS')
            self.assertEqual(record['aiTranscript']['sessionId'], '00000000-0000-4000-8000-000000000001')
            self.assertFalse(any(name.endswith('.jsonl') or 'extra_private' in name for name in archive.namelist()))
            for name in courseFiles:
                self.assertEqual(record['files'][name], hashlib.sha256(archive.read(name)).hexdigest())

    def testNoTranscriptOptionNeverCollectsExistingTranscriptOrRawLog(self):
        folder = self.root / 'source_without_pdf/assets'
        folder.mkdir(parents=True)
        for name in ('ai_transcript.txt', 'ai_transcript.json', 'ai_transcript_manifest.json',
                     'rollout-private-session.jsonl'):
            (folder / name).write_text('PRIVATE_EXISTING_CONVERSATION', encoding='utf8')
        with zipfile.ZipFile(self.runExport(False)) as archive:
            self.assertFalse(any('ai_transcript' in name or name.endswith('.jsonl') or name.startswith('course/')
                                 for name in archive.namelist()))
            self.assertNotIn('aiTranscript', json.loads(archive.read('verified/manifest.json')))

    def testTranscriptTamperOrMissingDataFileFails(self):
        path, workspace = self.makeTranscript()
        data = path.parent / 'ai_transcript.txt'
        original = data.read_bytes()
        data.write_bytes(original + b'corruption')
        with self.assertRaisesRegex(ValueError, 'changed or does not match'):
            export_submission.aiTranscriptBinding(path, workspace)
        data.unlink()
        with self.assertRaises(FileNotFoundError):export_submission.aiTranscriptBinding(path, workspace)

    def testMissingTranscriptManifestIsNotReconstructed(self):
        path, workspace = self.makeTranscript()
        path.unlink()
        with self.assertRaises(FileNotFoundError):export_submission.aiTranscriptBinding(path, workspace)

    def testRehashedInternalMessageStillFailsVisibleMessageWhitelist(self):
        path, workspace = self.makeTranscript()
        binding = json.loads(path.read_text(encoding='utf8'))
        dataPath = path.parent / 'ai_transcript.json'
        transcript = json.loads(dataPath.read_text(encoding='utf8'))
        transcript['messages'][0]['role'] = 'assistant'
        transcript['messages'][0]['phase'] = 'analysis'
        binding['messageCounts'] = {'assistant': 1}
        transcript['metadata'] = {key: value for key, value in binding.items() if key != 'files'}
        payload = (json.dumps(transcript) + '\n').encode('utf8')
        dataPath.write_bytes(payload)
        binding['files']['ai_transcript.json'] = {'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()}
        path.write_text(json.dumps(binding), encoding='utf8')
        with self.assertRaisesRegex(ValueError, 'non-visible message phase'):
            export_submission.aiTranscriptBinding(path, workspace)

    def testMissingExtraAndTraversalFileListsAreRejected(self):
        path, workspace = self.makeTranscript()
        original = json.loads(path.read_text(encoding='utf8'))
        for files in ({}, {'ai_transcript.txt': original['files']['ai_transcript.txt']},
                      {**original['files'], 'extra_private.txt': original['files']['ai_transcript.txt']},
                      {'../ai_transcript.txt': original['files']['ai_transcript.txt'],
                       'ai_transcript.json': original['files']['ai_transcript.json']},
                      {'..\\ai_transcript.txt': original['files']['ai_transcript.txt'],
                       'ai_transcript.json': original['files']['ai_transcript.json']},
                      {'C:/private.txt': original['files']['ai_transcript.txt'],
                       'ai_transcript.json': original['files']['ai_transcript.json']},
                      {'/private.txt': original['files']['ai_transcript.txt'],
                       'ai_transcript.json': original['files']['ai_transcript.json']}):
            with self.subTest(files=list(files)):
                path.write_text(json.dumps({**original, 'files': files}), encoding='utf8')
                with self.assertRaisesRegex(ValueError, 'exactly the two fixed'):
                    export_submission.aiTranscriptBinding(path, workspace)
        path.write_text(json.dumps({key: value for key, value in original.items() if key != 'files'}), encoding='utf8')
        with self.assertRaisesRegex(ValueError, 'exactly the two fixed'):
            export_submission.aiTranscriptBinding(path, workspace)

    def testTranscriptSchemaStatusSessionWorkspaceAndMetadataMustAgree(self):
        path, workspace = self.makeTranscript()
        original = json.loads(path.read_text(encoding='utf8'))
        changes = [('schema', 'unknown'), ('status', 'FAIL'), ('sessionId', 'not-a-session'),
                   ('sourceFileName', 'rollout-another-session.jsonl'),
                   ('workspace', str(workspace / 'other')), ('sourceSnapshotSha256', 'bad'),
                   ('sourceSnapshotBytes', 0), ('messageCounts', {'user': 99}),
                   ('selectionPolicy', {'responseItemFallback': True})]
        for field, value in changes:
            with self.subTest(field=field):
                path.write_text(json.dumps({**original, field: value}), encoding='utf8')
                with self.assertRaises(ValueError):export_submission.aiTranscriptBinding(path, workspace)
        path.write_text(json.dumps({key: value for key, value in original.items() if key != 'status'}), encoding='utf8')
        with self.assertRaisesRegex(ValueError, 'schema/status'):
            export_submission.aiTranscriptBinding(path, workspace)

    def testValidatedBytesCannotBeSwappedBeforeZipWrite(self):
        path, workspace = self.makeTranscript()
        expected = (path.parent / 'ai_transcript.txt').read_bytes()
        originalBinding = export_submission.aiTranscriptBinding
        def replaceAfterRead(manifest, root):
            result = originalBinding(manifest, root)
            (manifest.parent / 'ai_transcript.txt').write_bytes(b'UNVALIDATED_REPLACEMENT')
            return result
        with patch.object(export_submission, 'aiTranscriptBinding', side_effect=replaceAfterRead):
            archivePath = self.runExport(False, path)
        with zipfile.ZipFile(archivePath) as archive:
            self.assertEqual(archive.read('course/ai_transcript.txt'), expected)
            self.assertNotIn(b'UNVALIDATED_REPLACEMENT', archive.read('course/ai_transcript.txt'))


if __name__ == '__main__':
    unittest.main()
