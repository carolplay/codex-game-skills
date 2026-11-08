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
def add_two_button_claims(flow):
 """Visible but locked execute-all still has the new right-hand claim button."""
 flow=copy.deepcopy(flow);steps=flow['steps']
 if any(step['name']=='pre-layout-claim-existing' for step in steps):return flow
 old_layout={'all':['情报','下次刷新'],'none':['全部执行'],'page_text_regions':[[110,970,680,1060]]}
 reward={'any':['获得奖励','恭喜获得','点击任意位置退出'],'none':['胜利','失败','战败']}
 initial=[]
 for old,new in [('batch-claim-existing','pre-layout-claim-existing'),('batch-claim-existing-retry','pre-layout-claim-existing-retry'),('batch-dismiss-existing','pre-layout-dismiss-existing'),('batch-dismiss-existing-level-up','pre-layout-dismiss-existing-level-up')]:
  item=copy.deepcopy(next(x for x in steps if x['name']==old));item['name']=new;item.pop('skip_if_step_skipped',None)
  item.setdefault('skip_if_any',[]).append(copy.deepcopy(old_layout));initial.append(item)
 at=next(i for i,x in enumerate(steps) if x['name']=='batch-mode');steps[at:at]=initial
 result=[]
 for item in steps:
  if item['name'].startswith('legacy-') and item['name'].endswith('-claim') and item.get('action')=='click' and item.get('point')==[394,1017]:
   right=copy.deepcopy(item);right['name']+='-two-button';right['point']=[532,1017]
   right['before']['all']+=['全部执行','一键领取'];right['before']['page_text_regions']=[[110,970,680,1060]];right['before']['green_regions']=[{'bounds':[425,1000,650,1040],'min':.12}]
   right['skip_if']['green_regions']=[{'bounds':[425,1000,650,1040],'max':.08}];right.setdefault('skip_if_any',[]).append(copy.deepcopy(old_layout));result.append(right)
   item.setdefault('skip_if_any',[]).append(copy.deepcopy(reward))
  result.append(item)
 flow['steps']=result
 return flow

def add_firebeast_layout_waits(flow):
 """The locked two-button layout still claims on the right, after real travel."""
 flow=copy.deepcopy(flow);result=[]
 layout={'all':['情报','下次刷新','全部执行','一键领取'],'page_text_regions':[[110,970,680,1060]]}
 for step in flow['steps']:
  if step['name']=='legacy-cycle-0-firebeast-wait-complete':
   step['observe_interval_seconds']=5;step['skip_if']=copy.deepcopy(layout);result.append(step)
   other=copy.deepcopy(step);other['name']='legacy-cycle-0-firebeast-wait-two-button';other.pop('skip_if')
   other['before']=copy.deepcopy(layout);other['before']['none']=['前往查看','获得奖励','恭喜获得','点击任意位置退出']
   other['before']['green_regions']=[{'bounds':[425,1000,650,1040],'min':.12}]
   other['skip_if']={'all':['情报','下次刷新'],'none':['全部执行'],'page_text_regions':[[110,970,680,1060]]};result.append(other)
  else:result.append(step)
 flow['steps']=result
 return flow

def apply_bulk_lock_layout(flow):
 """A visible bulk label can be locked below lighthouse20; use legacy then."""
 flow=copy.deepcopy(flow)
 spec={'template':'intel-bulk-locked','bounds':[359,955,405,1012],'mode':'white-glyph','min_score':.94}
 locked={'all':['情报','下次刷新','全部执行'],'page_text_regions':[[110,970,680,1060]],'template_regions':[spec]}
 for step in flow['steps']:
  name=step['name']
  if name in ('batch-mode','event-firebeast-select'):step.setdefault('skip_if_any',[]).append(copy.deepcopy(locked))
  if name=='legacy-mode':step['skip_if']['template_regions']=[{**spec,'present':False}]
  if name=='legacy-empty-check':step['finish_if']['none']=[label for label in step['finish_if'].get('none',[]) if label!='全部执行']
  if name.startswith('legacy-'):
   for condition in step.get('skip_if_any',[]):
    if '全部执行' in condition.get('all',[]):condition['template_regions']=[{**spec,'present':False}]
 return add_firebeast_layout_waits(add_two_button_claims(flow))

def apply_partial_stamina_policy(flow):
 """Regenerate the published partial-dispatch and current hero-page behavior."""
 flow=copy.deepcopy(flow)
 red={'bounds':[250,1015,315,1045],'min':.02}
 low={'all':['情报','下次刷新','全部执行'],'none':['前往查看','获得奖励','全部执行中'],'page_text_regions':[[110,970,680,1060]],'red_regions':[red]}
 legacy_skip=copy.deepcopy(next(s for s in flow['steps'] if s['name']=='legacy-mode')['skip_if'])
 legacy_skip['all']=['情报','下次刷新','全部执行(']
 normal=copy.deepcopy(legacy_skip)
 legacy_skip['red_regions']=[{'bounds':[250,1015,315,1045],'max':.019}]
 floor={'all':['情报','下次刷新'],'none':['前往查看','获得奖励'],'text_regions':[{'bounds':[590,35,655,82],'pattern':r'^[0-9]$','crop_ocr':True,'min_confidence':.4,'prefer_frame_ocr':True}]}
 result=[]
 for step in flow['steps']:
  name=step['name']
  if name=='batch-round-anchor':
   done=step['finish_if'];done.pop('template_regions',None)
   done['page_text_regions']=[[100,30,690,205],[110,970,680,1060]]
   done['text_regions'][0]['pattern']=r'全部执行\([0O〇]\)'
   done['text_regions'][1]['pattern']=r'一键领取\([0O〇]\)'
   step['partial_completion_note']='Only execute(0)+claim(0) proves ordinary drain; low-stamina-floor is deferred remainder, never all tasks completed.'
  if name in ('batch-mode','event-firebeast-select'):
   step.setdefault('skip_if_any',[]).append(copy.deepcopy(low))
  if name=='batch-mode':
   step['skip_if_any'].append({'all':['情报','下次刷新','全部执行'],'none':['全部执行(','全部执行中','前往查看','获得奖励','恭喜获得'],'page_text_regions':[[110,970,680,1060]]})
  if name=='legacy-mode':step['skip_if']=copy.deepcopy(legacy_skip)
  if name in [f'legacy-cycle-0-{key}-select' for key in ('firebeast','beast','rescue','hero')]:
   before=copy.deepcopy(floor);before.pop('text_regions')
   result.append({'name':name+'-stamina-floor','action':'observe','before':before,'skip_if_step_skipped':'legacy-mode','finish_if':copy.deepcopy(floor)})
   step['skip_if_any']=[copy.deepcopy(legacy_skip)]
   if name=='legacy-cycle-0-firebeast-select':step['skip_if_any'].append(copy.deepcopy(normal))
  if name=='legacy-cycle-0-hero-explore':step['after']=['小队设置','战斗']
  if name=='legacy-cycle-0-hero-fight':step['before']=['小队设置','战斗']
  result.append(step)
 flow['steps']=result
 for step in flow['task_contract']['exits']:
  if step['name']=='exit-formation':step['before']=['小队设置','战斗']
  if step['name']=='exit-intel-stamina-supply':step['after']={'any':['情报','士兵比例','城镇'],'none':['获取更多','领主体力','丰盛的招待']}
 return flow

def build(flows):
 """New game-owned bulk execution; keep the event-only firebeast path."""
 legacy=build_legacy(flows)
 # Preserve the published mixed cycle's bounded exit budget when regenerating.
 # Components have their own budgets; copying the hero contract omits this one.
 legacy['task_contract']['recovery_timeout_seconds']=120
 level_page={'all':['探照灯升级','情报品质','最大情报刷新数量','点击任意位置继续'],'page_text_regions':[[200,180,590,270]]}
 legacy['task_contract']['exits'].insert(0,{'name':'exit-lighthouse-level-up','action':'click','point':[394,985],'before':copy.deepcopy(level_page),'after':{'all':['情报','下次刷新'],'none':['探照灯升级','前往查看']},'observe_attempts':5})
 legacy['task_contract']['exits'].insert(0,{'name':'exit-intel-stamina-supply','action':'click','point':[645,137],'before':['获取更多','领主体力','丰盛的招待'],'after':{'all':['情报','下次刷新'],'none':['获取更多','前往查看']},'observe_attempts':5})
 legacy['task_contract']['exits'].insert(0,{'name': 'exit-march-capacity-info', 'action': 'click', 'point': [625, 306], 'before': {'all': ['行军队列', '额外队列', '激活VIP', '前往购买'], 'text_regions': [{'bounds': [300, 280, 500, 335], 'pattern': '行军队列', 'crop_ocr': True, 'prefer_frame_ocr': True, 'min_confidence': 0.3}]}, 'after': {'all': ['英雄', '背包'], 'any': ['城镇', '野外'], 'none': ['额外队列', '前往激活'], 'page_text_regions': [[100, 995, 690, 1079]]}, 'observe_attempts': 5})
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
 def bounded_claim(name):
  first=claim(name)
  # An unchanged green claim button is intermediate evidence, not success.
  first['after']={'any':reward['any']+['情报'],'none':reward['none']}
  second=claim(name+'-retry')
  second.pop('skip_if')
  second['before']['all']=[label for label in second['before']['all'] if label!='一键领取']
  second['skip_if_any']=[copy.deepcopy(reward),copy.deepcopy(zero_right)]
  return [first,second]
 steps.extend([*bounded_claim('batch-claim-existing'),dismiss('batch-dismiss-existing'),
  {'name':'batch-execute','action':'click','text_target':{'text':'全部执行','bounds':left,'exact':False,'crop_ocr':True,'min_confidence':.3,'offset':[0,30]},'before':{**copy.deepcopy(button_page),'blue_regions':[{'bounds':blue_box,'min':.4}],'none':map_page['none']+['全部执行中']},'skip_if':zero_left,'after':['情报','下次刷新'],'observe_attempts':10},
  {'name':'batch-wait-complete','action':'observe','before':{**copy.deepcopy(button_page),'none':map_page['none']+['全部执行中']},'observe_attempts':30},
  *bounded_claim('batch-claim-completed'),dismiss('batch-dismiss-completed'),
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
  if s['name']=='event-firebeast-wait-complete':
   s['before']['green_regions']=[{'bounds':green_box,'min':.12}]
   s['observe_attempts']=30;s['observe_interval_seconds']=5
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
  else:
   # Chain every legacy selector to the already observed layout decision.
   # Whole-frame OCR can omit the bulk label on a later frame.
   s['skip_if_step_skipped']='legacy-mode'
   s.setdefault('skip_if_any',[]).append({'all':['情报','下次刷新','全部执行'],'page_text_regions':[[110,970,680,1060]]})
  steps.append(s)
 # Rewards can unlock a level-up overlay before the map is visible again.
 # Each optional dismissal retains the original map postcondition.
 expanded=[]
 for s in steps:
  if s.get('action')=='click' and ('close-reward' in s['name'] or s['name'].startswith('batch-dismiss-')):
   after=copy.deepcopy(s.get('after'))
   if isinstance(after,dict) and '下次刷新' in after.get('all',[]):
    s['after']={'any':['下次刷新','探照灯升级'],'page_text_regions':[[200,180,590,270]],'none':['胜利','失败','战败']}
    follow={'name':s['name']+'-level-up','action':'click','point':[394,985],'before':copy.deepcopy(level_page),'after':after,'skip_if':copy.deepcopy(after),'observe_attempts':5}
    if s.get('skip_if_step_skipped'):follow['skip_if_step_skipped']=s['skip_if_step_skipped']
    expanded.extend([s,follow]);continue
  expanded.append(s)
 steps=expanded
 return apply_partial_stamina_policy(apply_bulk_lock_layout({**legacy,'name':'WOS bulk intelligence execution plus event firebeast','steps':steps,'repeat_from':'batch-round-anchor','verification_scope':'0.2.3 scoped button OCR and lower execute click avoid cursor hiding zero-count label; prior role bulk9 completed but wait predicate failed before claim. Development bulk9 actual claim; next mature role0.2.1 bulk execution/wait/claim passed, firebeast dispatched but wait checked old claim region and bounded exit restored city.0.2.2 fixes event wait crop, requires explicit zero counts before completion to distinguish insufficient stamina, and retains prior local components only when bulk UI absent. New patch live pending; never agent fallback.','business_dependencies':['City entry and exit; stamina meal uses lighthouse plus before this action','Game execute-all handles ordinary intel; repeat after claim reveals queued tasks','Event firebeast remains separate; no claim that bulk clears event tasks','Explicit zero execute/claim counts, disabled buttons, not executing and no firebeast required for bulk completion','If bulk button absent or visibly locked, use fixed local legacy branches; actual UI determines availability']}))

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
