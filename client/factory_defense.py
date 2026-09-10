"""Detect new damage to observed owned buildings and service a defense station.

Native events preserve destruction and damage repaired between health samples.
Health polling is a fallback, never an attribution of the enemy's origin.
"""
import math

from .routes import corridor


class FactoryDefense:
    def __init__(self, state=None):
        self.state=state or {'health':{},'tick':None,'alarm':None}

    def event(self, record):
        """Accept bounded native owned-building evidence, including destruction."""
        seq=record.get('seq',0)
        if seq<=self.state.get('event_seq',0):
            return False
        self.state['event_seq']=seq
        alarm=self.state.get('alarm')
        damage={d['id']:d for d in (alarm or {}).get('damage',[])}
        damage.pop(record['id'],None)
        damage[record['id']]=dict(record)
        self.state['alarm']=dict(tick=max(record['tick'],(alarm or {}).get('tick',0)),
            damage=list(damage.values())[-32:])
        return True

    def observe(self, factory):
        tick=factory['tick']
        if self.state['tick'] is not None and tick<self.state['tick']:
            raise RuntimeError('Factory defense timeline regressed')
        previous=self.state['health']; current={}; damage=[]
        for e in factory['entities']:
            if e.get('id') is None or 'health' not in e or e.get('type')=='character':
                continue
            key=str(e['id']); current[key]=e['health']
            if key in previous and e['health']<previous[key]-.01:
                damage.append(dict(id=e['id'],entity=e['name'],position=e['position'],
                    health=e['health'],lost=previous[key]-e['health']))
        self.state.update(health=current,tick=tick)
        if damage:
            alarm=self.state.get('alarm') or {}
            combined={d['id']:d for d in alarm.get('damage',[])}
            for d in damage:
                combined.pop(d['id'],None)
                combined[d['id']]=d
            self.state['alarm']=dict(tick=max(tick,alarm.get('tick',0)),
                                     damage=list(combined.values())[-32:])
        return damage

    def response(self, observation, factory, plan):
        alarm=self.state['alarm']
        if not alarm:
            return None
        sites={s['id']:s for s in plan['sites']}
        stations=[]
        for sid in plan.get('defense_stations',[]):
            site=sites[sid]
            e=next((e for e in factory['entities'] if e['name']=='gun-turret'
                and math.dist(tuple(e['position'][k] for k in ('x','y')),
                              tuple(site['position'][k] for k in ('x','y')))<.2),None)
            if e and sum(i['count'] for i in e.get('ammo',[]))>0:
                distance=min(math.dist(tuple(site['position'][k] for k in ('x','y')),
                    tuple(d['position'][k] for k in ('x','y'))) for d in alarm['damage'])
                if distance<=36:
                    stations.append((distance,sid,site))
        if not stations:
            return dict(key='factory-defense:uncovered',actions=[],detail='No loaded station covers observed factory damage')
        _,sid,site=min(stations)
        if math.dist(tuple(observation['position'][k] for k in ('x','y')),
                     tuple(site['stand'][k] for k in ('x','y')))<=2:
            if observation['tick']-alarm['tick']>=600:
                self.state['alarm']=None
                return None
            return dict(key='factory-defense:hold',actions=[],detail='Observe the attacked area while local reflex owns combat')
        return dict(key='factory-defense:'+sid,actions=[dict(type='walk',**p,timeout=3600)
            for p in corridor(observation['position'],site['stand'],plan.get('corridors'),factory['entities'])],
            detail='Respond to new owned-factory damage at a loaded defensive station')
