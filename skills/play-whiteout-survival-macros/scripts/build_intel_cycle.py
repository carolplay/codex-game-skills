#!/usr/bin/env python3
"""Generate a fixed mixed-intel action from versioned local components; never launches a game."""
import json,copy,hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[1]
def build_legacy(flows):
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
def build(flows):
 """New game-owned bulk execution; keep the event-only firebeast path."""
 legacy=build_legacy(flows)
 legacy['task_contract']['exits'].insert(0,{'name':'exit-intel-stamina-supply','action':'click','point':[645,137],'before':['获取更多','领主体力','丰盛的招待'],'after':{'all':['情报','下次刷新'],'none':['获取更多','前往查看']},'observe_attempts':5})
 map_page={'all':['情报','下次刷新'],'none':['前往查看','获得奖励','恭喜获得','点击任意位置退出']}
 left=[125,980,380,1047];right=[410,980,665,1047]
 def counter(bounds,pattern):return {'bounds':bounds,'pattern':pattern,'crop_ocr':True,'min_confidence':.3}
 def count_page(bounds,pattern):return {**copy.deepcopy(map_page),'text_regions':[counter(bounds,pattern)]}
 button_page={**copy.deepcopy(map_page),'all':map_page['all']+['全部执行','一键领取'],'page_text_regions':[[110,970,680,1060]]}
 blue_box=[135,990,365,1040];green_box=[425,1000,650,1040]
 zero_left={**copy.deepcopy(button_page),'blue_regions':[{'bounds':blue_box,'max':.08}],'none':map_page['none']+['全部执行中'],'text_regions':[counter(left,r'全部执行\(0\)')]}
 zero_right={**copy.deepcopy(button_page),'green_regions':[{'bounds':green_box,'max':.08}]}
 fire_absent=copy.deepcopy(legacy['steps'][9]['finish_if']['template_regions'][0])
 done={**copy.deepcopy(button_page),'none':map_page['none']+['全部执行中'],'blue_regions':[{'bounds':blue_box,'max':.08}],'green_regions':[{'bounds':green_box,'max':.08}],'text_regions':[counter(left,r'全部执行\(0\)'),counter(right,r'一键领取\(0\)')],'template_regions':[fire_absent]}
 steps=copy.deepcopy(flows['beast']['steps'][:6])
 steps.append({'name':'batch-round-anchor','action':'observe','before':map_page,'finish_if':done,'observe_attempts':10})
 steps.append({'name':'batch-mode','action':'observe','before':map_page,'skip_if':{'all':['情报','下次刷新'],'none':['全部执行'],'page_text_regions':[[110,970,680,1060]]}})
 reward={'any':['获得奖励','恭喜获得','点击任意位置退出'],'none':['胜利','失败','战败']}
 def claim(name):
  before=copy.deepcopy(button_page)
  before['green_regions']=[{'bounds':green_box,'min':.12}]
  return {'name':name,'action':'click','point':[532,1017],'before':before,'after':reward,'skip_if':zero_right,'observe_attempts':10}
 def dismiss(name):return {'name':name,'action':'click','point':[394,960],'before':reward,'after':map_page,'skip_if':map_page,'observe_attempts':10}
 steps.extend([claim('batch-claim-existing'),dismiss('batch-dismiss-existing'),
  {'name':'batch-execute','action':'click','text_target':{'text':'全部执行','bounds':left,'exact':False,'crop_ocr':True,'min_confidence':.3,'offset':[0,30]},'before':{**copy.deepcopy(button_page),'blue_regions':[{'bounds':blue_box,'min':.4}],'none':map_page['none']+['全部执行中']},'skip_if':zero_left,'after':['情报','下次刷新'],'observe_attempts':10},
  {'name':'batch-wait-complete','action':'observe','before':{**copy.deepcopy(button_page),'none':map_page['none']+['全部执行中']},'observe_attempts':30},
  claim('batch-claim-completed'),dismiss('batch-dismiss-completed'),
  {'name':'batch-settle-map','action':'observe','before':map_page,'observe_attempts':10}])
 for s in steps[8:]:s['skip_if_step_skipped']='batch-mode'
 # Bulk execution leaves the event firebeast on the map. Its already-known
 # dispatch branch remains, but uses the new claim button after completion.
 group=[copy.deepcopy(s) for s in flows['firebeast']['steps'] if s['name'].startswith('beast-0-')]
 group=json.loads(json.dumps(group,ensure_ascii=False).replace('beast-0-','event-firebeast-'))
 group[0]['skip_if']=group[0].pop('finish_if')
 group[0]['skip_if_any']=[{'all':['情报','下次刷新'],'none':['全部执行']}]
 for s in group[1:]:s['skip_if_step_skipped']=group[0]['name']
 for s in group:
  if s['name']=='event-firebeast-claim':
   new=claim(s['name']);new['skip_if_step_skipped']=group[0]['name'];s.clear();s.update(new)
  if s['name']=='event-firebeast-wait-complete':s['before']['green_regions']=[{'bounds':green_box,'min':.12}]
 steps.extend(group)
 # Roles without the game's bulk button retain the previous local components;
 # the UI selects the branch, never the agent or an assumed account level.
 steps.append({'name':'legacy-mode','action':'observe','before':map_page,'skip_if':{'all':['情报','下次刷新','全部执行'],'page_text_regions':[[110,970,680,1060]]}})
 for source in flows['beast']['steps'][6:9]:
  s=copy.deepcopy(source);s['name']='legacy-'+s['name'];s['skip_if_step_skipped']='legacy-mode';steps.append(s)
 empty=copy.deepcopy(legacy['steps'][9]);empty['name']='legacy-empty-check';empty['finish_if'].setdefault('none',[]).append('全部执行');empty['skip_if_step_skipped']='legacy-mode';steps.append(empty)
 for source in legacy['steps'][10:]:
  s=copy.deepcopy(source);s['name']='legacy-'+s['name']
  if s.get('skip_if_step_skipped'):s['skip_if_step_skipped']='legacy-'+s['skip_if_step_skipped']
  else:s.setdefault('skip_if_any',[]).append({'all':['情报','下次刷新','全部执行']})
  steps.append(s)
 return {**legacy,'name':'WOS bulk intelligence execution plus event firebeast','steps':steps,'repeat_from':'batch-round-anchor','verification_scope':'0.2.3 scoped button OCR and lower execute click avoid cursor hiding zero-count label; prior role bulk9 completed but wait predicate failed before claim. Development bulk9 actual claim; next mature role0.2.1 bulk execution/wait/claim passed, firebeast dispatched but wait checked old claim region and bounded exit restored city.0.2.2 fixes event wait crop, requires explicit zero counts before completion to distinguish insufficient stamina, and retains prior local components only when bulk UI absent. New patch live pending; never agent fallback.','business_dependencies':['City entry and exit; stamina meal uses lighthouse plus before this action','Game execute-all handles ordinary intel; repeat after claim reveals queued tasks','Event firebeast remains separate; no claim that bulk clears event tasks','Explicit zero execute/claim counts, disabled buttons, not executing and no firebeast required for bulk completion','If bulk button absent, use fixed local legacy branches; actual UI determines availability']}

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
