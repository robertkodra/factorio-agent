"""Conservative collision bounds for explicitly scanned neutral obstacles.

Static prototype geometry is not a world survey. Instantiate it only for entities
returned by a bounded charted scan. Unknown orientation uses a conservative square;
these exclusions do not certify a navigable path or complete terrain coverage.
"""
SOLID_TYPES={'tree','container','simple-entity','simple-entity-with-owner'}


def neutral_bounds(scan, prototypes):
    rows=[]
    for e in scan['entities']:
        if e.get('force')!='neutral' or e.get('type') not in SOLID_TYPES:continue
        proto=prototypes.get(e['name']);box=proto.get('collision_box') if proto else None
        if not box:continue
        extent=max(abs(box[corner][axis]) for corner in ('left_top','right_bottom') for axis in ('x','y'))
        if not 0<extent<=20:continue
        rows.append(dict(name=e['name'],type=e['type'],position=dict(x=e['x'],y=e['y']),
            box=dict(left_top=dict(x=e['x']-extent,y=e['y']-extent),
                     right_bottom=dict(x=e['x']+extent,y=e['y']+extent))))
    return rows
