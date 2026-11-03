#!/usr/bin/env python3
"""Export one verified session's visible messages, never its internal trace.

Only completed UI UserMessage/AgentMessage events (and their older event_msg
forms) are eligible. response_item is deliberately not a fallback: it contains
runtime-injected user-role context as well as private/internal messages.
The input is read-only; output is restricted to this workspace's ignored build/.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
VISIBLE_PHASES={'commentary','final_answer','final'}
MAX_SOURCE_BYTES=512*1024*1024
SECRET_PATTERNS=(
    ('private_key',re.compile(r'-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----')),
    ('provider_key',re.compile(r'\b(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|xox[baprs]-[A-Za-z0-9-]{10,})')),
    ('aws_access_key',re.compile(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b')),
    ('bearer_or_basic',re.compile(r'\b(?:Bearer|Basic)\s+[A-Za-z0-9+/=_\-.]{12,}',re.I)),
    ('jwt',re.compile(r'\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b')),
    ('uri_userinfo',re.compile(r'\b[a-z][a-z0-9+.-]*://[^\s/@:]+:[^\s/@]+@',re.I)),
)
SECRET_ASSIGNMENT=re.compile(
    r'''\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|password|passwd|secret|token|aws[_-]?secret[_-]?access[_-]?key|secretAccessKey)\b["']?\s*[:=,]\s*["']?([^\s"',;]{6,})''',re.I)


class ExportError(ValueError):
    """Errors contain only safe metadata, never source message contents."""


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def credentialReasons(text):
    """Conservative known-format screen; omit a whole message, never rewrite it.

    This is a bounded detector, not proof that arbitrary natural language cannot
    contain a secret. All tool/internal records are excluded independently.
    """
    reasons={name for name,pattern in SECRET_PATTERNS if pattern.search(text)}
    for match in SECRET_ASSIGNMENT.finditer(text):
        value=match.group(1)
        if (value.upper() in {'REDACTED','EXAMPLE','PLACEHOLDER','CHANGEME','NONE','NULL'} or
            value.startswith(('<','${','$env:','os.environ','YOUR_','your_')) or set(value)<={'*','x','X'}):
            continue
        reasons.add('credential_assignment')
    return sorted(reasons)


def parseRecord(line,lineNumber):
    try:
        record=json.loads(line)
    except (ValueError,UnicodeError):
        raise ExportError(f'Invalid UTF-8/JSON record at source line {lineNumber}') from None
    if not isinstance(record,dict) or not isinstance(record.get('payload'),dict):
        raise ExportError(f'Invalid record shape at source line {lineNumber}')
    return record


def validateMetadata(record,expectedSessionId,workspaceRoot):
    if record.get('type')!='session_meta':
        raise ExportError('The first record must identify this session; no history search is permitted')
    payload=record['payload']
    if payload.get('id')!=expectedSessionId:
        raise ExportError('Session ID mismatch; nothing exported')
    cwd=payload.get('cwd')
    if not isinstance(cwd,str) or os.path.normcase(str(Path(cwd).resolve()))!=os.path.normcase(str(workspaceRoot.resolve())):
        raise ExportError('Session working directory does not match this workspace; nothing exported')
    return {'sessionId':expectedSessionId,'workspace':str(workspaceRoot.resolve()),
            'sessionStartedAt':payload.get('timestamp')}


def visibleMessage(record,lineNumber,sessionId,omissions):
    """Return only whitelisted user-visible fields; never pass raw payloads on."""
    payload=record['payload']
    if record.get('type')!='event_msg':return None
    eventType=payload.get('type')
    if eventType=='item_completed':
        if payload.get('thread_id')!=sessionId:
            omissions['other_or_missing_thread_id']+=1
            return None
        item=payload.get('item')
        if not isinstance(item,dict) or item.get('type') not in ('UserMessage','AgentMessage'):return None
        user=item['type']=='UserMessage';phase=item.get('phase')
        if (not user and phase not in VISIBLE_PHASES) or (user and phase not in (None,'user')):
            omissions['non_visible_message_phase']+=1
            return None
        blocks=[]
        if not isinstance(item.get('content'),list):
            omissions['unsupported_message_shape']+=1
            return None
        for block in item['content']:
            if isinstance(block,dict) and block.get('type') in ('text','Text') and isinstance(block.get('text'),str):
                blocks.append(block['text'])
            else:omissions['non_text_content_block']+=1
        # Async UI question titles/options are visible strings, not tool calls.
        # Keep their original strings separate rather than synthesising dialogue.
        questions=[]
        for question in item.get('questions') or []:
            if (isinstance(question,dict) and isinstance(question.get('title'),str) and
                (question.get('options') is None or isinstance(question.get('options'),list)) and
                all(isinstance(option,str) for option in question.get('options') or [])):
                questions.append({'title':question['title'],'options':question.get('options')})
            else:omissions['unsupported_question_shape']+=1
        message={'sourceLine':lineNumber,'timestamp':record.get('timestamp'),
                 'role':'user' if user else 'assistant','phase':'user' if user else phase,
                 'textBlocks':blocks,'visibleQuestions':questions,'sourceFormat':'completed_ui_item'}
        key=(payload.get('turn_id'),item.get('id')) if item.get('id') else None
    elif eventType in ('user_message','agent_message'):
        if payload.get('thread_id',sessionId)!=sessionId:
            omissions['other_or_missing_thread_id']+=1
            return None
        user=eventType=='user_message';phase=payload.get('phase',payload.get('channel'))
        if phase is not None and phase not in VISIBLE_PHASES|{'user'}:
            omissions['non_visible_message_phase']+=1
            return None
        if not isinstance(payload.get('message'),str):
            omissions['unsupported_message_shape']+=1
            return None
        message={'sourceLine':lineNumber,'timestamp':record.get('timestamp'),
                 'role':'user' if user else 'assistant','phase':'user' if user else phase or 'visible_agent_message',
                 'textBlocks':[payload['message']],'visibleQuestions':[],'sourceFormat':'legacy_visible_event'}
        key=None
    else:return None
    if not message['textBlocks'] and not message['visibleQuestions']:
        omissions['no_exportable_visible_text']+=1
        return None
    scanText='\n'.join(message['textBlocks'])+'\n'+json.dumps(message['visibleQuestions'],ensure_ascii=False)
    secretReasons=credentialReasons(scanText)
    if secretReasons:
        omissions['credential_screen_message']+=1
        for reason in secretReasons:omissions['credential_screen_'+reason]+=1
        return None
    return key,message


def exportTranscript(sessionLog,expectedSessionId,out,workspaceRoot=ROOT):
    sessionLog=Path(sessionLog).resolve();workspaceRoot=Path(workspaceRoot).resolve();out=Path(out).resolve()
    if not out.is_relative_to(workspaceRoot/'build'):
        raise ExportError('Output must be inside this workspace build/ directory')
    if not expectedSessionId or len(expectedSessionId)>80:
        raise ExportError('An explicit expected session ID is required')
    # Read one explicitly selected file only. Validate metadata before reading
    # its remaining contents. Never enumerate the account/session directory.
    with sessionLog.open('rb') as source:
        firstLine=source.readline(1024*1024)
        metadata=validateMetadata(parseRecord(firstLine,1),expectedSessionId,workspaceRoot)
        snapshotBytes=source.seek(0,2)
        if snapshotBytes>MAX_SOURCE_BYTES:raise ExportError('Session exceeds the bounded 512 MiB snapshot limit')
        source.seek(0)
        snapshot=source.read(snapshotBytes)
    if len(snapshot)!=snapshotBytes:raise ExportError('Source was truncated while taking the read-only snapshot')
    sourceCounts=Counter();omissions=Counter();messages=[];seen={};sourceTimes=[]
    lines=snapshot.splitlines()
    for lineNumber,line in enumerate(lines,1):
        record=parseRecord(line,lineNumber);payload=record['payload']
        recordType=record.get('type','unknown');subtype=payload.get('type')
        if recordType=='session_meta':validateMetadata(record,expectedSessionId,workspaceRoot)
        if isinstance(record.get('timestamp'),str):sourceTimes.append(record['timestamp'])
        label=recordType+(f'.{subtype}' if isinstance(subtype,str) else '')
        if recordType=='event_msg' and subtype=='item_completed' and isinstance(payload.get('item'),dict):
            label+='.'+str(payload['item'].get('type','unknown'))
        sourceCounts[label]+=1
        visible=visibleMessage(record,lineNumber,expectedSessionId,omissions)
        if visible is None:continue
        key,message=visible
        signature=(message['role'],message['phase'],message['textBlocks'],message['visibleQuestions'])
        if key is not None and key in seen:
            if seen[key]!=signature:raise ExportError(f'Conflicting completed UI item at source line {lineNumber}')
            omissions['duplicate_completed_ui_item']+=1
            continue
        if key is not None:seen[key]=signature
        messages.append(message)
    if not messages:raise ExportError('No whitelisted visible messages were found; no transcript exported')
    metadata.update(schema='member-b-visible-ai-transcript-v1',status='PASS',exportedAtUtc=datetime.now(timezone.utc).isoformat(),
        sourceFileName=sessionLog.name,sourceSnapshotSha256=sha256(snapshot),sourceSnapshotBytes=len(snapshot),
        sourceBytesAtCompletion=sessionLog.stat().st_size,sourceHashScope='Exactly the bytes read at export start; later appended records are outside this snapshot',
        sourceLineCount=len(lines),sourceTimeRange=[sourceTimes[0],sourceTimes[-1]] if sourceTimes else None,
        visibleTimeRange=[messages[0]['timestamp'],messages[-1]['timestamp']],
        messageCounts=dict(Counter(message['role'] for message in messages)),sourceRecordCounts=dict(sorted(sourceCounts.items())),
        omissionCounts=dict(sorted(omissions.items())),
        selectionPolicy={'allowed':'event_msg user_message/agent_message; event_msg.item_completed UserMessage/AgentMessage in this exact thread',
                         'assistantPhases':sorted(VISIBLE_PHASES),'responseItemFallback':False,
                         'credentialPolicy':'Omit entire visible messages matching known credential formats; detector is bounded, not a proof for arbitrary natural-language secrets'},
        exclusions=['analysis/reasoning including summaries','system/developer/base instructions','response_item records of every role',
                    'tool calls, tool results and command output','sub-agent communications','compaction summaries',
                    'images, attachments and non-text content','account/user identifiers and other raw session metadata',
                    'visible messages matching the credential screen'],
        scope='Only visible messages physically present in this one selected session snapshot. Earlier sessions, account-wide history and omitted compaction context are not reconstructed. This is not the complete project history.')
    transcript={'metadata':metadata,'messages':messages}
    text=['Member B — visible AI conversation transcript',
          f"Session: {expectedSessionId}",f"Source snapshot SHA256: {metadata['sourceSnapshotSha256']}",
          f"Visible coverage: {metadata['visibleTimeRange'][0]} to {metadata['visibleTimeRange'][1]}",metadata['scope'],
          'Original visible text follows verbatim. Headings and optional UI question metadata are exporter annotations.','']
    for message in messages:
        text.append(f"[{message['timestamp']}] {message['role']} ({message['phase']}; source line {message['sourceLine']})")
        text.extend(message['textBlocks'])
        if message['visibleQuestions']:
            text.extend(('[Visible question metadata — original strings]',json.dumps(message['visibleQuestions'],ensure_ascii=False,indent=2)))
        text.append('')
    outputBytes={'ai_transcript.txt':('\n'.join(text)+'\n').encode('utf8'),
                 'ai_transcript.json':(json.dumps(transcript,ensure_ascii=False,indent=2)+'\n').encode('utf8')}
    manifest={**metadata,'files':{name:{'sha256':sha256(data),'bytes':len(data)} for name,data in outputBytes.items()}}
    outputBytes['ai_transcript_manifest.json']=(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode('utf8')
    if any(out/name==sessionLog for name in outputBytes):raise ExportError('Output cannot replace the source log')
    out.mkdir(parents=True,exist_ok=True)
    if any((out/name).is_symlink() for name in outputBytes):
        raise ExportError('Refusing an output file that is a symbolic link')
    for name,data in outputBytes.items():
        # Replace a new inode rather than writing through a pre-existing hard
        # link. The source log must remain read-only even with hostile outputs.
        with tempfile.NamedTemporaryFile(dir=out,prefix='.ai_transcript_',delete=False) as temporary:
            temporary.write(data);temporaryPath=Path(temporary.name)
        try:os.replace(temporaryPath,out/name)
        finally:
            if temporaryPath.exists():temporaryPath.unlink()
    return manifest


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session-log',required=True,type=Path)
    parser.add_argument('--expected-session-id',required=True)
    parser.add_argument('--out',required=True,type=Path,help='Output directory under this workspace build/')
    args=parser.parse_args(argv)
    try:manifest=exportTranscript(args.session_log,args.expected_session_id,args.out)
    except (ExportError,OSError) as error:
        print(json.dumps({'status':'FAIL','error':str(error)},ensure_ascii=False));return 1
    print(json.dumps({'status':'PASS','out':str(args.out.resolve()),'messageCounts':manifest['messageCounts'],
                      'visibleTimeRange':manifest['visibleTimeRange'],'sourceSnapshotSha256':manifest['sourceSnapshotSha256'],
                      'omissionCounts':manifest['omissionCounts']},ensure_ascii=False))
    return 0


if __name__=='__main__':raise SystemExit(main())
