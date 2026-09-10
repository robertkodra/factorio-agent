package.path='mod/codex-controller/?.lua;'..package.path
local block=require('block_observation')
local charted=true;local calls=0
local force={is_chunk_charted=function()return charted end}
local surface={index=1}
local furnace={valid=true,unit_number=10,name='stone-furnace',type='furnace',force=force,surface=surface,position={x=2,y=3}}
local hidden={valid=true,unit_number=11,name='hidden',type='unit',force={},surface=surface}
surface.find_entities_filtered=function(filter)
 calls=calls+1;assert(filter.force==force and filter.radius==0.01)
 return {furnace,hidden}
end
local c={unit_number=7,force=force,surface=surface}
local function snapshot(e,f,s)
 assert(e==furnace and f==force and s==surface)
 return {id=10,health=200,energy=1,fuel={{name='coal',count=2}},input={},output={},
  status=1,fluid_boxes={{target_position={x=999,y=999}}}}
end
local function read(req)return block.read(req,c,100,42,'0.8.1',snapshot)end
local result=read{op='observe_entities',targets={{id=10,x=2,y=3},{id=11,x=2,y=3}}}
assert(#result.entities==1 and result.missing[1]==11)
assert(result.entities[1].fuel[1].count==2 and result.entities[1].fluid_boxes==nil)
assert(result.actor_unit==7 and result.sequence==42 and result.surface==1)
local function rejects(req)
 local before=calls;assert(not pcall(read,req));assert(calls==before,'Validate entire request before lookup')
end
rejects{op='observe_entities',targets={}}
rejects{op='observe_entities',targets={{id=10,x=0,y=0}},code='anything'}
rejects{op='observe_entities',targets={{id=10,x=0,y=0},{id=10,x=0,y=0}}}
rejects{op='observe_entities',targets={{id=10,x=0/0,y=0}}}
rejects{op='observe_entities',targets={{id=10,x=0,y=0,force='enemy'}}}
local many={};for i=1,65 do many[i]={id=i,x=0,y=0}end
rejects{op='observe_entities',targets=many}
charted=false;rejects{op='observe_entities',targets={{id=10,x=0,y=0}}};charted=true
furnace.valid=false;result=read{op='observe_entities',targets={{id=10,x=2,y=3}}}
assert(#result.entities==0 and result.missing[1]==10)
print('Bounded owned/charted entity reads and rejection boundaries passed')
-- Exercise fixed command wiring and the actual shared entity projection.
local request,response,command
furnace.valid=true;furnace.position={x=2,y=3};furnace.direction=0
furnace.health=200;furnace.max_health=200;furnace.status=1;furnace.energy=50
furnace.fluidbox={};furnace.products_finished=4
furnace.get_fuel_inventory=function()return {get_contents=function()return {{name='coal',count=2}}end}end
furnace.get_inventory=function()return {get_contents=function()return {{name='iron-ore',count=1}}end}end
furnace.get_output_inventory=function()return {get_contents=function()return {{name='iron-plate',count=3}}end}end
furnace.is_crafting=function()return true end
furnace.get_recipe=function()return {name='iron-plate'}end
furnace.burner={remaining_burning_fuel=1000,currently_burning={name={name='coal'}}}
c.valid=true;c.type='character'
defines={inventory={furnace_source=1,furnace_result=2},events={},entity_status={working=1}}
script={active_mods={base='2.0.77',['codex-controller']='0.8.1'},on_init=function()end,
 on_load=function()end,on_configuration_changed=function()end,on_event=function()end}
commands={add_command=function(_,_,fn)command=fn end}
helpers={json_to_table=function()return request end,table_to_json=function(v)response=v;return '{}'end}
rcon={print=function()end};log=function()end
game={tick=100};storage={agent={character=c,events={},sequence=42,jobs={}}}
dofile('mod/codex-controller/control.lua')
request={op='observe_entities',targets={{id=10,x=2,y=3}}};command{parameter='{}'}
assert(response.ok);local v=response.result.entities[1]
assert(v.id==10 and v.health==200 and v.energy==50 and v.status_name=='working')
assert(v.fuel[1].count==2 and v.input[1].name=='iron-ore' and v.output[1].count==3)
assert(v.products_finished==4 and v.crafting and v.fluid_boxes==nil)
assert(v.recipe=='iron-plate' and v.burner.item=='coal' and v.burner.remaining_energy==1000)
request={op='hello'};command{parameter='{}'}
assert(response.ok and response.result.version=='0.8.1' and response.result.observation_contract=='smelting-block-v1')
print('Fixed command projects real owned furnace state without gameplay mutation')
