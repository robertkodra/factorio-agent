-- Exercise the actual action executor: queue through the player adapter and
-- retain ownership after the queue becomes empty, without fabricating a craft.
local response, request, handler, queued= nil,nil,nil,0
local handlers={}
defines={inventory={},events={on_tick=1,on_player_crafted_item=2},controllers={character=1,spectator=5},build_check_type={}}
script={active_mods={base='2.0.77',['codex-controller']='0.3.1'},
  on_init=function()end,on_configuration_changed=function()end,on_load=function()end,
  on_event=function(id,f)if id then handlers[id]=f end end}
commands={add_command=function(_,_,f)handler=f end}
rcon={print=function()end};log=function()end
helpers={json_to_table=function()return request end,table_to_json=function(v)response=v;return '{}' end,write_file=function()end}
local character={valid=true,type='character',position={x=0,y=0},crafting_queue_size=0,
  force={recipes={lab={enabled=true}}},walking_state={walking=false},
  begin_crafting=function()error('Must use normal player crafting adapter')end}
local player
player={connected=true,index=1,cheat_mode=false,controller_type=1,
  get_craftable_count=function()return 1 end,
  begin_crafting=function(p)queued=queued+p.count;character.crafting_queue_size=p.count;return p.count end,
  set_controller=function(p)assert(p.type==1);character.player=player end}
character.player=nil
storage={agent={character=character,owner=1,jobs={},order={},events={},sequence=0}}
game={tick=1,speed=1,get_player=function()return player end}
prototypes={recipe={lab={}}}
package.path='mod/codex-controller/?.lua;'..package.path
dofile('mod/codex-controller/control.lua')
request={op='submit',id='craft-test',actions={{type='craft',recipe='lab',count=1},{type='await_craft'}}}
handler{parameter='{}'};assert(response.ok)
handlers[1]();assert(queued==1 and character.player==player)
game.tick=2;character.crafting_queue_size=0;handlers[1]()
assert(character.player==player, 'Queue completion must not detach the player')
-- Recording a native completion event does not create items or grant research.
handlers[2]{player_index=1,recipe={name='lab'},item_stack={name='lab',count=1}}
local events=storage.agent.events
assert(events[#events].kind=='player_crafted' and events[#events].detail.item=='lab')
assert(queued==1)
print('Player crafting ownership and completion recording passed')
