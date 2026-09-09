"""Exact batch-rounded material budgeting from the running game's recipe export."""
import json
import math
from collections import Counter
from .agent import ROOT

CATALOG = ROOT / 'data/catalog-2.0.77.json'

BASE = {'iron-plate','copper-plate','stone','wood','coal','water','crude-oil'}


def _calculate(wanted, inventory=None, crafts=None):
    recipes=json.loads(CATALOG.read_text())['recipes']
    stock=Counter(inventory or {})
    missing=Counter();batches=Counter();seconds=0
    def need(item, amount):
        nonlocal seconds
        used=min(stock[item],amount);stock[item]-=used;amount-=used
        if amount<=0:return
        if item in BASE or item not in recipes:
            missing[item]+=amount;return
        recipe=recipes[item]
        if crafts is not None and recipe['category'] != 'crafting':
            # Available intermediates may be used, but hand crafting cannot
            # manufacture missing smelted, chemical or fluid ingredients.
            missing[item]+=amount;return
        product=next(p for p in recipe['products'] if p['name']==item)
        if product.get('probability',1)!=1 or 'amount' not in product:
            raise ValueError('Non-deterministic recipe requires a separate model: '+item)
        count=math.ceil(amount/product['amount'])
        for ingredient in recipe['ingredients']:
            need(ingredient['name'],count*ingredient['amount'])
        batches[item]+=count;seconds+=count*recipe['energy']
        stock[item]+=count*product['amount']-amount
    if crafts is None:
        for item, amount in wanted.items():need(item,amount)
    else:
        for name, count in crafts:
            if isinstance(count,bool) or not isinstance(count,int) or count<1:
                raise ValueError('Craft counts must be positive integers')
            recipe=recipes[name]
            if recipe['category'] != 'crafting':
                raise ValueError('Recipe is not supported for hand crafting: '+name)
            for product in recipe['products']:
                if product.get('probability',1)!=1 or 'amount' not in product or product['type']!='item':
                    raise ValueError('Craft products must be deterministic items: '+name)
            for ingredient in recipe['ingredients']:
                if ingredient['type']!='item':raise ValueError('Fluid hand crafting is unsupported')
                need(ingredient['name'],count*ingredient['amount'])
            batches[name]+=count;seconds+=count*recipe['energy']
            for product in recipe['products']:stock[product['name']]+=count*product['amount']
    return dict(missing_base=dict(missing),recipe_batches=dict(batches),nominal_recipe_seconds=seconds,leftovers={k:v for k,v in stock.items() if v})


def budget(wanted, inventory=None):
    """Budget desired final item quantities, crediting items already in stock."""
    return _calculate(wanted, inventory)


def craft_budget(crafts, inventory=None):
    """Budget ordered (recipe, batch count) crafts, even if their products exist.

    Missing non-handcraftable intermediates are requirements, not free crafts.
    Recipe unlocks and queued work still need a live check. In this mode
    ``missing_base`` can include such intermediates as engine units or steel.
    """
    return _calculate({}, inventory, crafts=crafts)


if __name__=='__main__':
    import sys
    print(json.dumps(budget(json.loads(sys.argv[1])),indent=2))
