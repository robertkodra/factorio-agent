local VERSION = '0.7.0'
local navigation = require('navigation')
local combat_observation = require('combat_observation')
local reflex = require('reflex')
local transfer = require('transfer')
local manufacturing = require('manufacturing')
local job_history = require('job_history')
local resumed = false
local DIR = {north=0,northeast=2,east=4,southeast=6,south=8,southwest=10,west=12,northwest=14}
local INV = {fuel=defines.inventory.fuel,source=defines.inventory.furnace_source,result=defines.inventory.furnace_result,chest=defines.inventory.chest,input=defines.inventory.assembling_machine_input,output=defines.inventory.assembling_machine_output,ammo=defines.inventory.turret_ammo}
local TYPES = {walk=true,mine=true,craft=true,await_craft=true,place=true,put=true,take=true,wait_inventory=true,research=true,set_recipe=true,rotate=true,wait_ticks=true,launch=true}
local FIELDS = {type=true,x=true,y=true,count=true,item=true,recipe=true,entity=true,direction=true,belt_type=true,inventory=true,player_inventory=true,tolerance=true,timeout=true,ticks=true,technology=true}
local function state()
  storage.agent = storage.agent or {version=VERSION,jobs={},order={},events={},sequence=0,follow=true,pauses=0}
  return storage.agent
end
local function integer(x,lo,hi) return type(x)=='number' and x==math.floor(x) and x>=lo and x<=hi end
local function coordinate(x) return type(x)=='number' and x==x and math.abs(x)<=1000000 end
local function named(x) return type(x)=='string' and #x>0 and #x<=120 and x:match('^[%w_%-]+$') end
local function event(kind,detail)
  local s=state();s.sequence=s.sequence+1
  local e={seq=s.sequence,tick=game.tick,kind=kind,job=s.current,detail=detail}
  s.events[#s.events+1]=e
  if #s.events>2048 then table.remove(s.events,1) end
  helpers.write_file('codex-controller/events.jsonl',helpers.table_to_json(e)..'\n',true)
end
local function actor()
  local c=state().character
  if not c or not c.valid or c.type~='character' then error('no_bound_character') end
  return c
end
local function check_rules(player)
  if game.speed~=1 then error('policy_requires_normal_game_speed') end
  if player and player.cheat_mode then error('policy_rejects_cheat_mode') end
  for name,_ in pairs(script.active_mods) do
    if name~='base' and name~='codex-controller' then error('policy_rejects_extra_mod_'..name) end
  end
end
local function stop(c)
  if c and c.valid then
    c.walking_state={walking=false}
    c.mining_state={mining=false}
    if defines.shooting then c.shooting_state={state=defines.shooting.not_shooting,position=c.position} end
  end
end
local function finish(j,status,reason)
  local s=state();stop(s.character)
  j.status=status;j.error=reason;j.finished_tick=game.tick;j.runtime=nil
  event(status,{index=j.index,error=reason,metrics=j.metrics})
end
local function next_step(j,detail)
  local c=actor();local a=j.actions[j.index]
  if a.type=='walk' then c.walking_state={walking=false} end
  if a.type=='mine' then c.mining_state={mining=false} end
  event('step_complete',{index=j.index,action=a.type,result=detail})
  j.index=j.index+1;j.runtime=nil
end
local function entity_at(c,a)
  local filter={position={a.x,a.y},radius=0.15}
  if a.entity then filter.name=a.entity end
  local es=c.surface.find_entities_filtered(filter)
  table.sort(es,function(x,y) return x.type~='resource' and y.type=='resource' end)
  for _,e in ipairs(es) do if e~=c then return e end end
  error('entity_not_found')
end
local function close_to(c,e)
  if not c.can_reach_entity(e) then error('out_of_reach') end
end
local function inventory(e,name)
  if name=='ammo' and e.type~='ammo-turret' then error('ammo_requires_ammo_turret') end
  local idx=INV[name or 'chest']
  if name=='fuel' then
    local fuel=e.get_fuel_inventory()
    if not fuel then error('entity_has_no_fuel_inventory') end
    return fuel
  elseif name=='input' then
    if e.type=='lab' then idx=defines.inventory.lab_input
    elseif e.type=='furnace' then idx=defines.inventory.furnace_source
    elseif e.type=='rocket-silo' then idx=defines.inventory.rocket_silo_input
    elseif e.type~='assembling-machine' then error('entity_has_no_input_inventory') end
  elseif name=='output' then
    local output=e.get_output_inventory()
    if not output then error('entity_has_no_output_inventory') end
    return output
  end
  local inv=e.get_inventory(idx)
  if not inv then error('invalid_inventory_for_entity') end
  return inv
end
local function validate(actions)
  if type(actions)~='table' or #actions<1 or #actions>512 then error('actions_must_have_1_to_512_entries') end
  for key,_ in pairs(actions) do if not integer(key,1,#actions) then error('actions_must_be_array') end end
  local out={}
  for i,a in ipairs(actions) do
    if type(a)~='table' or not TYPES[a.type] then error('invalid_action_'..i) end
    for k,_ in pairs(a) do if not FIELDS[k] then error('unknown_action_field_'..tostring(k)) end end
    local b={};for k,v in pairs(a) do b[k]=v end
    if b.timeout~=nil and not integer(b.timeout,1,216000) then error('invalid_timeout') end
    b.timeout=b.timeout or 3600
    if a.type=='walk' or a.type=='mine' or a.type=='place' or a.type=='put' or a.type=='take' or a.type=='set_recipe' or a.type=='rotate' or a.type=='launch' or (a.type=='wait_inventory' and (a.x~=nil or a.y~=nil)) then
      if not coordinate(a.x) or not coordinate(a.y) then error('invalid_coordinates') end
    end
    if a.type=='walk' then
      b.tolerance=b.tolerance or 0.35
      if type(b.tolerance)~='number' or b.tolerance<0.1 or b.tolerance>10 then error('invalid_tolerance') end
    end
    if a.type=='mine' or a.type=='craft' or a.type=='put' or a.type=='take' or a.type=='wait_inventory' then
      if not integer(a.count,1,100000) then error('invalid_count') end
    end
    if a.type=='put' or a.type=='take' or a.type=='wait_inventory' then
      if not named(a.item) or not prototypes.item[a.item] then error('invalid_item') end
      if a.inventory and not INV[a.inventory] then error('invalid_inventory') end
    end
    if a.player_inventory~=nil and ((a.type~='put' and a.type~='take') or (a.player_inventory~='main' and a.player_inventory~='ammo')) then error('invalid_player_inventory') end
    if a.belt_type~=nil and (a.type~='place' or not prototypes.entity[a.entity] or
      prototypes.entity[a.entity].type~='underground-belt' or
      (a.belt_type~='input' and a.belt_type~='output')) then error('invalid_belt_type') end
    if a.type=='craft' or a.type=='set_recipe' then
      if not named(a.recipe) or not prototypes.recipe[a.recipe] then error('invalid_recipe') end
    end
    if a.type=='place' then
      if not named(a.entity) or not prototypes.entity[a.entity] then error('invalid_entity') end
      b.item=b.item or a.entity
      if not prototypes.item[b.item] or not prototypes.item[b.item].place_result or prototypes.item[b.item].place_result.name~=a.entity then error('invalid_placement_item') end
      if a.direction~=nil and not DIR[a.direction] then error('invalid_direction') end
      b.direction=b.direction or 'north'
    end
    if a.type=='research' and not named(a.technology) then error('invalid_technology') end
    if a.type=='launch' and a.entity~='rocket-silo' then error('launch_requires_silo_name') end
    if a.type=='wait_ticks' and not integer(a.ticks,1,216000) then error('invalid_ticks') end
    out[i]=b
  end
  return out
end
local function fingerprint(actions)
  local parts={}
  for _,a in ipairs(actions) do
    local keys={};for k,_ in pairs(a) do keys[#keys+1]=k end;table.sort(keys)
    local values={};for _,k in ipairs(keys) do values[#values+1]=helpers.table_to_json({k}):sub(2,-2)..':'..helpers.table_to_json({a[k]}):sub(2,-2) end
    parts[#parts+1]='{'..table.concat(values,',')..'}'
  end
  return '['..table.concat(parts,',')..']'
end
local function request_path(c,a,r)
  c.walking_state={walking=false}
  r.path=nil;r.ready=false;r.segment=1;r.progress_tick=nil;r.last_move_tick=game.tick;r.last_position=c.position
  r.path_id=c.surface.request_path{bounding_box=c.prototype.collision_box,collision_mask=c.prototype.collision_mask,start=c.position,goal={a.x,a.y},force=c.force,radius=a.tolerance,entity_to_ignore=c,pathfind_flags={prefer_straight_paths=true,no_break=true}}
  if not r.path_id then error('path_request_failed') end
end
local function start_step(c,j,a)
  local r={started_tick=game.tick};j.runtime=r
  event('step_started',{index=j.index,action=a.type})
  if a.type=='walk' then
    request_path(c,a,r);r.last_move_tick=game.tick;r.last_position=c.position;r.repaths=0
  elseif a.type=='mine' then
    local e=entity_at(c,a);close_to(c,e)
    local props=e.prototype.mineable_properties
    if not props.minable or not props.products or #props.products==0 then error('entity_not_mineable') end
    local item=a.item or props.products[1].name
    if not prototypes.item[item] then error('mining_product_not_item') end
    local produces=false;for _,p in pairs(props.products) do if p.name==item and p.type=='item' then produces=true end end
    if not produces then error('invalid_mining_product') end
    r.target=e;r.item=item;r.initial=c.get_item_count(item)
  elseif a.type=='craft' then
    if not c.force.recipes[a.recipe].enabled then error('recipe_locked') end
    -- Player-less character crafts do not update force production statistics or
    -- craft-item research triggers. Keep normal ownership through completion.
    if not c.player then
      local owner=game.get_player(state().owner)
      if not owner or not owner.connected then error('crafting_requires_viewer') end
      owner.set_controller{type=defines.controllers.character,character=c}
      event('craft_player_attached')
    end
    -- Use the player adapter, not LuaEntity's character adapter, so normal
    -- player crafting events and technology triggers are processed by the game.
    if c.player.get_craftable_count(a.recipe)<a.count then error('insufficient_materials') end
    local n=c.player.begin_crafting{recipe=a.recipe,count=a.count}
    if n~=a.count then error('craft_queue_rejected') end
    next_step(j,{queued=n});return
  elseif a.type=='place' then
    local pos={a.x,a.y};local dir=DIR[a.direction]
    if c.get_item_count(a.item)<1 then error('missing_item') end
    if not c.can_place_entity{name=a.entity,position=pos,direction=dir} then error('placement_rejected') end
    local removed=c.remove_item{name=a.item,count=1}
    if removed~=1 then error('inventory_changed') end
    local ok,e=pcall(function() return c.surface.create_entity{name=a.entity,position=pos,direction=dir,type=a.belt_type,force=c.force,raise_built=true,build_check_type=defines.build_check_type.manual} end)
    if not ok or not e then c.insert{name=a.item,count=1};error('placement_failed') end
    j.metrics.placed=(j.metrics.placed or 0)+1
    next_step(j,{entity=e.name,position=e.position});return
  elseif a.type=='put' or a.type=='take' then
    local e=entity_at(c,a);close_to(c,e)
    local own=a.player_inventory=='ammo' and c.get_inventory(defines.inventory.character_ammo) or c.get_main_inventory();local other=inventory(e,a.inventory)
    local src=a.type=='put' and own or other;local dst=a.type=='put' and other or own
    local added=transfer.move(src,dst,a.item,a.count)
    next_step(j,{entity=e.name,item=a.item,count=added});return
  elseif a.type=='launch' then
    local e=entity_at(c,a);close_to(c,e)
    if e.type~='rocket-silo' or e.force~=c.force then error('launch_requires_owned_silo') end
    if not e.launch_rocket() then error('rocket_not_ready') end
    next_step(j,{launch_ordered=true,silo=e.unit_number});return
  elseif a.type=='research' then
    if not c.force.add_research(a.technology) then error('research_unavailable') end
    next_step(j);return
  elseif a.type=='set_recipe' then
    local e=entity_at(c,a);close_to(c,e)
    if not c.force.recipes[a.recipe] or not c.force.recipes[a.recipe].enabled then error('recipe_locked') end
    local input=e.get_inventory(defines.inventory.assembling_machine_input)
    local output=e.get_output_inventory()
    if (input and not input.is_empty()) or (output and not output.is_empty()) or e.is_crafting() then error('empty_machine_before_recipe_change') end
    e.set_recipe(a.recipe);next_step(j);return
  elseif a.type=='rotate' then
    local e=entity_at(c,a);close_to(c,e)
    if not e.rotate() then error('rotation_rejected') end
    next_step(j);return
  end
end
local function step(c,j,a,r)
  if game.tick-r.started_tick>a.timeout then error('step_timeout') end
  if a.type=='walk' then
    local pos=c.position;local dx=a.x-pos.x;local dy=a.y-pos.y
    if dx*dx+dy*dy<=a.tolerance*a.tolerance then next_step(j,{position=pos});return end
    if not r.ready then return end
    if not r.path then
      if r.busy and (r.repaths or 0)<3 then r.repaths=(r.repaths or 0)+1;request_path(c,a,r);return end
      error('no_path')
    end
    while r.segment<#r.path do
      local q=r.path[r.segment].position;local n=r.path[r.segment+1].position
      local vx=n.x-q.x;local vy=n.y-q.y
      local near=(pos.x-n.x)^2+(pos.y-n.y)^2<0.04
      if near or (pos.x-q.x)*vx+(pos.y-q.y)*vy>=vx*vx+vy*vy then r.segment=r.segment+1 else break end
    end
    local t=r.segment<#r.path and r.path[r.segment+1].position or {x=a.x,y=a.y}
    local distance=math.sqrt((t.x-pos.x)^2+(t.y-pos.y)^2)
    if not navigation.progress(r,r.segment,distance,game.tick) then
      if r.repaths>=2 then error('no_path_progress') end
      r.repaths=r.repaths+1
      event('navigation_repath',{index=j.index,reason='no_path_progress',attempt=r.repaths,position=pos})
      request_path(c,a,r);return
    end
    local angle=math.atan2(t.x-pos.x,pos.y-t.y)
    local dir=(math.floor(angle/(math.pi/4)+0.5)*2)%16
    c.walking_state={walking=true,direction=dir}
    if (pos.x-r.last_position.x)^2+(pos.y-r.last_position.y)^2>0.0025 then r.last_position={x=pos.x,y=pos.y};r.last_move_tick=game.tick end
    if game.tick-r.last_move_tick>120 then
      if r.repaths>=2 then error('stuck') end
      r.repaths=r.repaths+1;r.last_move_tick=game.tick;request_path(c,a,r)
    end
  elseif a.type=='mine' then
    local gained=c.get_item_count(r.item)-r.initial
    if gained>=a.count then next_step(j,{item=r.item,mined=gained});return end
    if not r.target.valid then error('target_depleted_before_count') end
    close_to(c,r.target)
    c.mining_state={mining=true,position=r.target.position}
    c.selected=r.target -- Position-based selection can choose overlapping trees.
  elseif a.type=='await_craft' then
    if c.crafting_queue_size==0 then next_step(j) end
  elseif a.type=='wait_inventory' then
    local inv=c.get_main_inventory()
    if a.x~=nil then local e=entity_at(c,a);close_to(c,e);inv=inventory(e,a.inventory) end
    local n=inv.get_item_count(a.item)
    if n>=a.count then next_step(j,{count=n}) end
  elseif a.type=='wait_ticks' then
    if game.tick-r.started_tick>=a.ticks then next_step(j) end
  end
end
local function tick()
  local s=state();local c=s.character
  if not c or not c.valid then
    if s.guard then s.guard.enabled=false;s.guard.active=false end
    if s.current and s.jobs[s.current].status=='running' then finish(s.jobs[s.current],'failed','character_lost') end
    resumed=false
    return
  end
  local owner=game.get_player(s.owner)
  -- Retain player ownership after crafting; detaching at an empty queue can
  -- interfere with the engine's completion/trigger accounting.
  if owner and owner.connected and s.follow and owner.controller_type==defines.controllers.spectator then
    owner.teleport(c.position,c.surface) -- Camera only. Never teleports the engineer.
  end
  local j=s.current and s.jobs[s.current]
  local defending=false
  if s.guard and s.guard.enabled then
    local was_active=s.guard.active
    local ok,active=pcall(function()
      check_rules(owner)
      return reflex.update(c,s.guard,game.tick,s.last_damage)
    end)
    if not ok then
      s.guard.enabled=false;reflex.stop(c)
      if j and j.status=='running' then finish(j,'failed','reflex_error') end
      event('reflex_error',{error=tostring(active)});return
    end
    if active then
      if not was_active then event('reflex_started',{mode=s.guard.mode}) end
      if j and j.status=='running' then
        -- Preserve the completed steps and stop the remaining batch. The caller
        -- must revalidate a new plan after combat, never replay old actions.
        finish(j,'cancelled','defense_interrupt')
        s.guard.urgent=true;reflex.update(c,s.guard,game.tick,s.last_damage)
      end
      defending=true
    elseif was_active then event('reflex_clear') end
  end
  if owner and owner.connected and game.tick%6==0 then
    local panel=owner.gui.left.codex_agent_panel
    if not panel then
      panel=owner.gui.left.add{type='frame',name='codex_agent_panel',caption='Codex controller',direction='vertical'}
      panel.add{type='label',name='job',caption='Idle'}
      panel.add{type='label',name='activity',caption=''}
      panel.add{type='progressbar',name='mining',value=0}.style.width=260
      panel.add{type='button',name='codex_agent_stop',caption='Stop job'}
    end
    panel.job.caption=j and (j.id..': '..j.status..' ('..math.min(j.index,#j.actions)..'/'..#j.actions..')') or 'Idle'
    local action=j and j.status=='running' and j.actions[j.index]
    panel.activity.caption=(action and action.type or 'Waiting')..' | Coal '..c.get_item_count('coal')..' | Belts '..c.get_item_count('transport-belt')
    panel.mining.value=c.character_mining_progress
  end
  if defending then return end
  if not j or j.status~='running' then resumed=false;return end
  if resumed then
    resumed=false
    if j.runtime and j.actions[j.index].type=='walk' then request_path(c,j.actions[j.index],j.runtime) end
    event('resumed_after_load',{index=j.index})
  end
  local pos=c.position
  if j.last_position then
    local d=math.sqrt((pos.x-j.last_position.x)^2+(pos.y-j.last_position.y)^2)
    j.metrics.max_step=math.max(j.metrics.max_step or 0,d)
  end
  j.last_position={x=pos.x,y=pos.y};j.metrics.ticks=j.metrics.ticks+1
  if c.walking_state.walking and c.crafting_queue_size>0 then j.metrics.walk_craft_overlap_ticks=(j.metrics.walk_craft_overlap_ticks or 0)+1 end
  local a=j.actions[j.index]
  if not a then finish(j,'complete');return end
  local ok,err=pcall(function()
    check_rules(owner)
    if not j.runtime then start_step(c,j,a) end
    if j.runtime then step(c,j,a,j.runtime) end
  end)
  if not ok then finish(j,'failed',tostring(err)) end
end
local function job_status(j)
  if not j then return {status='idle'} end
  return {id=j.id,status=j.status,index=j.index,total=j.total or #j.actions,action=j.archived and j.action or (j.actions and j.actions[j.index] and j.actions[j.index].type),started_tick=j.started_tick,finished_tick=j.finished_tick,error=j.error,metrics=j.metrics}
end
local function snapshot()
  local s=state();local c=actor();local owner=game.get_player(s.owner)
  return {version=VERSION,tick=game.tick,speed=game.speed,paused=game.tick_paused,mods=script.active_mods,position=c.position,health=c.health,max_health=c.max_health,inventory=c.get_main_inventory().get_contents(),ammo=c.get_inventory(defines.inventory.character_ammo).get_contents(),crafting=c.crafting_queue or {},walking=c.walking_state,mining=c.mining_state.mining,actor_unit=c.unit_number,actor_has_player=c.player~=nil,viewer_controller=owner and owner.controller_type,job=job_status(s.current and s.jobs[s.current]),sequence=s.sequence,pauses=s.pauses,policy='no-console-lua-v1',guard=s.guard,guns=defines.inventory.character_guns and reflex.equipment(c) or nil}
end
local function factory_snapshot()
local c=actor();local f=c.force;local s=c.surface;
local o={tick=game.tick,speed=game.speed,paused=game.tick_paused,entities={},researched={},
launches=state().launches or {},research_events=state().research_events or {},
research=f.current_research and f.current_research.name,progress=f.research_progress,produced={}};
for n,t in pairs(f.technologies)do if t.researched then table.insert(o.researched,n)end end;
table.sort(o.researched);
for _,e in pairs(s.find_entities_filtered{force=f})do
 local v={id=e.unit_number,name=e.name,type=e.type,position=e.position,direction=e.direction,status=e.status,
 health=e.health,max_health=e.max_health,energy=e.energy,box=e.bounding_box};
 if defines.entity_status then for name,value in pairs(defines.entity_status)do if value==e.status then v.status_name=name;break end end end;
 v.electric_network_id=e.electric_network_id;
 v.fluid_boxes=manufacturing.connections(e,f);
 if e.type=='mining-drill' then
  v.drop=e.drop_position;local target=e.mining_target;
  if target and target.valid and f.is_chunk_charted(s,{math.floor(target.position.x/32),math.floor(target.position.y/32)}) then
   v.mining_target={name=target.name,position=target.position,amount=target.amount};
  end;
 end;
 v.fluids={};for i=1,#e.fluidbox do local fluid=e.fluidbox[i];if fluid then v.fluids[#v.fluids+1]={index=i,name=fluid.name,amount=fluid.amount,temperature=fluid.temperature}end end;
 local fuel=e.get_fuel_inventory();if fuel then v.fuel=fuel.get_contents()end;
 if e.type=='ammo-turret' then
  local ammo=e.get_inventory(defines.inventory.turret_ammo);v.ammo=ammo.get_contents();v.ammo_stacks={};
  for i=1,#ammo do local a=ammo[i];if a.valid_for_read then v.ammo_stacks[#v.ammo_stacks+1]={slot=i,name=a.name,count=a.count,rounds=a.ammo}end end;
 end;
 local input=nil;
 if e.type=='container' or e.type=='logistic-container' then v.chest=e.get_inventory(defines.inventory.chest).get_contents()end;
 if e.type=='assembling-machine' or e.type=='rocket-silo' then
  local recipe=e.get_recipe();v.recipe=recipe and recipe.name;
  input=e.get_inventory(e.type=='rocket-silo' and defines.inventory.rocket_silo_input or defines.inventory.assembling_machine_input);
 elseif e.type=='furnace' then input=e.get_inventory(defines.inventory.furnace_source);
 elseif e.type=='lab' then input=e.get_inventory(defines.inventory.lab_input);end;
 if input then v.input=input.get_contents()end;
 if e.type=='assembling-machine' or e.type=='furnace' or e.type=='rocket-silo' then
  v.products_finished=e.products_finished;v.crafting=e.is_crafting();
  local output=e.get_output_inventory();if output then v.output=output.get_contents()end;
 end;
 if e.type=='rocket-silo' then v.rocket_parts=e.rocket_parts;v.rocket_parts_required=e.prototype.rocket_parts_required;v.rocket_silo_status=e.rocket_silo_status end;
 if e.type=='inserter' then v.pickup=e.pickup_position;v.drop=e.drop_position;end;
 if e.type=='transport-belt' or e.type=='underground-belt' then
  v.lines={e.get_transport_line(1).get_contents(),e.get_transport_line(2).get_contents()};
  if e.type=='underground-belt' then
   v.belt_type=e.belt_to_ground_type;local n=e.neighbours;
   if n and n.valid and n.force==f then v.neighbour_id=n.unit_number end;
  end;
 end;
 table.insert(o.entities,v);
end;
local stats=f.get_item_production_statistics(s);
for _,n in pairs({'lab','firearm-magazine','iron-plate','copper-plate','automation-science-pack','logistic-science-pack',
'military-science-pack','chemical-science-pack','production-science-pack','utility-science-pack','rocket-part','rocket-silo','construction-robot','logistic-robot'})do
 o.produced[n]=stats.get_input_count(n);end;
return o
end
local function research_snapshot()
local c=actor();local f=c.force;local out={tick=game.tick,researched={},produced={},enabled_recipes={}};
for n,t in pairs(f.technologies)do if t.researched then out.researched[#out.researched+1]=n end end;
table.sort(out.researched);
for n,r in pairs(f.recipes)do if r.enabled then out.enabled_recipes[#out.enabled_recipes+1]=n end end;
table.sort(out.enabled_recipes);
local stats=f.get_item_production_statistics(c.surface);
for _,n in pairs({'lab','firearm-magazine','iron-plate','copper-plate','automation-science-pack','logistic-science-pack','military-science-pack','chemical-science-pack','construction-robot','logistic-robot'})do out.produced[n]=stats.get_input_count(n)end;
return out
end
local function handle(req)
  if type(req)~='table' then error('request_must_be_object') end
  local s=state();local op=req.op
  if op=='hello' then return {version=VERSION,commands={'prototype','bind','release','submit','status','observe','scan','survey','placement','inspect','factory','research_state','guard','cancel','pause','save'},actions=TYPES} end
  if op=='prototype' then
    for k,_ in pairs(req) do if k~='op' and k~='entity' then error('unknown_prototype_field') end end
    if not named(req.entity) then error('invalid_entity_name') end
    return manufacturing.prototype(req.entity)
  end
  if op=='bind' then
    if s.character and s.character.valid then check_rules(game.get_player(s.owner));return snapshot() end
    local p=game.get_player(req.player or 1)
    if not p or not p.connected or not p.character then error('active_character_required') end
    check_rules(p)
    if p.cheat_mode then error('cheat_mode_not_supported') end
    local c=p.character;stop(c)
    s.character=c;s.owner=p.index;s.guard=nil
    p.character=nil;p.set_controller{type=defines.controllers.spectator}
    event('bound',{owner=p.index,unit=c.unit_number,inventory=c.get_main_inventory().get_contents(),position=c.position})
    return snapshot()
  elseif op=='release' then
    local c=actor();local p=game.get_player(s.owner)
    if s.current and s.jobs[s.current].status=='running' then finish(s.jobs[s.current],'cancelled','released') end
    s.guard=nil;stop(c);p.set_controller{type=defines.controllers.character,character=c};s.character=nil
    if p.gui.left.codex_agent_panel then p.gui.left.codex_agent_panel.destroy() end
    event('released');return {released=true}
  elseif op=='observe' then return snapshot()
  elseif op=='factory' then return factory_snapshot()
  elseif op=='research_state' then return research_snapshot()
  elseif op=='guard' then
    local c=actor();check_rules(game.get_player(s.owner))
    for k,_ in pairs(req) do if k~='op' and k~='enabled' and k~='rally' then error('unknown_guard_field') end end
    if type(req.enabled)~='boolean' then error('guard_enabled_boolean_required') end
    if req.rally then
      if type(req.rally)~='table' or not coordinate(req.rally.x) or not coordinate(req.rally.y) then error('invalid_rally') end
      for k,_ in pairs(req.rally) do if k~='x' and k~='y' then error('unknown_rally_field') end end
      if (req.rally.x-c.position.x)^2+(req.rally.y-c.position.y)^2>4096 or
        not c.force.is_chunk_charted(c.surface,{math.floor(req.rally.x/32),math.floor(req.rally.y/32)}) then error('rally_must_be_nearby_and_charted') end
    end
    if s.guard and s.guard.active then stop(c) end
    s.guard={enabled=req.enabled,active=false,urgent=true,rally=req.rally,mode='watching'}
    event('guard_configured',{enabled=req.enabled,rally=req.rally});return s.guard
  elseif op=='status' then
    if req.id and not job_history.find(s,req.id) then error('unknown_job_id') end
    local j=req.id and job_history.find(s,req.id) or (s.current and s.jobs[s.current]);local out=job_status(j);out.tick=game.tick;out.sequence=s.sequence;out.events={};out.last_damage=s.last_damage;out.last_death=s.last_death
    local after=req.after or s.sequence
    if not integer(after,0,s.sequence) then error('invalid_cursor') end
    out.oldest_sequence=s.events[1] and s.events[1].seq or s.sequence+1
    out.events_lost=after<out.oldest_sequence-1
    out.guard=s.guard
    for _,e in ipairs(s.events) do if e.seq>after and #out.events<100 then out.events[#out.events+1]=e end end
    return out
  elseif op=='submit' then
    actor()
    check_rules(game.get_player(s.owner))
    if not named(req.id) then error('valid_id_required') end
    local actions=validate(req.actions);local signature=fingerprint(actions)
    local previous=job_history.find(s,req.id)
    if previous then
      if (previous.fingerprint or fingerprint(previous.actions))~=signature then error('id_conflict') end
      return job_status(previous)
    end
    if s.guard and s.guard.active then error('defense_active_revalidate_after_clear') end
    if s.current and s.jobs[s.current].status=='running' then error('busy') end
    job_history.make_room(s)
    local j={id=req.id,actions=actions,fingerprint=signature,index=1,status='running',started_tick=game.tick,metrics={ticks=0,max_step=0}}
    s.jobs[req.id]=j;s.order[#s.order+1]=req.id;s.current=req.id
    event('submitted',{id=req.id,actions=actions});return job_status(j)
  elseif op=='cancel' then
    local j=s.current and s.jobs[s.current]
    if req.id and (not j or req.id~=j.id) then error('job_id_mismatch') end
    if j and j.status=='running' then finish(j,'cancelled','requested') end
    if s.guard then s.guard.enabled=false;s.guard.active=false;stop(s.character) end
    return job_status(j)
  elseif op=='pause' then
    if type(req.value)~='boolean' then error('boolean_required') end
    if game.tick_paused~=req.value then s.pauses=s.pauses+1;event('pause',{value=req.value}) end
    game.tick_paused=req.value;return {paused=game.tick_paused,tick=game.tick}
  elseif op=='save' then
    if not named(req.name) then error('invalid_save_name') end
    game.server_save(req.name);event('save_requested',{name=req.name});return {requested=req.name,tick=game.tick}
  elseif op=='survey' then
    local c=actor();local radius=req.radius or 64;local limit=req.limit or 100
    if type(radius)~='number' or radius~=radius or radius<1 or radius>128 then error('radius_must_be_1_to_128') end
    if not integer(limit,1,100) then error('limit_must_be_1_to_100') end
    local water={};local pollution={}
    local function charted(x,y) return c.force.is_chunk_charted(c.surface,{math.floor(x/32),math.floor(y/32)}) end
    for _,t in pairs(c.surface.find_tiles_filtered{position=c.position,radius=radius,collision_mask='water_tile'}) do
      local p=t.position
      if charted(p.x,p.y) then water[#water+1]={name=t.name,x=p.x,y=p.y,distance=math.sqrt((p.x+0.5-c.position.x)^2+(p.y+0.5-c.position.y)^2)} end
    end
    table.sort(water,function(a,b) if a.distance~=b.distance then return a.distance<b.distance end;if a.x~=b.x then return a.x<b.x end;return a.y<b.y end)
    local total=#water;while #water>limit do water[#water]=nil end
    for x=math.floor((c.position.x-radius)/32),math.floor((c.position.x+radius)/32) do
      for y=math.floor((c.position.y-radius)/32),math.floor((c.position.y+radius)/32) do
        local px=math.max(x*32,math.min(c.position.x,x*32+32));local py=math.max(y*32,math.min(c.position.y,y*32+32))
        if (px-c.position.x)^2+(py-c.position.y)^2<=radius^2 and c.force.is_chunk_charted(c.surface,{x,y}) then
          pollution[#pollution+1]={x=x,y=y,amount=c.surface.get_pollution({x*32,y*32})}
        end
      end
    end
    return {tick=game.tick,water=water,water_total=total,pollution=pollution,radius=radius,scope='charted_chunks_near_engineer'}
  elseif op=='placement' then
    local c=actor()
    if not coordinate(req.x) or not coordinate(req.y) or not named(req.entity) then error('invalid_placement_query') end
    local p=prototypes.entity[req.entity];local item=prototypes.item[req.entity]
    if not p or not item or not item.place_result or item.place_result.name~=req.entity then error('placement_query_requires_named_building_item') end
    local dir=DIR[req.direction or 'north'];if not dir then error('invalid_direction') end
    -- Keep preflight local, including conservative coverage of the footprint and
    -- adjacent tile rules. Never query hidden terrain through a collision result.
    if (req.x-c.position.x)^2+(req.y-c.position.y)^2>100 then error('placement_query_must_be_local') end
    local b=p.collision_box
    local extent=math.ceil(math.max(math.abs(b.left_top.x),math.abs(b.left_top.y),math.abs(b.right_bottom.x),math.abs(b.right_bottom.y),p.tile_width/2,p.tile_height/2))+4
    if extent>32 then error('placement_footprint_too_large') end
    for x=math.floor((req.x-extent)/32),math.floor((req.x+extent)/32) do
      for y=math.floor((req.y-extent)/32),math.floor((req.y+extent)/32) do
        if not c.force.is_chunk_charted(c.surface,{x,y}) then error('placement_footprint_not_charted') end
      end
    end
    return {tick=game.tick,can_place=c.can_place_entity{name=req.entity,position={req.x,req.y},direction=dir},item_count=c.get_item_count(req.entity),position={x=req.x,y=req.y},entity=req.entity,direction=dir}
  elseif op=='scan' then
    local c=actor();local radius=req.radius or 64
    if type(radius)~='number' or radius<1 or radius>128 then error('radius_must_be_1_to_128') end
    if req.name and not named(req.name) then error('invalid_name') end
    local es=c.surface.find_entities_filtered{position=c.position,radius=radius,name=req.name,type=req.type}
    local out={}
    for _,e in ipairs(es) do
      local chunk={math.floor(e.position.x/32),math.floor(e.position.y/32)}
      if e~=c and c.force.is_chunk_charted(c.surface,chunk) and
        (e.force.name~='enemy' or c.force.is_chunk_visible(c.surface,chunk)) then
        out[#out+1]={id=e.unit_number,name=e.name,type=e.type,force=e.force.name,health=e.health,x=e.position.x,y=e.position.y,amount=e.type=='resource' and e.amount or nil,distance=math.sqrt((e.position.x-c.position.x)^2+(e.position.y-c.position.y)^2)}
      end
    end
    table.sort(out,function(a,b)return a.distance<b.distance end)
    local results={};for i=1,math.min(#out,req.limit and math.min(100,math.max(1,req.limit)) or 20)do results[i]=out[i]end
    return {entities=results,total=#out,truncated=#results<#out,tick=game.tick,scope='charted_with_currently_visible_enemies'}
  elseif op=='inspect' then
    local c=actor();if not coordinate(req.x) or not coordinate(req.y) then error('invalid_coordinates') end
    local e=entity_at(c,req);close_to(c,e)
    local invs={};for name,idx in pairs(INV) do if name~='ammo' or e.type=='ammo-turret' then local inv=e.get_inventory(idx);if inv then invs[name]=inv.get_contents() end end end
    local out={name=e.name,position=e.position,direction=e.direction,status=e.status,inventories=invs}
    if e.type=='transport-belt' or e.type=='underground-belt' then
      out.lines={e.get_transport_line(1).get_contents(),e.get_transport_line(2).get_contents()}
      if e.type=='underground-belt' then
        out.belt_type=e.belt_to_ground_type;local n=e.neighbours
        if n and n.valid and n.force==c.force then out.neighbour_id=n.unit_number end
      end
    end
    if e.type=='mining-drill' then out.drop_position=e.drop_position end
    return out
  end
  error('unknown_operation')
end
commands.add_command('codex-agent','Bounded local agent control (JSON).',function(cmd)
  if cmd.player_index and not game.get_player(cmd.player_index).admin then return end
  local ok,result=pcall(function()
    if not cmd.parameter or #cmd.parameter>131072 then error('request_too_large_or_missing') end
    return handle(helpers.json_to_table(cmd.parameter))
  end)
  local response=ok and {ok=true,result=result} or {ok=false,error=tostring(result)}
  if not ok then log('codex-agent rejected: '..tostring(result)) end
  rcon.print(helpers.table_to_json(response))
end)
script.on_init(function()state()end)
script.on_configuration_changed(function()state().version=VERSION end)
script.on_load(function()resumed=true end)
script.on_event(defines.events.on_tick,tick)
script.on_event(defines.events.on_entity_damaged,function(e)
  local s=state();local record=combat_observation.record(e,s.character,'damage')
  if record then s.last_damage=record;if s.guard then s.guard.urgent=true end;event('engineer_damaged',record) end
end)
script.on_event(defines.events.on_entity_died,function(e)
  local s=state();local record=combat_observation.record(e,s.character,'death')
  if record then s.last_death=record;event('engineer_died',record) end
end)
script.on_event(defines.events.on_player_crafted_item,function(e)
  if e.player_index==state().owner then
    event('player_crafted',{recipe=e.recipe.name,item=e.item_stack.name,count=e.item_stack.count})
  end
end)
if defines.events.on_research_finished then script.on_event(defines.events.on_research_finished,function(e)
  local s=state();local owner=s.owner and game.get_player(s.owner)
  if owner and e.research.force==owner.force then
    local record={technology=e.research.name,tick=game.tick,by_script=e.by_script}
    s.research_events=s.research_events or {};s.research_events[e.research.name]=record
    event('research_finished',record)
  end
end) end
if defines.events.on_rocket_launched then script.on_event(defines.events.on_rocket_launched,function(e)
  local s=state();local owner=s.owner and game.get_player(s.owner)
  if owner and e.rocket.valid and e.rocket.force==owner.force then
    local record={tick=game.tick,rocket=e.rocket.unit_number,
      silo=e.rocket_silo and e.rocket_silo.unit_number}
    s.launches=s.launches or {};s.launches[#s.launches+1]=record
    if #s.launches>64 then table.remove(s.launches,1) end
    event('rocket_launched',record)
  end
end) end
script.on_event(defines.events.on_script_path_request_finished,function(e)
  local s=state();local j=s.current and s.jobs[s.current];local r=j and j.runtime
  if r and r.path_id==e.id then r.path=e.path;r.ready=true;r.busy=e.try_again_later end
end)
script.on_event(defines.events.on_gui_click,function(e)
  if not e.element or not e.element.valid or e.element.name~='codex_agent_stop' then return end
  local s=state();if e.player_index~=s.owner then return end
  local j=s.current and s.jobs[s.current]
  if j and j.status=='running' then finish(j,'cancelled','viewer_stop_button') end
  if s.guard then s.guard.enabled=false;s.guard.active=false;stop(s.character) end
end)
