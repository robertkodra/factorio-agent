package.path='mod/codex-controller/?.lua;'..package.path
defines={inventory={character_guns=1,character_ammo=2},shooting={not_shooting=0,shooting_selected=2},
  events={on_tick=1,on_entity_damaged=2,on_entity_died=3},controllers={spectator=5}}
local M=require('reflex')
local seen,clear,shootable=true,true,true
local ammo={valid_for_read=true,name='firearm-magazine',count=2,ammo=7}
local gun={valid_for_read=true,name='pistol'}
local enemy={valid=true,unit_number=8,name='small-biter',position={x=4,y=0},prototype={attack_parameters={range=1}},force={name='enemy'}}
local entities={enemy}
local c={valid=true,name='character',type='character',unit_number=12,position={x=0,y=0},health=250,max_health=250,
  force={is_chunk_visible=function()return seen end,is_chunk_charted=function()return seen end},
  surface={find_entities_filtered=function()return entities end,can_place_entity=function()return clear end},
  get_inventory=function(i)if i==1 then return {gun} else return {ammo} end end,
  can_shoot=function(target,p)assert(target==enemy and p==enemy.position);return shootable end}
local g={enabled=true,urgent=true}
assert(M.update(c,g,1,nil) and g.active)
assert(c.shooting_state.state==2 and c.walking_state.walking and c.mining_state.mining==false)
assert(c.walking_state.direction==12, 'Move away from the enemy to the east')
assert(ammo.count==2 and ammo.ammo==7 and c.health==250, 'Only engine inputs may change; no manufactured shots')
seen=false;g={enabled=true,urgent=true}
assert(not M.update(c,g,1,nil) and g.observation.total==0, 'No targeting through fog')
seen=true;shootable=false;g={enabled=true,urgent=true}
assert(M.update(c,g,1,nil) and c.shooting_state.state==0, 'Engine range/cooldown check must pass')
shootable=true;ammo.valid_for_read=false;g={enabled=true,urgent=true}
assert(M.update(c,g,1,nil) and c.shooting_state.state==0 and c.walking_state.walking)
ammo.valid_for_read=true;clear=false;g={enabled=true,urgent=true}
M.update(c,g,1,nil);assert(not c.walking_state.walking, 'Do not step into collision')
clear=true;entities={};g={enabled=true,urgent=true};c.health=33
assert(M.update(c,g,1,nil), 'Critical health cannot depend on model advice')
c.health=250;g={enabled=true,urgent=true}
assert(not M.update(c,g,1,{actor_unit=999,tick=1}), 'Old life damage must not trigger reflex')
assert(M.update(c,g,3,{actor_unit=12,tick=3}))
assert(not M.update(c,g,300,nil), 'Clear only after quiet hysteresis')
assert(c.shooting_state.state==0 and not c.walking_state.walking)

-- Register the real controller; drive 60 simulated seconds with no model/client.
local handlers,command,request,response={},nil,nil,nil
script={active_mods={base='2.0.77',['codex-controller']='0.4.0'},on_init=function()end,
  on_load=function()end,on_configuration_changed=function()end,
  on_event=function(id,fn)if id then handlers[id]=fn end end}
commands={add_command=function(_,_,fn)command=fn end}
helpers={write_file=function()end,json_to_table=function()return request end,
  table_to_json=function(value)response=value;return '{}' end}
rcon={print=function()end};log=function()end
game={tick=1,speed=1,get_player=function()return nil end}
local j={id='haul',status='running',index=1,actions={{type='walk'}},metrics={}}
storage={agent={character=c,events={},sequence=0,jobs={haul=j},current='haul',guard={enabled=true,urgent=true}}}
entities={enemy}
dofile('mod/codex-controller/control.lua')
for tick=1,3600 do game.tick=tick;handlers[1]() end
assert(j.status=='cancelled' and j.error=='defense_interrupt')
assert(c.shooting_state.state==2 and c.walking_state.walking)
assert(storage.agent.guard.enabled and storage.agent.guard.active)
assert(#storage.agent.events<10, 'Do not flood event history every combat tick')
request={op='cancel'};command{parameter='{}'}
assert(response.ok and not storage.agent.guard.enabled)
assert(c.shooting_state.state==0 and not c.walking_state.walking)
request={op='guard',enabled=true,rally={x=1000,y=0}};command{parameter='{}'}
assert(not response.ok, 'Reject distant rally without revealing terrain')
request={op='guard',enabled=true,rally={x=5,y=0}};command{parameter='{}'}
assert(response.ok and storage.agent.guard.enabled)
request={op='guard',enabled=false,code='no'};command{parameter='{}'}
assert(not response.ok, 'Reject unknown command fields')
storage.agent.events={{seq=5,tick=1,kind='test'}};storage.agent.sequence=5
request={op='status',after=0};command{parameter='{}'}
assert(response.ok and response.result.events_lost and response.result.oldest_sequence==5)
-- A charted but currently hidden enemy must not leak through the general scan.
seen=false;c.force.is_chunk_charted=function()return true end
request={op='scan',type='unit'};command{parameter='{}'}
assert(response.ok and response.result.total==0)
seen=true;request={op='scan',type='unit'};command{parameter='{}'}
assert(response.ok and response.result.total==1 and response.result.entities[1].id==8)
print('Reflex visibility, legal inputs, interruption, stop, and 3600 tick offline trace passed')
