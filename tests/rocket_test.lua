local response,request,command;local handlers={};local launches=0
local force={};local owner={force=force};local silo={valid=true,name='rocket-silo',type='rocket-silo',force=force,unit_number=9}
silo.launch_rocket=function()launches=launches+1;return silo.ready or false end
local character={valid=true,type='character',force=force,position={x=0,y=0},walking_state={walking=false},crafting_queue_size=0,
 can_reach_entity=function()return silo.reachable~=false end,
 surface={find_entities_filtered=function()return{silo}end}}
defines={inventory={},events={on_tick=1,on_research_finished=2,on_rocket_launched=3},controllers={}}
script={active_mods={base='2.0.77',['codex-controller']='0.5.0'},on_init=function()end,
 on_configuration_changed=function()end,on_load=function()end,
 on_event=function(id,f)if id then handlers[id]=f end end}
commands={add_command=function(_,_,f)command=f end}
rcon={print=function()end};log=function()end
helpers={json_to_table=function()return request end,table_to_json=function(v)response=v;return '{}' end,write_file=function()end}
storage={agent={character=character,owner=1,jobs={},order={},events={},sequence=0,follow=false}}
game={tick=1,speed=1,get_player=function()return owner end}
package.path='mod/codex-controller/?.lua;'..package.path
dofile('mod/codex-controller/control.lua')
local serial=0
local function launch()
 serial=serial+1;request={op='submit',id='launch-'..serial,actions={{type='launch',entity='rocket-silo',x=0,y=0}}}
 command{parameter='{}'};assert(response.ok)
 handlers[1]();game.tick=game.tick+1;handlers[1]();game.tick=game.tick+1
 return storage.agent.jobs[request.id]
end
silo.reachable=false;assert(launch().status=='failed' and launches==0)
silo.reachable=true;silo.force={};assert(launch().status=='failed' and launches==0)
silo.force=force;assert(launch().status=='failed' and launches==1)
silo.ready=true;assert(launch().status=='complete' and launches==2)
assert(not storage.agent.launches,'A launch order must not count as a launch event')
handlers[3]{rocket={valid=true,force={},unit_number=22},rocket_silo=silo}
assert(not storage.agent.launches,'Other forces do not count')
handlers[3]{rocket={valid=true,force=force,unit_number=22},rocket_silo=silo}
assert(#storage.agent.launches==1 and storage.agent.launches[1].silo==9)
handlers[2]{research={name='military-2',force=force},by_script=false}
assert(storage.agent.research_events['military-2'].by_script==false)
handlers[2]{research={name='rocket-silo',force=force},by_script=true}
assert(storage.agent.research_events['rocket-silo'].by_script==true)
local old=storage.agent.jobs['launch-4']
storage.agent.receipts={['launch-4']={id=old.id,status=old.status,index=old.index,
 total=#old.actions,metrics=old.metrics,fingerprint=old.fingerprint,archived=true}}
storage.agent.jobs['launch-4']=nil
request={op='status',id='launch-4'};command{parameter='{}'}
assert(response.ok and response.result.id=='launch-4' and response.result.status=='complete')
request={op='submit',id='launch-4',actions={{type='launch',entity='rocket-silo',x=0,y=0}}}
command{parameter='{}'};assert(response.ok and launches==2,'Archived submission must not replay')
storage.agent.receipts['launch-4'].fingerprint='different-payload'
command{parameter='{}'};assert(not response.ok and response.error:find('id_conflict'))
print('Owned/reachable/ready silo gating and actual launch/research event evidence passed')
