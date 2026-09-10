"""Persistent, deterministic factory scheduler over fixed normal-mechanics actions.

Run against an explicitly configured, already-running practice world. Site
coordinates and access stances are private inputs, never inferred from hidden
terrain. Qwen is not in this control path. Uncertain submissions stop the runner
and retain the job ID for reconciliation; they are never replayed automatically.
"""
from __future__ import annotations

import argparse
from collections import Counter
import fcntl
import hashlib
import json
import math
from pathlib import Path
import secrets
import time

from .agent import Agent, ROOT
from .materials import CATALOG, craft_budget
from .progression import research_plan
from .routes import corridor, service_stances
from .supervisor import EventCursor


def contents(entries):
    result = Counter()
    for item in entries or []:
        if item.get('quality', 'normal') == 'normal':
            result[item['name']] += item['count']
    return result


def load_plan(path):
    plan = json.loads(Path(path).read_text())
    if plan.get('version') != 1 or not isinstance(plan.get('sites'), list):
        raise ValueError('Expected version 1 plan with sites')
    if type(plan.get('construction_batch_size',1)) is not int or not 1<=plan.get('construction_batch_size',1)<=20:
        raise ValueError('Construction batch size must be 1-20')
    if type(plan.get('clear_belt_trees',False)) is not bool:
        raise ValueError('clear_belt_trees must be boolean')
    if type(plan.get('watch_after_target',False)) is not bool:
        raise ValueError('watch_after_target must be boolean')
    radius=plan.get('local_transfer_radius',0)
    if isinstance(radius,bool) or not isinstance(radius,(int,float)) or not 0<=radius<=3:
        raise ValueError('Local transfer radius must be between 0 and 3 tiles')
    ids = set()
    for s in plan['sites']:
        if not isinstance(s.get('id'), str) or s['id'] in ids or not isinstance(s.get('entity'), str):
            raise ValueError('Site IDs must be unique and entities named')
        ids.add(s['id'])
        for key in ('position', 'stand'):
            if not isinstance(s.get(key), dict) or any(isinstance(s[key].get(k), bool) or
                    not isinstance(s[key].get(k), (int, float)) or
                    not math.isfinite(s[key][k]) or abs(s[key][k]) > 1_000_000 for k in ('x', 'y')):
                raise ValueError('Sites require bounded position and access stance')
        if math.dist(tuple(s['position'][k] for k in ('x','y')),
                     tuple(s['stand'][k] for k in ('x','y'))) > 9:
            raise ValueError('Access stance must be local to site')
    for source in plan.get('sources', []):
        if source.get('site') not in ids or source.get('inventory') not in ('fuel','output','chest'):
            raise ValueError('Source must refer to a site inventory')
        if type(source.get('reserve', 0)) is not int or source.get('reserve', 0) < 0:
            raise ValueError('Source reserve must be a nonnegative integer')
    for site in plan['sites']:
        if 'belt_type' in site and (site['entity'] != 'underground-belt' or site['belt_type'] not in ('input','output')):
            raise ValueError('belt_type requires a normal underground belt endpoint')
        if 'chest_slots' in site and (type(site['chest_slots']) is not int or not 0<=site['chest_slots']<=1000):
            raise ValueError('chest_slots must be an integer between 0 and 1000')
        if 'batch_size' in site and (type(site['batch_size']) is not int or not 1<=site['batch_size']<=100):
            raise ValueError('Cell batch_size must be 1-100')
        for item,minimum in site.get('stock_min',{}).items():
            target=site.get('stock_target',{}).get(item)
            if type(minimum) is not int or type(target) is not int or not 0<minimum<=target<=1000:
                raise ValueError('Buffer stocks require 0 < minimum <= target <= 1000')
        for key in ('input_site', 'output_site','input_inserter','output_inserter'):
            if key in site and site[key] not in ids:
                raise ValueError('Cell buffers must refer to configured sites')
    if plan.get('target') == 'infrastructure' and not any(s.get('build') for s in plan['sites']):
        raise ValueError('Infrastructure target requires construction sites')
    for sid in plan.get('defense_stations',[]):
        if sid not in ids or next(s for s in plan['sites'] if s['id']==sid)['entity']!='gun-turret':
            raise ValueError('Defense stations must refer to configured gun turrets')
    if plan.get('watch_after_target') and not plan.get('defense_stations'):
        raise ValueError('watch_after_target requires defense stations')
    if plan.get('target') not in ('rocket', 'infrastructure','defense'):
        research_plan([plan['target']])
    return plan


class Planner:
    """Choose one bounded skill from current state, never a replayed old batch."""
    def __init__(self, plan):
        self.plan = plan
        self.sites = {s['id']: s for s in plan['sites']}
        self.catalog = json.loads(CATALOG.read_text())
        self.recipes = self.catalog['recipes']
        self.reason = ''
        self.blocked_until = {}
        self.stance_attempts = Counter()
        self.service_intent = None
        self.consumed_gather = set()

    def refresh(self, observation, factory, research):
        self.o, self.f = observation, factory
        self.stock = contents(observation['inventory'])
        self.enabled = set(research['enabled_recipes'])
        self.entities = {}
        for sid, site in self.sites.items():
            p = site['position']
            self.entities[sid] = next((e for e in factory['entities']
                if e['name'] == site['entity'] and
                abs(e['position']['x'] - p['x']) < .2 and
                abs(e['position']['y'] - p['y']) < .2), None)

    def skill(self, key, actions, detail):
        if self.blocked_until.get(key, 0) > self.o['tick']:
            return None
        return dict(key=key, actions=actions, detail=detail)

    def at(self, sid, action, detail):
        site = self.sites[sid]
        p = self.o['position']
        # Avoid a service-position trip when already close to an owned inventory.
        # This is only a scheduling shortcut: native can_reach_entity still
        # decides whether the transfer is legal. A failed approach/transfer
        # restores stance-based navigation for this site.
        radius=self.plan.get('local_transfer_radius',0)
        if (radius and action['type'] in ('put','take') and self.entities.get(sid)
                and not self.stance_attempts[sid]
                and math.hypot(p['x']-site['position']['x'],p['y']-site['position']['y'])<=radius):
            self.service_intent=None
            return self.skill(detail+':'+sid,
                [dict(action,entity=site['entity'],**site['position'])],detail)
        # Travel and transfer are separate jobs: re-observe amounts after travel.
        options = service_stances(site, self.f['entities'] + self.f.get('obstacles',[]))
        stand = options[self.stance_attempts[sid] % len(options)]
        key = detail + ':' + sid
        if math.hypot(p['x'] - stand['x'], p['y'] - stand['y']) > .6:
            self.service_intent = dict(sid=sid, action=action, detail=detail)
            return self.skill('approach:' + sid,
                [dict(type='walk', **point, timeout=3600)
                 for point in corridor(p, stand, self.plan.get('corridors'),
                                      self.f['entities']+self.f.get('obstacles',[]))], 'Reach configured service stance')
        self.service_intent = None
        return self.skill(key, [dict(action, entity=site['entity'], **site['position'])], detail)

    def finish_service(self):
        """Finish the purpose of a trip, with current quantities and world state."""
        intent, self.service_intent = self.service_intent, None
        if not intent:
            return None
        sid, action, detail = intent['sid'], dict(intent['action']), intent['detail']
        entity = self.entities[sid]
        if action['type'] == 'place':
            if entity or not self.stock[self.sites[sid]['entity']]:
                return None
        elif action['type']=='mine' and self.sites[sid].get('gather'):
            if sid in self.consumed_gather:
                return None
        elif not entity:
            return None
        elif action['type'] in ('put', 'take'):
            item = action['item']
            if action['type'] == 'put':
                available = self.stock[item]
                if action.get('player_inventory') == 'ammo':
                    available = max(0, sum(s.get('magazines',0) for s in
                        self.o.get('guns',{}).get('slots',[]) if s.get('ammo')==item)
                        - self.plan.get('engineer_ammo_reserve',10))
            else:
                reserve = max((s.get('reserve',0) for s in self.plan.get('sources',[])
                    if s['site']==sid and s['item']==item and s['inventory']==action['inventory']),default=0)
                available = max(0, contents(entity.get(action['inventory']))[item]-reserve)
            action['count'] = min(action['count'], available)
            if not action['count']:
                return None
        elif action['type']=='set_recipe' and entity.get('recipe')==action['recipe']:
            return None
        return self.at(sid, action, detail)

    def input_location(self,sid):
        site=self.sites[sid]
        if site.get('input_inserter') and not self.entities.get(site['input_inserter']):
            return sid
        return site.get('input_site',sid)

    def output_location(self,sid):
        site=self.sites[sid]
        if site.get('output_inserter') and not self.entities.get(site['output_inserter']):
            return sid
        return site.get('output_site',sid)

    def sources(self, item):
        candidates = list(self.plan.get('sources', []))
        for sid, site in self.sites.items():
            recipe = self.recipes.get(site.get('recipe', ''))
            if recipe and any(p['name'] == item for p in recipe['products']):
                output=self.output_location(sid)
                candidates.append(dict(site=output,inventory='chest' if output!=sid else 'output',item=item))
        candidates = [s for s in candidates if s['item'] == item and self.entities[s['site']]]
        return sorted(candidates, key=lambda s: math.hypot(
            self.sites[s['site']]['stand']['x'] - self.o['position']['x'],
            self.sites[s['site']]['stand']['y'] - self.o['position']['y']))

    def ensure(self, item, amount, trail=()):
        missing = max(0, math.ceil(amount - self.stock[item]))
        if not missing:
            return None
        if item in trail or len(trail) > 20:
            self.reason = 'Dependency cycle while supplying ' + item
            return None
        trail = (*trail, item)
        available_total=sum(max(0,contents(self.entities[s['site']].get(s['inventory']))[item]
            -s.get('reserve',0)) for s in self.sources(item))
        ready_batch=min(missing,2 if item.endswith('science-pack') else 10)
        # Keep parallel producers fed before making another one-item delivery.
        # Otherwise the nearest assembler monopolizes every planning decision
        # while the other configured machines run out of intermediates.
        for sid, site in self.sites.items():
            recipe = self.recipes.get(site.get('recipe',''))
            entity = self.entities[sid]
            if not entity or not recipe or not any(p['name']==item for p in recipe['products']):
                continue
            inputs = contents(entity.get('input'))
            input_sid=self.input_location(sid)
            if input_sid!=sid:
                inputs.update(contents((self.entities.get(input_sid) or {}).get('chest')))
            output_sid = self.output_location(sid)
            available = contents((self.entities.get(output_sid) or {}).get(
                'chest' if output_sid!=sid else 'output'))[item]
            if available_total<ready_batch and available<2 and any(i['type']=='item' and inputs[i['name']]<i['amount']
                                   for i in recipe['ingredients']):
                choice = self.supply_cell(sid, missing, trail)
                if choice:
                    return choice
        pickup = max(missing, {'iron-plate':100,'copper-plate':100,'coal':60,
            'iron-gear-wheel':100,'electronic-circuit':100,'copper-cable':200,
            'transport-belt':100,'inserter':50}.get(item,0))
        def collection_cost(source):
            available=contents(self.entities[source['site']].get(source['inventory']))[item]-source.get('reserve',0)
            stand=self.sites[source['site']]['stand']
            travel=math.hypot(stand['x']-self.o['position']['x'],stand['y']-self.o['position']['y'])
            # Amortize a trip over usable stock. A nearly empty nearest furnace
            # must not monopolize collection while its neighbors hold full stacks.
            return (travel+12)/min(pickup,available) if available>0 else math.inf
        for source in sorted(self.sources(item),key=collection_cost):
            sid = source['site']
            available = contents(self.entities[sid].get(source['inventory']))[item] - source.get('reserve', 0)
            if available > 0:
                growing=any(self.output_location(machine_id)==sid and entity
                    and (entity.get('crafting') or entity.get('status_name')=='working')
                    for machine_id,entity in self.entities.items() if self.sites[machine_id].get('recipe'))
                threshold=min(pickup,2 if item.endswith('science-pack') else 10)
                stand=self.sites[sid]['stand']
                nearby=math.hypot(stand['x']-self.o['position']['x'],stand['y']-self.o['position']['y'])<=.6
                if available<threshold and growing and not nearby:
                    continue
                choice = self.at(sid, dict(type='take', item=item, count=min(pickup, available, 200),
                    inventory=source['inventory']), 'collect:' + item)
                if choice:
                    return choice
        for sid,site in sorted(self.sites.items(),key=lambda row:math.hypot(
                row[1]['position']['x']-self.o['position']['x'],row[1]['position']['y']-self.o['position']['y'])):
            if site.get('gather')==item and sid not in self.consumed_gather:
                return self.at(sid,dict(type='mine',item=item,count=1,timeout=3600),'gather')
        cells = [sid for sid, s in self.sites.items() if s.get('recipe') in self.recipes and
                 any(p['name'] == item for p in self.recipes[s['recipe']]['products'])]
        for sid in cells:
            choice = self.supply_cell(sid, missing, trail)
            if choice:
                return choice
        # Hands can bootstrap solids, but never synthesize chemical/smelted goods.
        recipe = self.recipes.get(item)
        if recipe and recipe['category'] == 'crafting' and item in self.enabled and not cells:
            if self.o.get('crafting'):
                self.reason = 'Normal hand crafting in progress'
                return None
            produced = next(p['amount'] for p in recipe['products'] if p['name'] == item)
            n = min(20, math.ceil(missing / produced))
            budget = craft_budget([(item, n)], self.stock)
            for ingredient, quantity in budget['missing_base'].items():
                choice = self.ensure(ingredient, self.stock[ingredient] + quantity, trail)
                if choice:
                    return choice
            if budget['missing_base']:
                self.reason = 'Missing production/supply for ' + ', '.join(budget['missing_base'])
                return None
            return self.skill('craft:' + item,
                [dict(type='craft', recipe=item, count=n)],
                'Craft available unlocked recipe with actual stock')
        self.reason = 'Waiting for supplied source or configured machine: ' + item
        return None

    def supply_fluid(self, item, trail):
        if item in trail or len(trail)>20:
            self.reason = 'Fluid dependency cycle: ' + item
            return None
        for sid, site in self.sites.items():
            recipe = self.recipes.get(site.get('recipe',''))
            if recipe and any(p['name']==item and p['type']=='fluid' for p in recipe['products']):
                choice = self.supply_cell(sid, 10, (*trail,item))
                if choice:
                    return choice
        self.reason = 'Verify connected pipe supply for ' + item
        return None

    def supply_cell(self, sid, desired, trail):
        site, entity = self.sites[sid], self.entities[sid]
        name = site['recipe']
        recipe = self.recipes[name]
        if name not in self.enabled:
            self.reason = 'Recipe locked: ' + name
            return None
        if not entity:
            if not site.get('build', False):
                self.reason = 'Missing configured machine: ' + sid
                return None
            if self.stock[site['entity']] < 1:
                return self.ensure(site['entity'], 1, trail)
            return self.at(sid, dict(type='place', direction=site.get('direction','north')), 'build')
        if entity.get('recipe') != name and entity['type'] == 'assembling-machine':
            return self.at(sid, dict(type='set_recipe', recipe=name), 'configure')
        count = site.get('batch_size', max(1, min(10, desired)))
        inputs = contents(entity.get('input'))
        input_sid = self.input_location(sid)
        if input_sid != sid:
            buffer = self.entities.get(input_sid)
            if not buffer:
                self.reason = 'Missing input buffer: ' + input_sid
                return None
            inputs.update(contents(buffer.get('chest')))
        if site.get('external_inputs'):
            self.reason = 'Waiting for native inserter supply/output: ' + sid
            return None
        for ingredient in recipe['ingredients']:
            if ingredient['type'] == 'fluid':
                # Fluids must arrive through normal pipes. Never insert them.
                if not any(f['name'] == ingredient['name'] and f['amount'] >= ingredient['amount']
                           for f in entity.get('fluids', [])):
                    choice = self.supply_fluid(ingredient['name'], trail)
                    if choice:
                        return choice
                continue
            item = ingredient['name']
            # Refill in batches instead of replacing each item immediately
            # while another ingredient is the actual production bottleneck.
            if inputs[item] >= max(1,math.ceil(count/2))*ingredient['amount']:
                continue
            missing = max(0, count * ingredient['amount'] - inputs[item])
            if missing:
                if self.stock[item]:
                    return self.at(input_sid, dict(type='put', inventory='chest' if input_sid!=sid else 'input', item=item,
                        count=min(missing, self.stock[item], 100)), 'feed:' + item)
                choice = self.ensure(item, missing, trail)
                if choice:
                    return choice
        self.reason = 'Waiting for actual machine output: ' + sid
        return None

    def maintain_buffers(self):
        ordered=sorted(self.sites.items(),key=lambda pair:math.hypot(
            pair[1]['stand']['x']-self.o['position']['x'],pair[1]['stand']['y']-self.o['position']['y']))
        for sid,site in ordered:
            entity=self.entities[sid]
            if not entity:
                continue
            for item,minimum in site.get('stock_min',{}).items():
                held=contents(entity.get('chest'))[item]
                if held<minimum:
                    amount=site['stock_target'][item]-held
                    if self.stock[item]:
                        return self.at(sid,dict(type='put',inventory='chest',item=item,
                            count=min(amount,self.stock[item])),'buffer:'+item)
                    choice=self.ensure(item,amount)
                    if choice:
                        return choice
        return None

    def maintenance(self):
        equipped = sum(s.get('magazines',0) for s in self.o.get('guns',{}).get('slots',[])
                       if s.get('ammo')=='firearm-magazine')
        if equipped < self.plan.get('engineer_ammo_reserve', 10):
            choice = self.ensure('firearm-magazine', self.plan.get('engineer_ammo_reserve',10)-equipped)
            if choice:
                return choice
        ordered = sorted(self.sites.items(), key=lambda pair: math.hypot(
            pair[1]['stand']['x']-self.o['position']['x'], pair[1]['stand']['y']-self.o['position']['y']))
        for sid, site in ordered:
            entity = self.entities[sid]
            if not entity:
                continue
            remote = math.hypot(site['stand']['x']-self.o['position']['x'],
                                site['stand']['y']-self.o['position']['y']) > 24
            nearby_sources = [s for s in self.plan.get('sources', []) if s['inventory']=='output'
                and math.hypot(self.sites[s['site']]['position']['x']-site['position']['x'],
                               self.sites[s['site']]['position']['y']-site['position']['y']) < 8]
            # A remote burner is not an emergency when finished metal buffers
            # already cover the next work. Refill it on the next collection
            # visit instead of abandoning construction for another round trip.
            buffered = any(self.stock[s['item']] + sum(
                contents(e.get('output'))[s['item']] for e in self.entities.values() if e) >= 30
                for s in nearby_sources)
            for inventory, item, minimum, target in (
                    ('fuel', 'coal', site.get('fuel_min', 0), site.get('fuel_target', 10)),
                    ('ammo', 'firearm-magazine', site.get('ammo_min', 0), site.get('ammo_target', 20))):
                if minimum and contents(entity.get(inventory))[item] < minimum:
                    if inventory=='fuel' and remote and buffered and entity['type']!='boiler':
                        continue
                    if inventory == 'ammo':
                        equipped = sum(s.get('magazines',0) for s in self.o.get('guns',{}).get('slots',[]) if s.get('ammo')==item)
                        spare = max(0, equipped - self.plan.get('engineer_ammo_reserve', 10))
                        if spare:
                            return self.at(sid, dict(type='put', inventory='ammo', player_inventory='ammo',
                                item=item, count=min(target-contents(entity.get('ammo'))[item],spare)), 'maintain:ammo')
                    if self.stock[item]:
                        return self.at(sid, dict(type='put', inventory=inventory, item=item,
                            count=min(target - contents(entity.get(inventory))[item], self.stock[item])),
                            'maintain:' + item)
                    choice = self.ensure(item, max(target,60) if item=='coal' else target)
                    if choice:
                        return choice
        return None

    def choose(self, observation, factory, research):
        self.refresh(observation, factory, research)
        self.reason = ''
        if observation.get('guard', {}).get('active') or observation['health'] < .5*observation['max_health']:
            self.reason = 'Local defense owns inputs'
            return None
        choice = self.finish_service()
        if choice:
            return choice
        choice = self.maintenance()
        if choice:
            return choice
        for sid,site in self.sites.items():
            entity=self.entities[sid]
            if entity and 'chest_slots' in site and entity.get('chest_slots')!=site['chest_slots']:
                return self.at(sid,dict(type='limit_chest',slots=site['chest_slots']), 'limit-stock')
        # Establish power and buffers before a downstream component can demand
        # an assembler that depends on that same infrastructure for its output.
        rank={'small-electric-pole':0,'medium-electric-pole':0,'big-electric-pole':0,
              'substation':0,'wooden-chest':1,'iron-chest':1,'steel-chest':1}
        construction=sorted(self.sites.items(),key=lambda row:rank.get(row[1]['entity'],2))
        for sid, site in construction:
            if any(t not in factory['researched'] for t in site.get('requires', [])):
                continue
            if site.get('build') and (not site.get('recipe') or site.get('eager')) and not self.entities[sid]:
                if self.stock[site['entity']] < 1:
                    queued=any(q.get('recipe')==site['entity'] for q in self.o.get('crafting',[]))
                    if queued:
                        approach=self.at(sid,dict(type='place',direction=site.get('direction','north'),
                            **({'belt_type':site['belt_type']} if 'belt_type' in site else {})), 'build')
                        if approach and all(a['type']=='walk' for a in approach['actions']):
                            return approach
                        # Arrival is not permission to place an item that has
                        # not finished crafting. Reobserve native stock first.
                        self.service_intent=None
                        self.reason='At construction site; waiting for native crafting output'
                        return None
                    remaining=sum(1 for other_id,other in self.sites.items()
                        if other.get('build') and other['entity']==site['entity'] and not self.entities[other_id]
                        and all(t in factory['researched'] for t in other.get('requires',[])))
                    choice = self.ensure(site['entity'], min(remaining,self.plan.get('construction_batch_size',1)))
                else:
                    choice = self.at(sid, dict(type='place', direction=site.get('direction','north'),
                        **({'belt_type':site['belt_type']} if 'belt_type' in site else {})), 'build')
                if choice:
                    return choice
        # Optional production stock must not preempt every construction step.
        # Fuel/ammunition still run first; if construction cannot get a needed
        # component, feeding its upstream buffers can now unblock it.
        choice=self.maintain_buffers()
        if choice:
            return choice
        target = self.plan['target']
        if target=='defense':
            self.reason='Factory defense watch is active'
            return None
        if target == 'infrastructure':
            self.reason = 'Infrastructure placed; verify connections and sustained operation separately'
            return None
        technologies = ['military-2', 'rocket-silo'] if target == 'rocket' else [target]
        pending = research_plan(technologies, factory['researched'])['steps']
        current = factory.get('research')
        if not current and pending:
            step = pending[0]
            if 'trigger' in step:
                trigger = step['trigger']
                if trigger['type']=='craft-item':
                    item = trigger['item']['name']
                    # Existing stock does not prove a native production trigger.
                    # Request additional normal production and wait for the
                    # game to report the technology actually researched.
                    choice = self.ensure(item, self.stock[item]+trigger.get('count',1))
                    if choice:
                        return choice
                self.reason = 'Native production trigger required: ' + step['technology']
                return None
            return self.skill('research:' + step['technology'],
                [dict(type='research', technology=step['technology'])], 'Select next unlocked research')
        if current:
            tech = self.catalog['technologies'][current]
            remaining = max(1, math.ceil(tech['count'] * (1 - factory.get('progress', 0))))
            labs = [(sid, e) for sid, e in self.entities.items() if e and e['type']=='lab']
            if not labs:
                self.reason = 'A configured powered lab is required'
                return None
            # Balance lab-ready research units across colours. Filling every
            # red buffer first can postpone green production while all labs
            # are already blocked on green packs.
            ingredients=sorted(tech['ingredients'], key=lambda ingredient:
                sum(contents(lab.get('input'))[ingredient['name']] for _,lab in labs)
                / ingredient['amount'])
            for ingredient in ingredients:
                item = ingredient['name']
                for sid, lab in sorted(labs, key=lambda p: contents(p[1].get('input'))[item]):
                    held = contents(lab.get('input'))[item]
                    if held < min(10, remaining):
                        if self.stock[item]:
                            return self.at(sid, dict(type='put', inventory='input', item=item,
                                count=min(remaining-held, self.stock[item], 20)), 'supply-science:' + item)
                        choice = self.ensure(item, min(20, remaining-held))
                        if choice:
                            return choice
            self.reason = self.reason or 'Research is progressing; verify actual completion'
        elif not pending:
            if target != 'rocket':
                self.reason = 'Target research verified complete'
                return None
            silos = [(sid,self.entities[sid]) for sid,s in self.sites.items() if s['entity']=='rocket-silo']
            if not silos:
                self.reason = 'Rocket-silo site and production chain required'
                return None
            for sid, silo in silos:
                if silo and silo['rocket_parts'] >= silo['rocket_parts_required']:
                    return self.at(sid, dict(type='launch'), 'launch')
                choice = self.supply_cell(sid, 10, ())
                if choice:
                    return choice
        return None


class Journal:
    def __init__(self, directory, plan, resume=False):
        self.directory = Path(directory).resolve()
        if ROOT / 'runtime' not in self.directory.parents:
            raise ValueError('Run records must stay inside runtime/')
        fingerprint = hashlib.sha256(json.dumps(plan,sort_keys=True).encode()).hexdigest()
        if resume:
            self.state = json.loads((self.directory/'state.json').read_text())
            if self.state['plan_sha256'] != fingerprint:
                raise ValueError('Resume requires the exact recorded plan')
        else:
            self.directory.mkdir(parents=True, exist_ok=False)
            self.state = dict(plan_sha256=fingerprint, pending=None, serial=0)
        self.state.setdefault('run_id', secrets.token_hex(6))
        self.stream = (self.directory/'events.jsonl').open('a' if resume else 'x')
        self.save()

    def save(self):
        temporary = self.directory/'state.tmp'
        temporary.write_text(json.dumps(self.state,indent=2)+'\n')
        temporary.replace(self.directory/'state.json')

    def emit(self, kind, data):
        self.stream.write(json.dumps(dict(kind=kind, wall_epoch=time.time(),
                                         monotonic=time.monotonic(), data=data))+'\n')
        self.stream.flush()


class Runner:
    def __init__(self, game, planner, journal):
        self.game, self.planner, self.journal = game, planner, journal
        self.cursor = EventCursor()
        self.cursor.value = journal.state.get('event_cursor')
        self.actor = journal.state.get('actor')
        self.last_tick = journal.state.get('last_tick')
        self.last_reason = None
        self.neutral_geometry = []
        self.geometry_origin = None
        self.geometry_tick = None
        self.prototypes = {}
        self.started_tick = journal.state.get('started_tick')
        self.failures = Counter(journal.state.get('failures',{}))
        self.planner.stance_attempts.update(journal.state.get('stance_attempts',{}))
        self.planner.blocked_until.update(journal.state.get('blocked_until',{}))
        if any(n>=3 for n in self.failures.values()):
            raise RuntimeError('Repeated failures require a corrected plan and a new journal')
        self.planner.service_intent = journal.state.get("service_intent")
        self.planner.consumed_gather.update(journal.state.get("consumed_gather",[]))
        from .factory_defense import FactoryDefense
        self.factory_defense=FactoryDefense(journal.state.get('factory_defense'))
        self.defense_factory=None
        self.defense_poll_wall=0

    def poll(self):
        status = self.game.request('status', **({} if self.cursor.value is None else {'after': self.cursor.value}))
        for event in self.cursor.consume(status):
            self.journal.emit('game_event', event)
            if event['kind'] in ('factory_damaged','factory_destroyed'):
                self.factory_defense.event(dict(event['detail'],seq=event['seq'],tick=event['tick']))
        self.journal.state['event_cursor'] = self.cursor.value
        if status.get('last_factory_damage'):
            self.factory_defense.event(status['last_factory_damage'])
        self.journal.state['factory_defense']=self.factory_defense.state
        o = self.game.request('observe')
        self.journal.emit('observation', o)
        if o['paused'] or o['speed'] != 1 or not o.get('guard',{}).get('enabled'):
            raise RuntimeError('Runner requires normal-speed unpaused play with local guard enabled')
        if o.get('version') not in ('0.6.0','0.7.0','0.8.0') or o.get('mods',{}).get('base') != '2.0.77':
            raise RuntimeError('Controller/catalog version mismatch')
        if o['version']=='0.6.0' and any('belt_type' in s for s in self.planner.sites.values()):
            raise RuntimeError('Explicit underground endpoints require controller 0.7.0')
        if self.actor is not None and (o['actor_unit'] != self.actor or o['tick'] < self.last_tick):
            raise RuntimeError('Character or world changed; preserve episode and start a new one')
        self.actor, self.last_tick = o['actor_unit'], o['tick']
        if self.started_tick is None:
            self.started_tick = o['tick']
        self.journal.state.update(actor=self.actor, last_tick=self.last_tick, started_tick=self.started_tick)
        self.journal.save()
        pending = self.journal.state['pending']
        # Observe the whole owned factory even while walking/crafting. The
        # engineer-local reflex does not report remote buildings being attacked.
        if self.planner.plan.get('defense_stations') and time.monotonic()-self.defense_poll_wall>=.5:
            self.defense_factory=self.game.request('factory')
            damage=self.factory_defense.observe(self.defense_factory)
            self.defense_poll_wall=time.monotonic()
            self.journal.state['factory_defense']=self.factory_defense.state
            if damage:
                self.journal.emit('factory_damage_detected',dict(tick=self.defense_factory['tick'],damage=damage))
                print('Factory damage detected; defense takes priority',flush=True)
            self.journal.save()
        alarm=self.factory_defense.state['alarm']
        if alarm and pending and not pending['key'].startswith('factory-defense:') and o.get('job',{}).get('status')=='running':
            # The existing fixed cancel also disables the local guard. Restore
            # it immediately before doing any new work, preserving its rally.
            pending['factory_defense_cancelled']=True
            self.journal.save()
            guard=o.get('guard',{})
            try:
                result=self.game.request('interrupt' if o['version']=='0.8.0' else 'cancel',id=pending['id'])
                self.journal.emit('factory_defense_preempted',result)
            finally:
                if o['version']!='0.8.0':
                    self.game.request('guard',enabled=True,**({'rally':guard['rally']} if guard.get('rally') else {}))
            return False
        if pending:
            job = self.game.request('status', id=pending['id'])
            if job['status'] == 'running':
                return False
            if job.get('id') != pending['id'] or job['status'] not in ('complete','failed','cancelled'):
                raise RuntimeError('Pending job outcome unknown; no replay')
            self.journal.emit('job_reconciled', dict(skill=pending, result=job))
            self.journal.state['pending'] = None
            if job['status']=='complete' and pending['key'].startswith('gather:'):
                self.planner.consumed_gather.add(pending['key'].split(':',1)[1])
                self.journal.state['consumed_gather']=sorted(self.planner.consumed_gather)
            self.journal.save()
            if job['status'] != 'complete':
                if job.get('error') not in ('defense_interrupt','factory_defense_interrupt') and not pending.get('factory_defense_cancelled'):
                    self.failures[pending['key']] += 1
                    if pending['key'].startswith('approach:') or 'out_of_reach' in job.get('error',''):
                        sid = pending['key'].rsplit(':',1)[1]
                        self.planner.stance_attempts[sid] += 1
                    self.planner.blocked_until[pending['key']] = o['tick'] + 600
                    self.journal.state.update(failures=dict(self.failures),
                        stance_attempts=dict(self.planner.stance_attempts),
                        blocked_until=self.planner.blocked_until)
                    self.journal.save()
                    if self.failures[pending['key']] >= 3:
                        raise RuntimeError('Repeated skill failure: ' + pending['key'])
                # Never continue a cancelled batch. Choose again from fresh state.
                return False
        elif o.get('job',{}).get('status') == 'running':
            raise RuntimeError('Another executor owns the engineer')
        if o.get('guard',{}).get('active'):
            return False
        f, r = self.game.request('factory'), self.game.request('research_state')
        self.journal.emit('factory', f)
        # Nearby neutral wrecks/trees are absent from the owned-factory snapshot.
        # Exclude their observed bounds from service stances without exposing any
        # uncharted entity or pretending that a truncated scan proves clearance.
        if (self.geometry_origin is None or o['tick']-self.geometry_tick>=600
                or math.dist(tuple(o['position'][k] for k in ('x','y')),
                             tuple(self.geometry_origin[k] for k in ('x','y')))>=8):
            from .obstacles import neutral_bounds, SOLID_TYPES
            scan=self.game.request('scan',radius=16,limit=100)
            for e in scan['entities']:
                if e.get('force')=='neutral' and e.get('type') in SOLID_TYPES and e['name'] not in self.prototypes:
                    self.prototypes[e['name']]=self.game.request('prototype',entity=e['name'])
            self.neutral_geometry=neutral_bounds(scan,self.prototypes)
            self.geometry_origin=dict(o['position']);self.geometry_tick=o['tick']
            self.journal.emit('nearby_geometry',dict(scan=scan,obstacles=self.neutral_geometry))
        f['obstacles']=self.neutral_geometry
        if any(e.get('by_script') for e in f.get('research_events',{}).values()):
            raise RuntimeError('Script-completed research is not a compliant milestone')
        if self.planner.plan['target'] == 'infrastructure':
            from .belt_routes import NATIVE_DIRECTIONS
            self.planner.refresh(o, f, r)
            requested = [s for s in self.planner.sites.values() if s.get('build')]
            done = bool(requested) and all(self.planner.entities[s['id']] and
                (s['entity'] not in ('transport-belt','underground-belt') or
                 (self.planner.entities[s['id']].get('direction') == NATIVE_DIRECTIONS[s.get('direction', 'north')]
                  and (s['entity']!='underground-belt' or self.planner.entities[s['id']].get('belt_type')==s.get('belt_type','input'))))
                for s in requested)
        elif self.planner.plan['target']=='defense':
            done=False
        elif self.planner.plan['target'] == 'rocket':
            done = any(e['tick'] > self.started_tick for e in f.get('launches', []))
        else:
            done = self.planner.plan['target'] in f['researched']
        if done:
            if not self.journal.state.get('target_verified'):
                self.journal.emit('target_verified', dict(target=self.planner.plan['target'], factory=f))
                self.journal.state['target_verified']=True
                self.journal.save()
            if not self.planner.plan.get('watch_after_target') and not alarm:
                return True
        choice=self.factory_defense.response(o,f,self.planner.plan)
        if choice and not choice['actions']:
            self.journal.emit('factory_defense_waiting',choice)
            return False
        if not choice:
            if done or self.journal.state.get('production_suspended'):
                self.planner.refresh(o,f,r)
                choice=self.planner.maintenance()
                self.planner.reason=('Construction suspended; factory defense watch remains active'
                    if self.journal.state.get('production_suspended') else
                    'Target verified; factory defense watch remains active')
            else:
                choice = self.planner.choose(o, f, r)
        self.journal.state['service_intent'] = self.planner.service_intent
        self.journal.save()
        if not choice:
            if self.planner.reason != self.last_reason:
                self.journal.emit('waiting', {'reason': self.planner.reason})
                print(self.planner.reason, flush=True)
                self.last_reason = self.planner.reason
            return False
        from .belt_routes import nearby_belt_batch
        if choice['actions'][0].get('entity') == 'transport-belt' and choice['actions'][0]['type'] == 'place':
            choice = nearby_belt_batch(choice, self.planner.sites, self.planner.entities, o, f['researched'])
        for action in choice['actions']:
            if action['type']=='mine' and choice['key'].startswith('gather:'):
                nearby=self.game.request('scan',name=action['entity'],radius=10,limit=100)
                self.journal.emit('gather_preflight',nearby)
                if not any(abs(e['x']-action['x'])<.2 and abs(e['y']-action['y'])<.2 for e in nearby['entities']):
                    if nearby.get('truncated'):
                        raise RuntimeError('Gather preflight is truncated; cannot infer absence')
                    self.planner.consumed_gather.add(choice['key'].split(':',1)[1])
                    self.journal.state['consumed_gather']=sorted(self.planner.consumed_gather)
                    self.journal.save()
                    return False
            if action['type']=='place':
                check = self.game.request('placement', **{k:action[k]
                    for k in ('entity','x','y','direction') if k in action})
                self.journal.emit('placement_preflight', check)
                if not check['can_place']:
                    if self.planner.plan.get('clear_belt_trees') and action['entity']=='transport-belt':
                        from .construction import clear_tree_for_belt
                        scan=self.game.request('scan',type='tree',radius=10,limit=100)
                        for tree in scan['entities']:
                            if tree['name'] not in self.prototypes:
                                self.prototypes[tree['name']]=self.game.request('prototype',entity=tree['name'])
                        self.journal.emit('tree_clearance_scan',scan)
                        recovery=clear_tree_for_belt(action,o,f,scan,self.prototypes)
                        if recovery and self.planner.blocked_until.get(recovery['key'],0)<=o['tick']:
                            choice=recovery
                            break
                    reason='Configured footprint is blocked: '+choice['key']
                    if not self.planner.plan.get('defense_stations'):
                        raise RuntimeError(reason)
                    # A rejected footprint has not submitted any part of this
                    # batch. Keep monitoring and defensive maintenance alive
                    # while a corrected plan is prepared, including on resume.
                    self.planner.service_intent=None
                    self.journal.state.update(service_intent=None,production_suspended=
                        dict(reason=reason,tick=o['tick'],action=dict(action)))
                    self.journal.save()
                    self.journal.emit('production_suspended',self.journal.state['production_suspended'])
                    print(reason+'; defense watch remains active',flush=True)
                    return False
        self.journal.state['serial'] += 1
        job = dict(choice, id='auto-' + self.journal.state.get('run_id',self.journal.directory.name)
                   + '-' + str(self.journal.state['serial']))
        # Write intent durably BEFORE sending. On uncertainty the process exits
        # with this exact ID available; no implicit retry or new-ID submission.
        self.journal.state['pending'] = job
        self.journal.save()
        self.journal.emit('intent', job)
        result = self.game.request('submit', id=job['id'], actions=job['actions'],
            **({'defense':choice['key'].startswith('factory-defense:')} if o['version']=='0.8.0' else {}))
        self.journal.emit('submitted', result)
        print(choice['key'], flush=True)
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seconds', type=float, default=600)
    parser.add_argument('--resume', action='store_true', help='Reconcile the exact recorded pending job before continuing')
    args = parser.parse_args()
    if not math.isfinite(args.seconds) or not 0 < args.seconds <= 14400:
        raise ValueError('Duration must be 1-14400 seconds')
    plan = load_plan(args.plan)
    # One local process may own production; the in-game reflex remains separate.
    with (ROOT/'runtime/autopilot.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        journal = Journal(args.output, plan, resume=args.resume)
        journal.emit('manifest', {'plan':plan, 'mode':'bounded-normal-mechanics',
            'resumed':args.resume,
            'source_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
                for name in ('client/autopilot.py','client/routes.py','client/materials.py',
                             'client/progression.py','client/agent.py','client/obstacles.py',
                             'client/belt_routes.py','client/construction.py','client/factory_defense.py','data/catalog-2.0.77.json')}})
        try:
            with Agent() as game:
                runner = Runner(game, Planner(plan), journal)
                end = time.monotonic() + args.seconds
                while time.monotonic() < end:
                    start = time.monotonic()
                    if runner.poll():
                        print('Target verified in game', flush=True)
                        return
                    time.sleep(max(0, .1 - (time.monotonic()-start)))
                journal.emit('deadline', {'pending':journal.state['pending'],
                                         'game_paused':False, 'job_may_continue':True})
        except BaseException as exc:
            journal.emit('runner_stopped', {'error':type(exc).__name__, 'message':str(exc),
                                           'pending':journal.state['pending']})
            raise
        finally:
            journal.stream.close()


if __name__ == '__main__':
    main()
