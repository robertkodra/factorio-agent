-- Keep recent full jobs and durable compact receipts. A retired ID is never
-- reusable, even when its full action/runtime table has left the recent ring.
local M={RECENT=256,MAX_RECEIPTS=65536}
function M.find(s,id) return s.jobs[id] or (s.receipts and s.receipts[id]) end
function M.make_room(s)
  s.receipts=s.receipts or {};s.receipt_count=s.receipt_count or 0
  if #s.order<M.RECENT then return end
  if s.receipt_count>=M.MAX_RECEIPTS then error('job_receipts_full_preserve_run') end
  local index
  for i,id in ipairs(s.order) do
    if id~=s.current and s.jobs[id].status~='running' then index=i;break end
  end
  if not index then error('no_retirable_job') end
  local id=s.order[index];local j=s.jobs[id]
  s.receipts[id]={id=id,status=j.status,index=j.index,total=#j.actions,
    action=j.actions[j.index] and j.actions[j.index].type,
    started_tick=j.started_tick,finished_tick=j.finished_tick,error=j.error,
    metrics=j.metrics,fingerprint=j.fingerprint,archived=true}
  s.receipt_count=s.receipt_count+1;s.jobs[id]=nil;table.remove(s.order,index)
end
return M
