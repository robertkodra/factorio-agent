package.path='mod/codex-controller/?.lua;'..package.path
local history=require('job_history')
local s={jobs={},order={}}
for i=1,1200 do
 history.make_room(s)
 local id='job-'..i;s.current=id;s.order[#s.order+1]=id
 s.jobs[id]={id=id,index=2,actions={{type='wait_ticks'}},status=i%3==0 and 'failed' or 'complete',
   error=i%3==0 and 'test_failure' or nil,fingerprint='exact-payload-'..i,metrics={ticks=1}}
end
assert(#s.order==256 and s.receipt_count==944)
for i=1,1200 do
 local j=history.find(s,'job-'..i)
 assert(j and j.fingerprint=='exact-payload-'..i)
 if i%3==0 then assert(j.status=='failed' and j.error=='test_failure') end
end
assert(s.jobs[s.current] and not s.receipts[s.current])
s.receipt_count=history.MAX_RECEIPTS
assert(not pcall(history.make_room,s),'Capacity must never silently discard old IDs')
print('1200 jobs retain receipt identity and failure evidence without replay or active eviction')
