"""Bind pinned recipe fluid slots to observed prototype ports and cardinal turns."""
DIRECTIONS={'north':0,'east':4,'south':8,'west':12}
STEPS={0:(0,-1),4:(1,0),8:(0,1),12:(-1,0)}


def recipe_ports(prototype, recipe, position, direction='north'):
    if direction not in DIRECTIONS:
        raise ValueError('Fluid layouts require a cardinal direction')
    turn=DIRECTIONS[direction];result=[]
    for field,kind in [('ingredients','input'),('products','output')]:
        boxes=sorted((b for b in prototype['fluid_boxes'] if b['production_type']==kind),key=lambda b:b['index'])
        fluids=[i for i in recipe[field] if i['type']=='fluid']
        used=set()
        for ordinal,fluid in enumerate(fluids,1):
            slot=fluid.get('fluidbox_index',ordinal)
            if slot<1 or slot>len(boxes) or slot in used:
                raise ValueError('Recipe fluid slot is unavailable or duplicated')
            used.add(slot);box=boxes[slot-1]
            if box.get('filter') and box['filter']!=fluid['name']:
                raise ValueError('Recipe does not match the fluid-box filter')
            for connection in box['connections']:
                if connection['type']!='normal':
                    continue
                offset=connection['positions'][turn//4]
                facing=(connection['direction']+turn)%16
                if facing not in STEPS:
                    raise ValueError('Non-cardinal fluid connection')
                dx,dy=STEPS[facing]
                inside={k:position[k]+offset[k] for k in ('x','y')}
                result.append(dict(fluid=fluid['name'],flow=kind,box=box['index'],
                    position=inside,target=dict(x=inside['x']+dx,y=inside['y']+dy)))
    return result


def connected_segment(source,source_box,destination,destination_box,fluid):
    """Require a shared native segment and matching locks; not a throughput test."""
    def box(entity,index):
        return next((b for b in entity.get('fluid_boxes',[]) if b['index']==index),{})
    a,b=box(source,source_box),box(destination,destination_box)
    return (a.get('segment_id') is not None and a.get('segment_id')==b.get('segment_id')
            and a.get('locked_fluid') in (None,fluid) and b.get('locked_fluid') in (None,fluid))


def fluid_path(factory, source, destination, fluid):
    """Find a directed native connection path between (entity ID, box) pairs.

    Output-only boxes can lack segment IDs. Follow observed reciprocal ports,
    admitting flow only out of the source port and into the receiving port.
    This proves topology, not production or adequate throughput.
    """
    from collections import deque
    boxes={(e['id'],b['index']):b for e in factory['entities'] if e.get('id') is not None
           for b in e.get('fluid_boxes',[])}
    observed={(e['id'],f['index']):f['name'] for e in factory['entities'] if e.get('id') is not None
              for f in e.get('fluids',[])}
    start,goal=tuple(source),tuple(destination)
    def compatible(key):
        return (key in boxes and boxes[key].get('locked_fluid') in (None,fluid)
                and observed.get(key) in (None,fluid))
    if not compatible(start) or not compatible(goal):return []
    queue=deque([start]);parents={start:None}
    while queue and goal not in parents:
        node=queue.popleft()
        for c in boxes[node].get('connections',[]):
            target=(c.get('target_id'),c.get('target_box'))
            if c.get('flow') not in ('output','input-output') or target in parents or not compatible(target):continue
            receiving=any(r.get('target_id')==node[0] and r.get('target_box')==node[1]
                          and r.get('flow') in ('input','input-output')
                          for r in boxes[target].get('connections',[]))
            if receiving:parents[target]=node;queue.append(target)
    if goal not in parents:return []
    path=[];node=goal
    while node is not None:path.append(node);node=parents[node]
    return list(reversed(path))
