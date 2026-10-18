"""Summarize canonical run reports; no game access or shared-quota attribution."""
import argparse
import csv
import json
from datetime import datetime
from pathlib import Path


def first(data,*keys):
    return next((data[k] for k in keys if data.get(k) is not None),None)


def elapsed(start,end):
    try:
        return round((datetime.fromisoformat(end.replace('Z','+00:00'))-datetime.fromisoformat(start.replace('Z','+00:00'))).total_seconds()/60,2)
    except (ValueError,TypeError,AttributeError):return None


def canonical_reports(directory):
    grouped={}
    for path in sorted(Path(directory).glob('*.json')):
        try:data=json.loads(path.read_text())
        except (ValueError,OSError):continue
        if not isinstance(data,dict):continue
        run=str(data.get('run_id') or path.name.split('.')[0])
        if 'device' in path.stem or data.get('category') or not data.get('role'):continue
        rank=3 if path.name==run+'.json' else 1 if 'checkpoint' in path.stem else 2
        if run not in grouped or rank>grouped[run][0]:grouped[run]=(rank,path,data)
    return {run:(p,d) for run,(_,p,d) in grouped.items()}


def rows_for(directory,state=None):
    reports=canonical_reports(directory)
    dispatch={str(r['run_id']):r for r in (state or {}).get('runs',[])}
    rows=[]
    for run in sorted(set(reports)|set(dispatch)):
        path,data=reports.get(run,(None,{}));entry=dispatch.get(run,{})
        m=data.get('metrics') or data.get('metrics_final') or {}
        m=m if isinstance(m,dict) else {}
        usage=data.get('usage') or {};finish=data.get('coordination_finish') or {}
        start=first(m,'started_at') or first(data,'started_at','started_at_utc','utc_started_at','lock_acquired_at') or entry.get('started_at')
        end=first(m,'finished_at') or first(data,'finished_at','ended_at_utc') or finish.get('ended_at') or entry.get('ended_at')
        stop=first(m,'ui_stopped_at') or first(data,'ui_stopped_at','ui_stopped_at_utc','utc_ui_stopped_at')
        actions=m.get('actions') or [];totals=m.get('totals') or {}
        def total(key):
            values=[a.get(key) for a in actions if isinstance(a,dict)]
            if values and all(type(v) in (int,float) for v in values):return sum(values)
            return totals.get(key) if not actions and type(totals.get(key)) in (int,float) else None
        credits=m.get('credits') or {};tokens=m.get('tokens') or {}
        report_kind='missing' if path is None else 'checkpoint' if 'checkpoint' in path.stem else 'final'
        warnings=[]
        if report_kind!='final':warnings.append('final_report_'+report_kind)
        if not start or not end:warnings.append('timing_incomplete')
        if data.get('tasks_all_complete') is False:warnings.append('daily_tasks_incomplete')
        rows.append(dict(run_id=run,role=data.get('role') or entry.get('role'),
            outcome=first(data,'outcome','run_outcome','status') or entry.get('status'),
            tasks_all_complete=data.get('tasks_all_complete'),report_kind=report_kind,
            started_at=start,ended_at=end,elapsed_minutes=elapsed(start,end),ui_elapsed_minutes=elapsed(start,stop),
            model=m.get('model'),shared_start_percent=(m.get('usage_start')or{}).get('used_percent',first(usage,'start_used_percent','shared_used_percent_start')),
            shared_end_percent=(m.get('usage_end')or{}).get('used_percent',first(usage,'end_used_percent','shared_used_percent_end')),
            credit_cost=credits.get('attributable_cost') if credits.get('source') else None,
            input_tokens=tokens.get('input'),cached_input_tokens=tokens.get('cached_input'),output_tokens=tokens.get('output'),total_tokens=tokens.get('total'),
            screenshots=total('screenshots'),retries=total('retries'),
            attribution='Shared usage is observational only; exact credits require a per-run source.',
            warnings=';'.join(warnings),report=str(path) if path else None))
    return rows


def write(rows,directory):
    folder=Path(directory);folder.mkdir(parents=True,exist_ok=True)
    (folder/'runs.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    if rows:
        with (folder/'runs.csv').open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    missing=[r for r in rows if r['report_kind']!='final']
    (folder/'report-followups.json').write_text(json.dumps(missing,ensure_ascii=False,indent=2)+'\n')
    return {'runs':len(rows),'missing_final_reports':len(missing),'output':str(folder/'runs.csv')}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--feedback',required=True,type=Path);p.add_argument('--state',type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    state=json.loads(a.state.read_text()) if a.state and a.state.exists() else {}
    print(json.dumps(write(rows_for(a.feedback,state),a.output)))
