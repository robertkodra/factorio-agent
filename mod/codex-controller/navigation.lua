-- Track progress towards the current path waypoint, not merely displacement.
-- Small back-and-forth movements must not reset the watchdog indefinitely.
local navigation = {}
function navigation.progress(r, segment, distance, tick)
  if r.progress_segment ~= segment or not r.progress_tick then
    r.progress_segment = segment
    r.progress_best = distance
    r.progress_tick = tick
  elseif distance < r.progress_best - 0.1 then
    r.progress_best = distance
    r.progress_tick = tick
  end
  return tick - r.progress_tick <= 120
end
return navigation
