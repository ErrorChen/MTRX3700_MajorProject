"""Synthetic export-boundary tests. No account/session discovery is performed."""
import hashlib,json,os
from pathlib import Path
import sys,tempfile,unittest

root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'tools'))
from export_ai_transcript import ExportError,exportTranscript

SESSION='synthetic-visible-export-test'
TIME='2026-11-03T04:00:00Z'


def record(kind,payload):return {'type':kind,'timestamp':TIME,'payload':payload}


def ui(kind,text,itemId='one',phase='commentary',threadId=SESSION,**extra):
    item={'type':kind,'id':itemId,'content':[{'type':'text' if kind=='UserMessage' else 'Text','text':text}]}
    if kind=='AgentMessage':item['phase']=phase
    item.update(extra)
    return record('event_msg',{'type':'item_completed','thread_id':threadId,'turn_id':'turn1','item':item})


class TranscriptExportTests(unittest.TestCase):
    def setUp(self):
        parent=root/'build/member_b/ai_transcript_tests';parent.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=parent)
        self.workspace=Path(self.temp.name);self.source=self.workspace/'source.jsonl';self.out=self.workspace/'build/export'
        self.meta=record('session_meta',{'id':SESSION,'cwd':str(self.workspace),'timestamp':TIME,
            'creator_account_id':'ACCOUNT_PRIVATE','base_instructions':'BASE_PRIVATE'})

    def tearDown(self):self.temp.cleanup()

    def write(self,*rows):
        self.source.write_text(''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in (self.meta,*rows)),encoding='utf8')

    def export(self,expected=SESSION):
        return exportTranscript(self.source,expected,self.out,self.workspace)

    def testStrictWhitelistExcludesInternalRolesToolsReasoningAndOtherThreads(self):
        rows=[ui('UserMessage','真实用户文本',itemId='user'),ui('AgentMessage','Visible answer',itemId='assistant')]
        for role in ('system','developer','user','assistant','tool'):
            rows.append(record('response_item',{'type':'message','role':role,'content':f'PRIVATE_RESPONSE_{role}'}))
        for kind in ('Reasoning','SubAgentActivity','CommandExecution','ImageView','ContextCompaction'):
            rows.append(record('event_msg',{'type':'item_completed','thread_id':SESSION,
                        'item':{'type':kind,'content':f'PRIVATE_CONTENT_{kind}'}}))
        rows.extend((ui('AgentMessage','PRIVATE_ANALYSIS',itemId='hidden',phase='analysis'),
                     ui('AgentMessage','PRIVATE_OTHER_THREAD',itemId='other',threadId='another-session'),
                     record('compacted',{'message':'PRIVATE_SUMMARY'})))
        self.write(*rows);manifest=self.export()
        self.assertEqual(manifest['messageCounts'],{'user':1,'assistant':1})
        texts='\n'.join(path.read_text(encoding='utf8') for path in self.out.iterdir())
        for sentinel in ('PRIVATE_RESPONSE','PRIVATE_CONTENT','PRIVATE_ANALYSIS','PRIVATE_OTHER_THREAD',
                         'PRIVATE_SUMMARY','ACCOUNT_PRIVATE','BASE_PRIVATE'):
            self.assertNotIn(sentinel,texts)
        self.assertFalse(manifest['selectionPolicy']['responseItemFallback'])

    def testVerbatimUnicodeNewlinesAndVisibleQuestionStrings(self):
        text='  原样保留\n第二行\t\\literal\\n\n'
        q=[{'title':'实际问题？','options':['选项一','选项二']}]
        message=ui('AgentMessage',text,phase='final_answer',questions=q)
        message['payload']['item']['content'].append({'type':'Image','path':'PRIVATE_ATTACHMENT'})
        self.write(message);manifest=self.export()
        result=json.loads((self.out/'ai_transcript.json').read_text(encoding='utf8'))
        self.assertEqual(result['messages'][0]['textBlocks'],[text])
        self.assertEqual(result['messages'][0]['visibleQuestions'],q)
        self.assertIn(text,(self.out/'ai_transcript.txt').read_text(encoding='utf8'))
        self.assertEqual(manifest['omissionCounts']['non_text_content_block'],1)
        self.assertNotIn('PRIVATE_ATTACHMENT',(self.out/'ai_transcript.json').read_text(encoding='utf8'))

    def testLegacyVisibleEventsAndAnalysisChannelExclusion(self):
        self.write(record('event_msg',{'type':'user_message','message':'User visible'}),
                   record('event_msg',{'type':'agent_message','message':'Assistant visible'}),
                   record('event_msg',{'type':'agent_message','channel':'analysis','message':'PRIVATE_REASONING'}))
        manifest=self.export()
        self.assertEqual(manifest['messageCounts'],{'user':1,'assistant':1})
        self.assertEqual(manifest['omissionCounts']['non_visible_message_phase'],1)

    def testIdentityDirectoryAndMalformedInputsFailBeforeWriting(self):
        self.write(ui('UserMessage','Safe'))
        with self.assertRaisesRegex(ExportError,'Session ID'):self.export('wrong-session')
        self.assertFalse(self.out.exists())
        self.meta['payload']['cwd']=str(self.workspace/'different');self.write(ui('UserMessage','Safe'))
        with self.assertRaisesRegex(ExportError,'working directory'):self.export()
        self.meta['payload']['cwd']=str(self.workspace);self.write(ui('UserMessage','Safe'))
        with self.source.open('a',encoding='utf8') as source:source.write('{broken PRIVATE_RAW')
        with self.assertRaisesRegex(ExportError,'source line 3') as error:self.export()
        self.assertNotIn('PRIVATE_RAW',str(error.exception));self.assertFalse(self.out.exists())

    def testOutputMustStayInsideWorkspaceBuild(self):
        self.write(ui('UserMessage','Safe'))
        with self.assertRaisesRegex(ExportError,'workspace build'):
            exportTranscript(self.source,SESSION,self.workspace/'not-ignored',self.workspace)

    def testCredentialScreenOmitsWholeMessagesWithoutLeakingMatchedValues(self):
        # Deliberately fake values, matching supported credential formats.
        examples=['sk-'+('A'*24),'password = "abcdef123456"','https://user:abcdef123456@example.invalid',
                  '-----BEGIN PRIVATE KEY-----\nFAKE','Bearer '+('B'*20)]
        self.write(ui('UserMessage','Do not expose credentials.',itemId='safe'),
                   *(ui('UserMessage',value,itemId=f'secret{i}') for i,value in enumerate(examples)))
        manifest=self.export()
        self.assertEqual(manifest['messageCounts'],{'user':1})
        self.assertEqual(manifest['omissionCounts']['credential_screen_message'],len(examples))
        outputs='\n'.join(path.read_text(encoding='utf8') for path in self.out.iterdir())
        for value in examples:self.assertNotIn(value,outputs)

    def testCompletedDuplicateDeduplicatesButConflictFails(self):
        message=ui('AgentMessage','Only once')
        self.write(message,message);manifest=self.export()
        self.assertEqual(manifest['messageCounts'],{'assistant':1})
        self.assertEqual(manifest['omissionCounts']['duplicate_completed_ui_item'],1)
        self.write(message,ui('AgentMessage','Conflicting content'))
        with self.assertRaisesRegex(ExportError,'Conflicting completed'):self.export()

    def testHashesAndExistingHardLinkCannotModifySource(self):
        self.write(ui('UserMessage','Unmodified source'))
        original=self.source.read_bytes();self.out.mkdir(parents=True)
        os.link(self.source,self.out/'ai_transcript.txt')
        manifest=self.export()
        self.assertEqual(self.source.read_bytes(),original)
        self.assertEqual(manifest['status'],'PASS')
        self.assertEqual(manifest['sourceSnapshotSha256'],hashlib.sha256(original).hexdigest())
        for name,entry in manifest['files'].items():
            data=(self.out/name).read_bytes()
            self.assertEqual(entry['sha256'],hashlib.sha256(data).hexdigest())
            self.assertEqual(entry['bytes'],len(data))
        self.assertIn('not the complete project history',manifest['scope'])


if __name__=='__main__':unittest.main()
