"""Relative item-fed assembly cells for the bounded factory scheduler.

These are construction plans, not free blueprints or placement guarantees.
Each item is crafted/placed normally and actual power/output must be observed.
Fluid recipes deliberately require a separate routed fluid layout.
"""
import argparse
from collections import Counter
import json

from .materials import CATALOG


def assembly_cell(recipe, origin=(0,0), prefix='cell'):
    catalog = json.loads(CATALOG.read_text())
    r = catalog['recipes'][recipe]
    if r['category'] not in ('crafting','advanced-crafting') or any(
            i['type'] != 'item' for i in r['ingredients'] + r['products']):
        raise ValueError('This cell supports item-only assembly; route fluids separately')
    if any(type(v) is not int for v in origin):
        raise ValueError('Cell origin must be an integer tile coordinate')
    ox,oy = origin
    sites=[]
    def add(label,entity,x,y,sx,sy,**kw):
        sites.append(dict(id=prefix+'-'+label,entity=entity,
            position=dict(x=ox+x,y=oy+y),stand=dict(x=ox+sx,y=oy+sy),build=True,**kw))
    add('power','small-electric-pole',.5,2.5,1.5,3.5)
    add('link','small-electric-pole',4.5,2.5,3.5,3.5)
    add('input','wooden-chest',-2.5,.5,-2.5,2.5)
    add('output','wooden-chest',3.5,.5,3.5,2.5)
    # Base inserter north picks north and drops south. West picks left and
    # drops right; both arms therefore move items from left to right.
    add('inserter-in','inserter',-1.5,.5,-1.5,2.5,direction='west')
    add('inserter-out','inserter',2.5,.5,2.5,2.5,direction='west')
    add('machine','assembling-machine-1',.5,.5,.5,3.5,recipe=recipe,
        input_site=prefix+'-input',output_site=prefix+'-output')
    return dict(sites=sites, materials=dict(Counter(s['entity'] for s in sites)),
                bounding_tiles=dict(left=ox-3,top=oy-1,right=ox+5,bottom=oy+4),
                limitations=['Requires a connected, adequately supplied power grid.',
                             'Check charted terrain, full footprints and access before installation.',
                             'Input/output chests are finite buffers; the scheduler replenishes/collects them.',
                             'Recipe must be unlocked and the actual machine must produce output.'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('recipe');parser.add_argument('--x',type=int,default=0)
    parser.add_argument('--y',type=int,default=0);parser.add_argument('--prefix',default='cell')
    a=parser.parse_args()
    print(json.dumps(assembly_cell(a.recipe,(a.x,a.y),a.prefix),indent=2))
