local navigation = dofile('mod/codex-controller/navigation.lua')
local r = {}
assert(navigation.progress(r,1,10,0))
-- Moving back and forth does not count as cumulative progress.
for tick=1,120 do assert(navigation.progress(r,1,10+(tick%2)*0.14,tick)) end
assert(not navigation.progress(r,1,10.05,121))
-- Actual progress buys time; roundoff-sized changes do not.
assert(navigation.progress(r,1,9,122))
assert(navigation.progress(r,1,8.95,240))
assert(not navigation.progress(r,1,8.95,243))
-- A new path segment may initially be farther from its target.
assert(navigation.progress(r,2,50,244))
assert(navigation.progress(r,2,49,360))
-- A new path/reloaded legacy runtime initializes its progress state.
r.progress_tick=nil
assert(navigation.progress(r,2,60,500))
assert(not navigation.progress(r,2,60,621))
print('Navigation progress watchdog passed')
