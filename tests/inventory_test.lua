-- Exercise real transfer actions with distinct main, character ammo, and turret
-- inventories. The default source must never silently raid equipped ammunition.
local response, request, handler
local handlers={}
defines={inventory={turret_ammo=7,character_ammo=8},events={on_tick=1},controllers={}}
script={active_mods={base='2.0.77',['codex-controller']='0.3.2'},
  on_init=function()end,on_configuration_changed=function()end,on_load=function()end,
  on_event=function(id,f)if id then handlers[id]=f end end}
commands={add_command=function(_,_,f)handler=f end}
rcon={print=function()end};log=function()end
helpers={json_to_table=function()return request end,table_to_json=function(v)response=v;return '{}' end,write_file=function()end}
local function stock(count)
  local inv={count=count}
  inv.get_item_count=function()return inv.count end
  inv.get_insertable_count=function()return 100-inv.count end
  inv.remove=function(p)local n=math.min(p.count,inv.count);inv.count=inv.count-n;return n end
  inv.insert=function(p)inv.count=inv.count+p.count;return p.count end
  return inv
end
local main,ammo,turret=stock(0),stock(20),stock(0)
local entity={name='gun-turret',type='ammo-turret',get_inventory=function(id)assert(id==7);return turret end}
local character={valid=true,type='character',position={x=0,y=0},walking_state={walking=false},
  surface={find_entities_filtered=function()return {entity} end},can_reach_entity=function()return true end,
  get_main_inventory=function()return main end,get_inventory=function(id)assert(id==8);return ammo end}
storage={agent={character=character,jobs={},order={},events={},sequence=0}}
game={tick=1,speed=1,get_player=function()return nil end}
prototypes={item={['firearm-magazine']={magazine_size=10}}}
package.path='mod/codex-controller/?.lua;'..package.path
dofile('mod/codex-controller/control.lua')
local serial=0
local function transfer(kind,source,count)
  serial=serial+1
  request={op='submit',id='transfer-'..serial,actions={{type=kind,entity='gun-turret',x=0,y=0,
    inventory='ammo',player_inventory=source,item='firearm-magazine',count=count}}}
  handler{parameter='{}'};assert(response.ok)
  handlers[1]();game.tick=game.tick+1;handlers[1]();game.tick=game.tick+1
  return storage.agent.jobs[request.id]
end
assert(transfer('put',nil,10).status=='failed')
assert(main.count==0 and ammo.count==20 and turret.count==0)
assert(transfer('put','ammo',10).status=='complete')
assert(ammo.count==10 and turret.count==10)
assert(transfer('take',nil,1).status=='complete')
assert(main.count==1 and turret.count==9)
assert(transfer('put','main',1).status=='complete')
assert(main.count==0 and turret.count==10)
assert(transfer('take','ammo',1).status=='complete')
assert(ammo.count==11 and turret.count==9)
entity.type='lab'
assert(transfer('put','ammo',1).status=='failed')
assert(ammo.count==11 and turret.count==9)
entity.type='ammo-turret'
ammo[1]={valid_for_read=true,name='firearm-magazine',ammo=4}
local failed=transfer('put','ammo',1)
assert(failed.status=='failed' and failed.error:find('partial_ammo_requires_native_inventory'))
assert(ammo.count==11 and turret.count==9 and ammo[1].ammo==4)
ammo[1].ammo=10
turret[1]={valid_for_read=true,name='firearm-magazine',ammo=7}
assert(transfer('put','ammo',1).status=='failed')
assert(transfer('take','ammo',1).status=='failed')
assert(ammo.count==11 and turret.count==9 and turret[1].ammo==7)
turret[1].ammo=10
assert(transfer('put','ammo',1).status=='complete')
assert(ammo.count==10 and turret.count==10)
print('Explicit ammo routing, default main inventory, and entity guard passed')
