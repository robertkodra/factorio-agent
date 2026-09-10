-- The real fixed executor must preserve native placement and item costs.
local response,request,command;local handlers={};local created={};local stock=2
local owner={};local character={valid=true,type='character',force={},position={x=0,y=0},
 walking_state={walking=false},crafting_queue_size=0,
 get_item_count=function()return stock end,
 remove_item=function(a)stock=stock-a.count;return a.count end,
 insert=function(a)stock=stock+a.count end}
character.can_place_entity=function()return character.allowed~=false end
character.surface={create_entity=function(a)
 assert(a.raise_built and a.build_check_type==1)
 created[#created+1]=a
 if character.fail_create then return nil end
 return {name=a.name,position=a.position}
end}
defines={inventory={},events={on_tick=1},controllers={},build_check_type={manual=1}}
script={active_mods={base='2.0.77',['codex-controller']='0.7.0'},on_init=function()end,
 on_configuration_changed=function()end,on_load=function()end,
 on_event=function(id,f)if id then handlers[id]=f end end}
commands={add_command=function(_,_,f)command=f end};rcon={print=function()end};log=function()end
helpers={json_to_table=function()return request end,table_to_json=function(v)response=v;return '{}' end,write_file=function()end}
storage={agent={character=character,owner=1,jobs={},order={},events={},sequence=0,follow=false}}
game={tick=1,speed=1,get_player=function()return owner end}
prototypes={entity={['underground-belt']={type='underground-belt'},['transport-belt']={type='transport-belt'}},item={
 ['underground-belt']={place_result={name='underground-belt'}},['transport-belt']={place_result={name='transport-belt'}}}}
package.path='mod/codex-controller/?.lua;'..package.path
dofile('mod/codex-controller/control.lua')
local serial=0
local function place(entity,belt_type)
 serial=serial+1;request={op='submit',id='belt-'..serial,actions={{type='place',entity=entity,x=0,y=0,direction='north',belt_type=belt_type}}}
 command{parameter='{}'}
 if not response.ok then return nil end
 for _=1,2 do handlers[1]();game.tick=game.tick+1 end
 return storage.agent.jobs[request.id]
end
assert(not place('transport-belt','output') and stock==2)
assert(not place('underground-belt','invalid') and stock==2)
character.allowed=false;assert(place('underground-belt','output').status=='failed' and stock==2 and #created==0)
character.allowed=true;character.fail_create=true
assert(place('underground-belt','output').status=='failed' and stock==2)
character.fail_create=false
assert(place('underground-belt','input').status=='complete' and stock==1)
assert(created[#created].type=='input' and created[#created].direction==0)
assert(place('underground-belt','output').status=='complete' and stock==0)
assert(created[#created].type=='output')
assert(place('underground-belt','output').status=='failed' and stock==0)
print('Typed underground placement, native preflight, item costs and failed-placement refund passed')
