-- Experimental early-game bullet defense. Only writes normal character inputs.
-- Does not pathfind globally, grant equipment, change damage, or promise survival.
local M={}
local function d2(a,b)return (a.x-b.x)^2+(a.y-b.y)^2 end
local function visible(c,p)
  return c.force.is_chunk_visible(c.surface,{math.floor(p.x/32),math.floor(p.y/32)})
end
function M.stop(c)
  if c and c.valid then
    c.walking_state={walking=false}
    c.mining_state={mining=false}
    c.shooting_state={state=defines.shooting.not_shooting,position=c.position}
  end
end
function M.equipment(c)
  local guns=c.get_inventory(defines.inventory.character_guns)
  local ammo=c.get_inventory(defines.inventory.character_ammo)
  local slots={}
  if guns and ammo then
    for i=1,#guns do
      local g,a=guns[i],ammo[i]
      slots[#slots+1]={slot=i,gun=g.valid_for_read and g.name or nil,
        ammo=a and a.valid_for_read and a.name or nil,
        magazines=a and a.valid_for_read and a.count or 0,
        rounds=a and a.valid_for_read and a.ammo or 0}
    end
  end
  return {selected=c.selected_gun_index,slots=slots}
end
local function weapon(c)
  local guns=c.get_inventory(defines.inventory.character_guns)
  local ammo=c.get_inventory(defines.inventory.character_ammo)
  if not guns or not ammo then return false end
  local selected=nil
  for i=1,#guns do
    local g,a=guns[i],ammo[i]
    if g.valid_for_read and (g.name=='pistol' or g.name=='submachine-gun') and a and a.valid_for_read
       and (a.name=='firearm-magazine' or a.name=='piercing-rounds-magazine' or a.name=='uranium-rounds-magazine') then
      selected=i
      if g.name=='submachine-gun' then break end
    end
  end
  if selected then c.selected_gun_index=selected;return true end
  return false
end
function M.sample(c,tick)
  local all=c.surface.find_entities_filtered{position=c.position,radius=40,force='enemy',type={'unit','turret'}}
  local threats={}
  for _,e in pairs(all) do
    if e.valid and visible(c,e.position) then
      local range=e.prototype.attack_parameters and e.prototype.attack_parameters.range or 1
      local distance=math.sqrt(d2(c.position,e.position))
      if distance<=math.max(20,range+5) then
        threats[#threats+1]={entity=e,id=e.unit_number,name=e.name,position=e.position,
          distance=distance,range=range}
      end
    end
  end
  table.sort(threats,function(a,b)return a.distance<b.distance end)
  local summary={tick=tick,scope='currently_visible_chunks_within_40',radius=40,entities={},total=#threats,truncated=#threats>64}
  for i=1,math.min(#threats,64) do
    local e=threats[i];summary.entities[i]={id=e.id,name=e.name,position=e.position,distance=e.distance,range=e.range}
  end
  return threats,summary
end
local function escape(c,threats,rally)
  local best,best_score=nil,-math.huge
  for direction=0,14,2 do
    local angle=direction*math.pi/8
    local dx,dy=math.sin(angle),-math.cos(angle)
    local clear=true
    for _,distance in ipairs({0.75,1.5}) do
      local p={x=c.position.x+dx*distance,y=c.position.y+dy*distance}
      if not visible(c,p) or not c.surface.can_place_entity{name=c.name,position=p,force=c.force} then clear=false;break end
    end
    if clear then
      local p={x=c.position.x+dx*1.5,y=c.position.y+dy*1.5}
      local score=0
      for i=1,math.min(#threats,64) do
        local t=threats[i]
        -- Repel most strongly from nearby threats. This local heuristic does
        -- not establish a safe global escape route or model acid projectiles.
        score=score-100/(d2(p,t.position)+1)
      end
      if rally then score=score-.04*math.sqrt(d2(p,rally)) end
      if score>best_score then best_score=score;best=direction end
    end
  end
  if best then c.walking_state={walking=true,direction=best}
  else c.walking_state={walking=false} end
  return best
end
function M.update(c,g,tick,last_damage)
  if not g or not g.enabled then return false end
  if tick%3~=0 and not g.urgent then return g.active or false end
  g.urgent=false
  local threats,summary=M.sample(c,tick)
  g.observation=summary
  local damaged=last_damage and last_damage.actor_unit==c.unit_number and tick-last_damage.tick<=180
  local danger=#threats>0 or damaged or c.health<c.max_health*.5
  if danger then g.last_danger=tick end
  local active=danger or (g.active and tick-(g.last_danger or tick)<90)
  if not active then
    if g.active then M.stop(c) end
    g.active=false;g.mode='watching';return false
  end
  g.active=true;c.mining_state={mining=false}
  local target=nil
  if weapon(c) then
    for i=1,math.min(#threats,64) do
      local e=threats[i].entity
      if c.can_shoot(e,e.position) then target=e;break end
    end
  end
  c.shooting_state={state=target and defines.shooting.shooting_selected or defines.shooting.not_shooting,
    position=target and target.position or c.position}
  if target then c.selected=target end
  if #threats>0 or (g.rally and d2(c.position,g.rally)>4) then
    g.direction=escape(c,threats,g.rally)
  else c.walking_state={walking=false};g.direction=nil end
  g.mode=target and 'fighting' or 'escaping_or_waiting'
  return true
end
return M
