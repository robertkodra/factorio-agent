-- Execute real transfer actions. Only transfer_stack may change inventory.
local response, request, handler
local handlers={}
defines={inventory={turret_ammo=7,character_ammo=8,lab_input=9,assembling_machine_input=5},events={on_tick=1},controllers={}}
script={active_mods={base='2.0.77',['codex-controller']='0.5.0'},
  on_init=function()end,on_configuration_changed=function()end,on_load=function()end,
  on_event=function(id,f)if id then handlers[id]=f end end}
commands={add_command=function(_,_,f)handler=f end}
rcon={print=function()end};log=function()end
helpers={json_to_table=function()return request end,table_to_json=function(v)response=v;return '{}' end,write_file=function()end}
local function stock(count,rounds)
  local stack={valid_for_read=count>0,name='firearm-magazine',count=count,ammo=rounds or 10}
  local inv={stack}
  inv.get_item_count=function()return stack.count end
  inv.get_insertable_count=function()return 100-stack.count end
  inv.remove=function()error('Must not destroy stack metadata')end
  inv.insert=function()error('Must not reconstruct ammunition')end
  stack.transfer_stack=function(src,n)
    assert(src~=stack and n<=src.count)
    local transferred=n==src.count and ((n-1)*10+src.ammo) or n*10
    local target_rounds=stack.count>0 and ((stack.count-1)*10+stack.ammo) or 0
    src.count=src.count-n;src.valid_for_read=src.count>0
    target_rounds=target_rounds+transferred
    stack.count=math.ceil(target_rounds/10);stack.ammo=(target_rounds-1)%10+1;stack.valid_for_read=true
    return true
  end
  return inv
end
local main,ammo,turret=stock(0),stock(20,4),stock(0)
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
local function transfer(kind,source,count,inventory)
  serial=serial+1
  request={op='submit',id='transfer-'..serial,actions={{type=kind,entity='gun-turret',x=0,y=0,
    inventory=inventory or 'ammo',player_inventory=source,item='firearm-magazine',count=count}}}
  handler{parameter='{}'};assert(response.ok)
  handlers[1]();game.tick=game.tick+1;handlers[1]();game.tick=game.tick+1
  return storage.agent.jobs[request.id]
end
local function total()
 local result=0
 for _,inv in ipairs({main,ammo,turret})do local s=inv[1];if s.valid_for_read then result=result+(s.count-1)*10+s.ammo end end
 return result
end
assert(total()==194)
assert(transfer('put',nil,10).status=='failed' and total()==194)
assert(transfer('put','ammo',10).status=='complete' and total()==194)
assert(ammo[1].count==10 and turret[1].count==10)
assert(transfer('put','ammo',10).status=='complete' and total()==194)
assert(ammo[1].count==0 and turret[1].ammo==4)
assert(transfer('take','ammo',9).status=='complete' and total()==194)
assert(transfer('take','main',11).status=='complete' and total()==194)
assert(main[1].ammo==4 and turret[1].count==0)
assert(transfer('put','main',11).status=='complete' and total()==194)
entity.type='lab'
assert(transfer('put','ammo',1).status=='failed' and total()==194)
-- Input mapping must select the lab inventory, not an assembler's numeric ID.
entity.get_inventory=function(id)assert(id==9);return turret end
assert(transfer('put','ammo',1,'input').status=='complete' and total()==194)
print('Native amount-limited transfer, partial rounds, reserves, and lab mapping passed')
