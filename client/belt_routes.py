"""Directed surface belts along explicitly chosen, surveyed waypoints.

This does not survey terrain or prove lane contents. Every placement still
requires local native preflight and ordinary inventory-funded construction.
"""
import math

DIRECTIONS = {(0, -1): 'north', (1, 0): 'east', (0, 1): 'south', (-1, 0): 'west'}
NATIVE_DIRECTIONS = {'north': 0, 'east': 4, 'south': 8, 'west': 12}


def underground_pair(start, end, max_span, prefix='crossing'):
    """Two ordinary endpoints; max_span must come from the actual prototype."""
    route = belt_route([start, end], 'north', prefix)
    if type(max_span) is not int or not 1 <= max_span <= 255:
        raise ValueError('Use the observed positive underground span limit')
    if len(route['path'])-1 > max_span:
        raise ValueError('Underground endpoints exceed the native span')
    direction = route['sites'][0]['direction']
    sites = []
    for side, p in [('input',start),('output',end)]:
        sites.append(dict(id=prefix+'-'+side,entity='underground-belt',build=True,
            position=dict(x=p[0],y=p[1]),stand=dict(x=p[0]+2,y=p[1]),
            direction=direction,belt_type=side))
    return dict(sites=sites,materials={'underground-belt':2},
        limitations=['Native endpoint placement and reciprocal neighbour IDs must be verified.',
                     'Other nearby underground belts can change pairing; observe actual item flow.'])


def belt_route(waypoints, final_direction, prefix='belt'):
    points = [tuple(p) for p in waypoints]
    if len(points) < 2 or final_direction not in NATIVE_DIRECTIONS:
        raise ValueError('Two tile-centered waypoints and a cardinal output are required')
    if any(len(p) != 2 or any(isinstance(v, bool) or not isinstance(v, (int, float))
            or not math.isfinite(v) or abs(v) > 1_000_000 or v % 1 != .5 for v in p) for p in points):
        raise ValueError('Waypoints must be bounded tile centers')
    path = [points[0]]
    for a, b in zip(points, points[1:]):
        dx, dy = b[0]-a[0], b[1]-a[1]
        if bool(dx) == bool(dy):
            raise ValueError('Each leg must be nonempty and cardinal')
        length = int(abs(dx)+abs(dy))
        if len(path)+length > 10000:
            raise ValueError('Belt route exceeds construction bound')
        step = (int(dx/length), int(dy/length))
        path.extend((a[0]+step[0]*i, a[1]+step[1]*i) for i in range(1, length+1))
    if len(set(path)) != len(path):
        raise ValueError('A surface route cannot cross or revisit itself')
    sites = []
    for i, p in enumerate(path):
        direction = final_direction if i == len(path)-1 else DIRECTIONS[
            (int(path[i+1][0]-p[0]), int(path[i+1][1]-p[1]))]
        # Belts are walkable. A nearby stance on the route saves walking around
        # every tile; native movement and placement still enforce collisions.
        sites.append(dict(id=f'{prefix}-{i}', entity='transport-belt', build=True,
                          position=dict(x=p[0], y=p[1]),
                          stand=dict(x=p[0], y=p[1]), direction=direction))
    return dict(sites=sites, materials={'transport-belt': len(sites)}, path=path,
                limitations=['Caller must survey the corridor and resolve other belts/obstacles.',
                             'Normal placement and actual lane flow require live validation.'])


def nearby_belt_batch(choice, sites, entities, observation, researched, limit=12):
    """Append stocked, nearby belt placements without moving or replaying work."""
    if len(choice['actions']) != 1:
        return choice
    first = choice['actions'][0]
    if first['type'] != 'place' or first['entity'] != 'transport-belt':
        return choice
    stock = sum(i['count'] for i in observation['inventory']
                if i['name'] == 'transport-belt' and i.get('quality', 'normal') == 'normal')
    actions = [first]
    used = {(first['x'], first['y'])}
    p = observation['position']
    for sid, site in sites.items():
        q = site['position']
        if (len(actions) >= min(limit, stock) or site['entity'] != 'transport-belt'
                or not site.get('build') or entities.get(sid)
                or any(t not in researched for t in site.get('requires', []))
                or (q['x'], q['y']) in used
                or math.hypot(q['x']-p['x'], q['y']-p['y']) > 5):
            continue
        actions.append(dict(type='place', entity='transport-belt', **q,
                            direction=site.get('direction', 'north')))
        used.add((q['x'], q['y']))
    return dict(choice, actions=actions)
