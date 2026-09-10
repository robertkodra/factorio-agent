-- Read-only combat evidence. Never expose a currently hidden attacker's location.
local M = {}
local function visible(entity, observer)
  if not entity or not entity.valid then return nil end
  local p = entity.position
  if not observer.force.is_chunk_visible(entity.surface,
      {math.floor(p.x / 32), math.floor(p.y / 32)}) then
    return {visible=false}
  end
  return {visible=true,name=entity.name,type=entity.type,
          position={x=p.x,y=p.y},force=entity.force and entity.force.name}
end

function M.record(e, character, kind)
  if not character or not character.valid or e.entity ~= character then return nil end
  local p = character.position
  return {kind=kind,tick=e.tick,actor_unit=character.unit_number,
          position={x=p.x,y=p.y},health=e.final_health,
          damage=e.final_damage_amount,
          damage_type=e.damage_type and e.damage_type.name,
          cause=visible(e.cause,character),source=visible(e.source,character)}
end

return M
