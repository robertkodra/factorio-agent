-- Bounded read of already observed infrastructure. No discovery or mutation.
local M={}
local function number(v,lo,hi)
 return type(v)=='number' and v==v and v>=lo and v<=hi
end
function M.read(req,c,tick,sequence,version,snapshot)
 for k,_ in pairs(req) do if k~='op' and k~='targets' then error('unknown_observation_field') end end
 if type(req.targets)~='table' or #req.targets<1 or #req.targets>64 then error('targets_must_be_1_to_64') end
 local ids={};local count=0
 for k,t in pairs(req.targets) do
  if type(k)~='number' or k%1~=0 or k<1 or k>#req.targets then error('targets_must_be_array') end
  count=count+1
  if type(t)~='table' then error('invalid_target') end
  for field,_ in pairs(t) do if field~='id' and field~='x' and field~='y' then error('unknown_target_field') end end
  if not number(t.id,1,4294967295) or t.id%1~=0 or ids[t.id] or
    not number(t.x,-1000000,1000000) or not number(t.y,-1000000,1000000) then error('invalid_target') end
  ids[t.id]=true
  if not c.force.is_chunk_charted(c.surface,{math.floor(t.x/32),math.floor(t.y/32)}) then error('target_not_charted') end
 end
 if count~=#req.targets then error('targets_must_be_array') end
 local out={tick=tick,sequence=sequence,actor_unit=c.unit_number,surface=c.surface.index,
   version=version,scope='owned_charted_requested_entities',entities={},missing={}}
 for _,t in ipairs(req.targets) do
  local found=nil
  -- Positional lookup also supports prototypes without get-by-unit-number.
  for _,e in pairs(c.surface.find_entities_filtered{position={t.x,t.y},radius=0.01,force=c.force}) do
   if e.valid and e.unit_number==t.id and e.force==c.force and e.surface==c.surface and e.type~='character' and
     c.force.is_chunk_charted(c.surface,{math.floor(e.position.x/32),math.floor(e.position.y/32)}) then
    found=e;break
   end
  end
  if found then
   local v=snapshot(found,c.force,c.surface)
   if found.type=='furnace' and found.get_recipe then
    local recipe=found.get_recipe();v.recipe=recipe and recipe.name
   end
   local burner=found.burner
   if burner then v.burner={remaining_energy=burner.remaining_burning_fuel,
     item=burner.currently_burning and burner.currently_burning.name.name} end
   -- Fluid-neighbour geometry is outside this smelting observation contract.
   v.fluid_boxes=nil
   if v.neighbour_id then
    local n=found.neighbours
    if not n or not n.valid or not c.force.is_chunk_charted(c.surface,
       {math.floor(n.position.x/32),math.floor(n.position.y/32)}) then v.neighbour_id=nil end
   end
   out.entities[#out.entities+1]=v
  else out.missing[#out.missing+1]=t.id end
 end
 return out
end
return M
