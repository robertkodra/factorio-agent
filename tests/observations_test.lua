-- Run the real fixed-command handlers with a tiny world containing a hidden
-- water tile. This catches accidental disclosure even when results are sorted.
local response, request, handler
defines={inventory={fuel=1,furnace_source=2,furnace_result=3,chest=4,
  assembling_machine_input=5,assembling_machine_output=6,turret_ammo=7},
  events={},controllers={},build_check_type={}}
script={active_mods={},on_init=function()end,on_configuration_changed=function()end,
  on_load=function()end,on_event=function()end}
commands={add_command=function(_,_,f)handler=f end}
rcon={print=function()end}
log=function()end
helpers={json_to_table=function()return request end,
  table_to_json=function(v)response=v;return '{}' end,write_file=function()end}
local surface={find_tiles_filtered=function(filter)
  assert(filter.collision_mask=='water_tile')
  return {{name='water',position={x=0,y=0}}, {name='water',position={x=32,y=0}}}
end,get_pollution=function(p)assert(p[1]==0);return 12 end}
local force={is_chunk_charted=function(_,p)return p[1]==0 and p[2]==0 end}
local character={valid=true,type='character',position={x=16,y=16},surface=surface,force=force,
  get_item_count=function()return 1 end,can_place_entity=function()return false end}
storage={agent={character=character}}
game={tick=10}
prototypes={entity={['stone-furnace']={collision_box={left_top={x=-0.7,y=-0.7},right_bottom={x=0.7,y=0.7}},tile_width=2,tile_height=2}},
  item={['stone-furnace']={place_result={name='stone-furnace'}}}}
package.path='mod/codex-controller/?.lua;'..package.path
dofile('mod/codex-controller/control.lua')
local function call(r)
  request=r;handler{parameter='{}'};return response
end
local s=call{op='survey',radius=64,limit=100}
assert(s.ok and #s.result.water==1 and s.result.water[1].x==0)
assert(#s.result.pollution==1 and s.result.pollution[1].amount==12)
for _,r in ipairs({{op='survey',radius=129},{op='survey',radius=0/0},
                   {op='survey',limit=101},{op='survey',limit=1.5}}) do assert(not call(r).ok) end
assert(call{op='placement',x=16,y=16,entity='stone-furnace'}.result.can_place==false)
assert(not call{op='placement',x=27,y=16,entity='stone-furnace'}.ok)
-- Within the local radius but with its conservative footprint crossing fog.
character.position.x=17
assert(not call{op='placement',x=27,y=16,entity='stone-furnace'}.ok)
assert(not call{op='placement',x=16,y=16,entity='small-biter'}.ok)
print('Charted survey and local placement boundaries passed')
