package.path='mod/codex-controller/?.lua;'..package.path
local combat=require('combat_observation')
local visible=true
local character={valid=true,unit_number=12,position={x=3,y=4},
  force={is_chunk_charted=function()return true end,is_chunk_visible=function()return visible end}}
local cause={valid=true,name='small-worm-turret',type='turret',
  position={x=20,y=4},surface={},force={name='enemy'}}
local e={entity=character,tick=100,final_health=40,final_damage_amount=7,
  damage_type={name='acid'},cause=cause}
local r=combat.record(e,character,'damage')
assert(r.health==40 and r.damage==7 and r.damage_type=='acid' and r.actor_unit==12)
assert(r.cause.name=='small-worm-turret' and r.cause.position.x==20)
assert(character.position.x==3 and e.final_health==40, 'Observation must not mutate gameplay')
visible=false;r=combat.record(e,character,'damage')
assert(r.cause.visible==false and r.cause.position==nil and r.cause.name==nil)
visible=true;e.cause={valid=false};e.source=nil
r=combat.record(e,character,'death');assert(r.cause==nil and r.kind=='death')
e.cause=nil;e.damage_type=nil;r=combat.record(e,character,'death')
assert(r.damage_type==nil and r.cause==nil)
e.entity={valid=true};assert(combat.record(e,character,'damage')==nil)
e.entity=character;character.valid=false
assert(combat.record(e,character,'damage')==nil)
-- Exercise actual event registration and status after the character is gone.
local handlers,command,request,response={},nil,nil,nil
defines={inventory={},events={on_entity_damaged=1,on_entity_died=2}}
script={active_mods={},on_init=function()end,on_load=function()end,
  on_configuration_changed=function()end,
  on_event=function(id,fn)if id then handlers[id]=fn end end}
commands={add_command=function(_,_,fn)command=fn end}
helpers={write_file=function()end,json_to_table=function()return request end,
  table_to_json=function(value)response=value;return '{}' end}
rcon={print=function()end};log=function()end;game={tick=100}
character.valid=true;e.entity=character;e.cause=cause;e.damage_type={name='acid'}
storage={agent={character=character,events={},sequence=0,jobs={}}}
dofile('mod/codex-controller/control.lua')
handlers[1](e);handlers[2](e);character.valid=false
request={op='status',after=0};command{parameter='{}'}
assert(response.ok and response.result.status=='idle')
assert(response.result.last_damage.health==40)
assert(response.result.last_death.actor_unit==12 and #response.result.events==2)
assert(response.result.events[1].kind=='engineer_damaged')
assert(response.result.events[2].kind=='engineer_died')
print('Combat observation, missing causes and charted boundaries passed')
