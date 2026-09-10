package.path='mod/codex-controller/?.lua;'..package.path
local m=require('manufacturing')
local force={};local friendly={valid=true,force=force,unit_number=5,name='pipe'}
local hostile={valid=true,force={},unit_number=9,name='hidden-pipe'}
local fb={{}}
fb.get_fluid_segment_id=function()return 7 end
fb.get_locked_fluid=function()return 'water' end
fb.get_pipe_connections=function()return{
 {position={x=0,y=0},target_position={x=1,y=0},target={owner=friendly},target_fluidbox_index=1},
 {position={x=0,y=0},target_position={x=0,y=1},target={owner=hostile},target_fluidbox_index=1}}
end
local rows=m.connections({fluidbox=fb},force)
assert(rows[1].segment_id==7 and rows[1].locked_fluid=='water')
assert(rows[1].connections[1].target_id==5)
assert(rows[1].connections[2].target_id==nil and rows[1].connections[2].target_name==nil)
prototypes={entity={['oil-refinery']={name='oil-refinery',type='assembling-machine',
 collision_box={},tile_width=5,tile_height=5,fluidbox_prototypes={{index=1,volume=100,
 production_type='input',filter={name='crude-oil'},pipe_connections={{connection_type='normal',
 flow_direction='input',direction=8,positions={{x=1,y=2}}}}}}}}}
local p=m.prototype('oil-refinery')
assert(p.tile_width==5 and p.fluid_boxes[1].filter=='crude-oil')
assert(p.fluid_boxes[1].connections[1].positions[1].y==2)
assert(not pcall(m.prototype,'nonexistent'))
print('Static geometry and owned-factory fluid connectivity boundaries passed')
