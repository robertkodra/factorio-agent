"""Recover a surface-belt obstruction by normally mining an observed tree."""
import math
from .obstacles import neutral_bounds
from .routes import service_stances


def clear_tree_for_belt(action, observation, factory, scan, prototypes):
    if action.get('type') != 'place' or action.get('entity') != 'transport-belt':
        return None
    trees = dict(scan,entities=[e for e in scan['entities']
                               if e.get('type')=='tree' and e.get('force')=='neutral'])
    bounds = neutral_bounds(trees,prototypes)
    for tree in bounds:
        box=tree['box'];x,y=action['x'],action['y']
        # Base surface-belt collision extent; this controller admits base only.
        if not (box['left_top']['x'] < x+.4 and box['right_bottom']['x'] > x-.4
                and box['left_top']['y'] < y+.4 and box['right_bottom']['y'] > y-.4):
            continue
        p=tree['position'];origin=observation['position']
        distance=math.hypot(origin['x']-p['x'],origin['y']-p['y'])
        if distance>10:
            continue
        stand={k:p[k]+(origin[k]-p[k])*2/max(distance,.01) for k in ('x','y')}
        stand=service_stances(dict(position=p,stand=stand,gather='wood'),
                              factory['entities']+bounds)[0]
        return dict(key=f"clear-tree:{tree['name']}@{p['x']},{p['y']}",
                    detail='Normally mine an observed tree obstructing the planned belt',
                    actions=[dict(type='walk',**stand,timeout=3600),
                             dict(type='mine',entity=tree['name'],**p,item='wood',count=1,timeout=3600)])
    return None
