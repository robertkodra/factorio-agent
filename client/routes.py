"""Route through explicitly surveyed corridors, using normal walk actions."""
import heapq
import math


def distance(a,b):
    return math.hypot(a['x']-b['x'],a['y']-b['y'])


def corridor(start,goal,network):
    if not network or distance(start,goal)<24:
        return [goal]
    nodes=network['nodes'];edges=network['edges']
    first=min(nodes,key=lambda n:distance(start,nodes[n]))
    last=min(nodes,key=lambda n:distance(goal,nodes[n]))
    adjacent={n:[] for n in nodes}
    for a,b in edges:
        adjacent[a].append(b);adjacent[b].append(a)
    queue=[(0,first,[])];seen=set();path=None
    while queue:
        cost,node,prior=heapq.heappop(queue)
        if node in seen:continue
        seen.add(node)
        if node==last:
            path=prior+[node];break
        for other in adjacent[node]:
            heapq.heappush(queue,(cost+distance(nodes[node],nodes[other]),other,prior+[node]))
    if path is None:
        raise ValueError('Configured travel corridor is disconnected')
    points=[nodes[n] for n in path]+[goal]
    result=[];previous=start
    for p in points:
        if distance(previous,p)<.6:continue
        # Short destinations constrain the game pathfinder to the surveyed
        # corridor. Collision/path failure still stops the normal movement job.
        pieces=max(1,math.ceil(distance(previous,p)/24))
        for i in range(1,pieces+1):
            result.append({k:previous[k]+(p[k]-previous[k])*i/pieces for k in ('x','y')})
        previous=p
    return result


def service_stances(site,entities):
    p=site['position'];stand=site['stand']
    if site.get('gather') and distance(p,stand)>2:
        scale=2/distance(p,stand)
        stand={k:p[k]+(stand[k]-p[k])*scale for k in ('x','y')}
    options=[stand]
    # Natural-entity reach is shorter than the generic factory service radius.
    # Leave margin for the normal walking arrival tolerance.
    for radius in ((1.5,2) if site.get('gather') else (3,4,5)):
        for dx,dy in ((1,0),(0,1),(-1,0),(0,-1),(1,1),(-1,1),(-1,-1),(1,-1)):
            scale=radius/math.hypot(dx,dy) if site.get('gather') else radius
            options.append({'x':p['x']+scale*dx,'y':p['y']+scale*dy})
    result=[]
    for option in options:
        if any(e.get('box') and
            e['box']['left_top']['x']-.25<option['x']<e['box']['right_bottom']['x']+.25 and
            e['box']['left_top']['y']-.25<option['y']<e['box']['right_bottom']['y']+.25
            for e in entities if e.get('type') not in ('character','transport-belt','inserter','resource')):
            continue
        if option not in result:result.append(option)
    if not result:raise ValueError('No unoccupied service stance in observed factory geometry')
    return result
