"""Plan ordinary surface pipes inside an explicitly surveyed tile set.

Coordinates are tile indices; generated placements use tile centers. Callers
must provide verified machine-port endpoints, terrain and collision exclusions.
This routes pipes only: it does not infer ports, expose terrain, supply fluids,
place underground pipes, or prove engine fluid connectivity/throughput.
"""
from collections import deque


def pipe_route(fluid, start, goal, allowed, blocked=(), existing=None, prefix='pipe'):
    if not isinstance(fluid,str) or not fluid:
        raise ValueError('Name the fluid being routed')
    allowed, blocked = set(allowed), set(blocked)
    existing = dict(existing or {})
    start,goal=tuple(start),tuple(goal)
    for tile in allowed | blocked | set(existing) | {start,goal}:
        if len(tile)!=2 or any(type(v) is not int or abs(v)>1_000_000 for v in tile):
            raise ValueError('Tiles must contain bounded integer coordinates')
    if len(allowed)>100_000:
        raise ValueError('Route scope must remain bounded')
    def neighbors(p):
        x,y=p
        return ((x+1,y),(x,y+1),(x-1,y),(x,y-1))
    def usable(p):
        if p not in allowed or p in blocked:
            return False
        # Adjacent surface pipes join. Reject both crossing and side contact
        # with a previously assigned different fluid, including at endpoints.
        return all(q not in existing or existing[q]==fluid for q in (p,*neighbors(p)))
    if not usable(start) or not usable(goal):
        raise ValueError('Endpoints must be surveyed, clear and fluid-compatible')
    queue=deque([start]);parents={start:None}
    while queue and goal not in parents:
        p=queue.popleft()
        for q in neighbors(p):
            if q not in parents and usable(q):
                parents[q]=p;queue.append(q)
    if goal not in parents:
        raise ValueError('No separated surface-pipe route within surveyed tiles')
    path=[];p=goal
    while p is not None:
        path.append(p);p=parents[p]
    path.reverse()
    sites=[]
    for i,p in enumerate(path):
        if p in existing:
            continue
        access=next((q for q in neighbors(p) if q in allowed and q not in blocked
                     and q not in path and q not in existing),None)
        if access is None:
            raise ValueError('No surveyed side access for pipe construction')
        sites.append(dict(id=f'{prefix}-{i}',entity='pipe',build=True,
            position=dict(x=p[0]+.5,y=p[1]+.5),stand=dict(x=access[0]+.5,y=access[1]+.5)))
    return dict(fluid=fluid,path=path,sites=sites,materials={'pipe':len(sites)},
        limitations=['Endpoints and machine port directions must be checked separately.',
                     'Only the provided surveyed tiles and fluid reservations are considered.',
                     'Native placement, actual fluid flow, power and capacity require live validation.'])
