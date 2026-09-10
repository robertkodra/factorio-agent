-- Read-only geometry and fluid connectivity. Prototype data contains no world
-- observations. Connected targets are exposed only for the player's factory.
local M={}
function M.prototype(name)
 local p=prototypes.entity[name]
 if not p then error('unknown_entity_prototype') end
 local out={name=p.name,type=p.type,collision_box=p.collision_box,
   tile_width=p.tile_width,tile_height=p.tile_height,fluid_boxes={}}
 for _,b in pairs(p.fluidbox_prototypes or {}) do
  local row={index=b.index,production_type=b.production_type,volume=b.volume,
    filter=b.filter and b.filter.name,connections={}}
  for _,c in pairs(b.pipe_connections) do
   row.connections[#row.connections+1]={type=c.connection_type,flow=c.flow_direction,
     direction=c.direction,positions=c.positions,max_underground_distance=c.max_underground_distance}
  end
  out.fluid_boxes[#out.fluid_boxes+1]=row
 end
 if p.type=='electric-pole' then
  out.wire_distance=p.get_max_wire_distance();out.supply_distance=p.get_supply_area_distance()
 elseif p.type=='mining-drill' then out.mining_radius=p.get_mining_drill_radius();out.mining_speed=p.mining_speed end
 return out
end
function M.connections(entity,force)
 local rows={}
 for i=1,#entity.fluidbox do
  local row={index=i,segment_id=entity.fluidbox.get_fluid_segment_id(i),
    locked_fluid=entity.fluidbox.get_locked_fluid(i),connections={}}
  for _,c in pairs(entity.fluidbox.get_pipe_connections(i)) do
   local target=c.target and c.target.owner
   local v={type=c.connection_type,flow=c.flow_direction,position=c.position,target_position=c.target_position}
   if target and target.valid and target.force==force then
    v.target_id=target.unit_number;v.target_name=target.name;v.target_box=c.target_fluidbox_index
   end
   row.connections[#row.connections+1]=v
  end
  rows[#rows+1]=row
 end
 return rows
end
return M
