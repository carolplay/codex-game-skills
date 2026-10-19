#!/usr/bin/env python3
"""Generate a fixed mixed-intel action from versioned local components; never launches a game."""
import json,copy,hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[1]
def build(flows):
 base=copy.deepcopy(flows['beast']);prefix=[]
 for s in base['steps']:
  if s['name'].startswith('beast-0-'):break
  prefix.append(s)
 keys=['firebeast','beast','rescue','hero'];conditions=[];groups={}
 for key in keys:
  source=flows[key];old='beast' if key=='firebeast' else key;group=[copy.deepcopy(s) for s in source['steps'] if s['name'].startswith(old+'-0-')];selector=group[0];conditions.append(copy.deepcopy(selector['finish_if']['template_regions'][0]));groups[key]=(old,group)
 empty=copy.deepcopy(prefix[-1]['before']);empty['template_regions']=conditions
 map_before=copy.deepcopy(prefix[-1]['before']);steps=copy.deepcopy(prefix)
 for n in range(1):
  steps.append({'name':f'cycle-{n}-empty-check','action':'observe','before':map_before,'finish_if':empty})
  for key in keys:
   old,group=groups[key];group=json.loads(json.dumps(group,ensure_ascii=False).replace(old+'-0-',f'cycle-{n}-{key}-'))
   selector=group[0];selector['skip_if']=selector.pop('finish_if')
   for s in group[1:]:s['skip_if_step_skipped']=selector['name']
   steps.extend(group)

 def strengthen(x):
  if isinstance(x,dict):
   if '城镇' in x.get('all',[]) and '英雄' in x.get('all',[]):
    regions=x.setdefault('page_text_regions',[]);crop=[600,1010,689,1079]
    if crop not in regions:regions.append(crop)
   for v in x.values():strengthen(v)
  elif isinstance(x,list):
   for v in x:strengthen(v)
 strengthen(steps)
 return {'action_id':'wos-intel-cycle','action_version':'0.1.0','name':'WOS local mixed intelligence cycle','reference_size':[788,1079],'status':'candidate','execution_timeout_seconds':1800,'repeat_from':'cycle-0-empty-check','steps':steps,'task_contract':copy.deepcopy(flows['hero']['task_contract']),'verification_scope':'Repeat mixed tasks until registered markers are absent; no task-count cap, 1800s watchdog; unknownskins and bounty not inferredcomplete. Standalone ordinarycomponents and Firebeast paths were sampled; fullcycle livepending.','business_dependencies':['Fixedcityentry andexit; local map must be re-observed before every selection','Firebeast/ordinarybeast/rescue/hero may reveal more queued tasks afterclaim; repeatuntil allknownmarkers absent or1800s watchdog','Absence of registered glyphs is not proof that unknownskins/bounties are done; final auditrecords deviations'],'component_versions':{k:{'action_id':v['action_id'],'action_version':v['action_version'],'sha256':hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()} for k,v in flows.items()}}
if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--output',type=Path,required=True)
 parser.add_argument('--version',required=True,help='Deliberate new action version; repin catalog/manifests separately')
 args=parser.parse_args()
 flows={k:json.loads((root/f'actions/wos-intel-{k}.json').read_text()) for k in ['beast','rescue','hero','firebeast']}
 flow=build(flows);flow['action_version']=args.version
 args.output.write_text(json.dumps(flow,ensure_ascii=False,indent=2)+'\n')
 print(args.output)
