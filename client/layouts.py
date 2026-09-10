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
        input_site=prefix+'-input',output_site=prefix+'-output',
        input_inserter=prefix+'-inserter-in',output_inserter=prefix+'-inserter-out',batch_size=50)
    return dict(sites=sites, materials=dict(Counter(s['entity'] for s in sites)),
                bounding_tiles=dict(left=ox-3,top=oy-1,right=ox+5,bottom=oy+4),
                limitations=['Requires a connected, adequately supplied power grid.',
                             'Check charted terrain, full footprints and access before installation.',
                             'Input/output chests are finite buffers; the scheduler replenishes/collects them.',
                             'Recipe must be unlocked and the actual machine must produce output.'])




def smelting_cell(recipe, origin=(0,0), prefix='smelt'):
    """Electric drill -> mixed ore/fuel chest -> furnace -> output chest."""
    if recipe not in ('iron-plate','copper-plate') or any(type(v) is not int for v in origin):
        raise ValueError('A metal recipe and integer furnace origin are required')
    x,y=origin
    def site(label,entity,dx,dy,sx,sy,**kw):
        return dict(id=prefix+'-'+label,entity=entity,position=dict(x=x+dx,y=y+dy),
                    stand=dict(x=x+sx,y=y+sy),build=True,**kw)
    sites=[site('power-north','small-electric-pole',2.5,-3.5,3.5,-3.5),
           site('power-south','small-electric-pole',2.5,1.5,3.5,1.5),
           site('input','wooden-chest',.5,-2.5,2.5,-2.5,
                stock_min={'coal':5},stock_target={'coal':30}),
           site('output','wooden-chest',.5,2.5,2.5,2.5),
           site('inserter-in','inserter',.5,-1.5,2.5,-1.5,direction='north'),
           site('inserter-out','inserter',.5,1.5,2.5,1.5,direction='north'),
           site('drill','electric-mining-drill',.5,-4.5,3.5,-4.5,direction='south',
                requires=['electric-mining-drill']),
           site('furnace','stone-furnace',0,0,3,0,recipe=recipe,
                input_site=prefix+'-input',output_site=prefix+'-output',external_inputs=True,eager=True)]
    return dict(sites=sites,materials=dict(Counter(s['entity'] for s in sites)),
                limitations=['Drill must cover observed ore and actually feed the input chest.',
                             'Both poles must join an adequately supplied grid.',
                             'Coal is replenished in the input chest; native inserters feed the furnace.',
                             'Normal placement and observed output are required.'])


def pole_line(start, end, prefix='power-line', wire_distance=7.5):
    """Connect tile-centered endpoints; terrain and actual network remain unproven.

    Endpoints are existing/planned poles and are excluded from returned sites.
    A one-tile spacing margin absorbs diagonal tile-center quantization.
    """
    import math
    points=(tuple(start),tuple(end))
    if any(len(p)!=2 or any(isinstance(v,bool) or not isinstance(v,(int,float))
            or not math.isfinite(v) or abs(v)>1_000_000 or v%1!=.5 for v in p) for p in points):
        raise ValueError('Pole endpoints must be bounded tile centers')
    if isinstance(wire_distance,bool) or not isinstance(wire_distance,(int,float)) or not 2<wire_distance<=100:
        raise ValueError('Wire distance must be greater than 2 and at most 100')
    a,b=points
    count=max(1,math.ceil(math.dist(a,b)/(wire_distance-1)))
    if count>10000:
        raise ValueError('Pole line exceeds bounded construction scope')
    path=[a]
    for i in range(1,count):
        p=tuple(round(a[k]+(b[k]-a[k])*i/count-.5)+.5 for k in range(2))
        if p!=path[-1]:path.append(p)
    path.append(b)
    if any(math.dist(x,y)>wire_distance for x,y in zip(path,path[1:])):
        raise ValueError('Quantized span exceeds the supplied wire distance')
    sites=[dict(id=f'{prefix}-{i}',entity='small-electric-pole',build=True,
        position=dict(x=x,y=y),stand=dict(x=x,y=y+2)) for i,(x,y) in enumerate(path[1:-1],1)]
    return dict(sites=sites,materials={'small-electric-pole':len(sites)},
        limitations=['Every footprint and stance needs normal local preflight.',
                     'The endpoints must actually exist and observed machines must receive power.'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('recipe');parser.add_argument('--x',type=int,default=0)
    parser.add_argument('--y',type=int,default=0);parser.add_argument('--prefix',default='cell')
    a=parser.parse_args()
    print(json.dumps(assembly_cell(a.recipe,(a.x,a.y),a.prefix),indent=2))
