#!/usr/bin/env python3
"""Plan one fixed visit locally; never performs input or schedules work."""
import argparse,json
from datetime import datetime,timezone,timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


def plan(config,instant,visit_key=None):
    zone=ZoneInfo(config['timezone']);local=instant.astimezone(zone)
    candidates=[]
    for visit in config['visits']:
        hour,minute=map(int,visit['local_start'].split(':'))
        for day in (local.date(),local.date()-timedelta(days=1)):
            due=datetime(day.year,day.month,day.day,hour,minute,tzinfo=zone)
            if due<=local and (not visit_key or visit['key']==visit_key):candidates.append((due,visit))
    if not candidates:raise ValueError('Unknown visit key or no eligible visit')
    due,visit=max(candidates,key=lambda x:x[0].astimezone(timezone.utc))
    catalog=config['macro_catalog'];tasks=[]
    for task in visit['tasks']:
        macro=catalog.get(task,{})
        supported=macro.get('status') in ('replay_verified','replay_verified_no_new_reward','real_claim_replay_verified')
        partial=macro.get('status') in ('inspection_only','cooldown_replay_verified','empty_replay_verified_help_inspection_only')
        if not (supported or partial):continue
        tasks.append({'task':task,'executor':'macro',
                      'macro':macro.get('workflow') if supported or partial else None,
                      'verification_scope':macro.get('status','not_macroized'),
                      'reason':macro.get('pending_validation') if partial else (None if supported else macro.get('status','not_macroized'))})
    return {'visit':visit['key'],'game_day_utc':instant.astimezone(timezone.utc).date().isoformat(),
            'planned_local':due.isoformat(),'planned_utc':due.astimezone(timezone.utc).isoformat(),
            'timezone':config['timezone'],'schedules_enabled':config.get('enabled',False),
            'tasks':tasks,'automatic_game_actions':False,
            'run_mode':'macro_only_record_deviations','agent_fallback':False,
            'completion_rule':'Check only the selected existing macros once after execution; record deviations without repair or additional daily tasks.'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',required=True,type=Path)
    p.add_argument('--at',help='ISO timestamp with timezone; default now UTC');p.add_argument('--visit')
    p.add_argument('--output',type=Path);a=p.parse_args()
    now=datetime.fromisoformat(a.at.replace('Z','+00:00')) if a.at else datetime.now(timezone.utc)
    if now.tzinfo is None:raise ValueError('--at must include a timezone')
    result=plan(json.loads(a.config.read_text()),now,a.visit);text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if a.output:a.output.write_text(text)
    print(text,end='')
