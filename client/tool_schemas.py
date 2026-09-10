"""Bounded MCP tool contracts for controller 0.8.0, with no generic operation tool.

These schemas restrict shape and bounds. The mod remains authoritative for
unlocks, item costs, reach, collision, ownership, and all gameplay preconditions.
"""


def obj(properties=None, required=(), **constraints):
    return dict(type="object", properties=properties or {}, required=list(required),
                additionalProperties=False, **constraints)


def integer(low, high):
    return dict(type="integer", minimum=low, maximum=high)


def number(low, high):
    return dict(type="number", minimum=low, maximum=high)


NAME = dict(type="string", minLength=1, maxLength=120, pattern=r"^[A-Za-z0-9_-]+(?![\s\S])")
COORD = number(-1000000, 1000000)
COUNT = integer(1, 100000)
TICKS = integer(1, 216000)
INVENTORY = dict(type="string", enum=["fuel", "source", "result", "chest", "input", "output", "ammo"])
PLAYER_INVENTORY = dict(type="string", enum=["main", "ammo"])
DIRECTION = dict(type="string", enum=[
    "north", "northeast", "east", "southeast", "south", "southwest", "west", "northwest"])
POSITION = dict(x=COORD, y=COORD)
ENTITY = dict(**POSITION, entity=NAME)


def action(kind, properties=None, required=(), **constraints):
    return obj(dict(type=dict(const=kind), timeout=TICKS, **(properties or {})),
               ("type", *required), **constraints)


ACTIONS = [
    action("walk", dict(**POSITION, tolerance=number(0.1, 10)), ("x", "y")),
    action("mine", dict(**ENTITY, item=NAME, count=COUNT), ("x", "y", "count")),
    action("craft", dict(recipe=NAME, count=COUNT), ("recipe", "count")),
    action("await_craft"),
    action("place", dict(**ENTITY, item=NAME, direction=DIRECTION,
                        belt_type=dict(type="string", enum=["input", "output"])), ("x", "y", "entity")),
    action("put", dict(**ENTITY, item=NAME, count=COUNT, inventory=INVENTORY, player_inventory=PLAYER_INVENTORY),
           ("x", "y", "item", "count")),
    action("take", dict(**ENTITY, item=NAME, count=COUNT, inventory=INVENTORY, player_inventory=PLAYER_INVENTORY),
           ("x", "y", "item", "count")),
    action("wait_inventory", dict(**ENTITY, item=NAME, count=COUNT, inventory=INVENTORY),
           ("item", "count"), dependentRequired={
               "x": ["y"], "y": ["x"], "entity": ["x", "y"], "inventory": ["x", "y"]}),
    action("research", dict(technology=NAME), ("technology",)),
    action("set_recipe", dict(**ENTITY, recipe=NAME), ("x", "y", "recipe")),
    action("rotate", ENTITY, ("x", "y")),
    action("wait_ticks", dict(ticks=TICKS), ("ticks",)),
    action("limit_chest", dict(**ENTITY, slots=integer(0,1000)), ("x","y","entity","slots")),
    action("launch", ENTITY, ("x", "y", "entity")),
]

# Every entry is a fixed operation; caller-supplied op/code/console fields fail
# validation. Keep all defaults in the mod so repeated job fingerprints match.
TOOLS = {
    "prototype": (obj(dict(entity=NAME), ("entity",)), "Read static entity geometry, fluid ports and supported mining/pole dimensions. Contains no world state."),
    "hello": (obj(), "Read controller version and supported operations; does not bind an engineer."),
    "bind": (obj(dict(player=integer(1, 65535))),
             "Bind a connected player's existing engineer under normal game rules. Default player is 1."),
    "release": (obj(), "Return the engineer to the viewer and cancel the remaining active batch."),
    "observe": (obj(), "Read engineer state, main and ammunition inventories, crafting, pause state, and current job."),
    "scan": (obj(dict(name=NAME, type=NAME, radius=number(1, 128), limit=integer(1, 100))),
             "Scan charted surroundings only. Defaults: radius 64, limit 20. Optional name/type filters."),
    "inspect": (obj(ENTITY, ("x", "y")),
                "Inspect an entity within engineer reach, optionally selected by exact entity name."),
    "survey": (obj(dict(radius=number(1, 128), limit=integer(1, 100))),
               "Read nearby charted water tiles and chunk pollution. Defaults: radius 64, water limit 100. "
               "Tile coordinates are top-left corners; chunk coordinates represent 32x32 tiles. "
               "Does not reveal unexplored terrain or establish that no distant enemies exist."),
    "placement": (obj(dict(**ENTITY, direction=DIRECTION), ("x", "y", "entity")),
                  "Read normal character placement preflight within 10 tiles on charted terrain. "
                  "Checks current stance and collisions; does not place or reserve an item. "
                  "Run while unpaused: paused checks return false even at valid sites. "
                  "Does not prove power, fluid or inserter connectivity. Recheck at execution."),
    "factory": (obj(), "Read the player's factory, inventories, fluids, power-network IDs, machine output, "
                "research completion records, and actual rocket-launch events. Launch-order success is not completion."),
    "research_state": (obj(), "Read completed technologies, enabled recipe names, and supported production counters."),
    "guard": (obj(dict(enabled=dict(type="boolean"), rally=obj(POSITION, ("x", "y"))), ("enabled",)),
              "Enable or disable experimental tick-local bullet defense using equipped weapons and normal ammunition. "
              "Optional rally must be within 64 tiles on charted terrain; this does not establish route safety. "
              "Interrupts remaining production work on nearby visible threats, recent damage or critical health. "
              "Does not equip missing items, model acid, or guarantee survival. Default off. Cancel disables it."),
    "submit": (obj(dict(id=NAME, defense=dict(type="boolean"), actions=dict(type="array", minItems=1, maxItems=512,
                                             items=dict(oneOf=ACTIONS))), ("id", "actions")),
               "Submit one item-funded, tick-executed batch and return immediately. One active job. "
               "Use a stable unique id; same id/actions retrieves existing work, changed actions conflict. "
               "A failure preserves completed steps. After a lost reply, query status with the SAME id; "
               "never resubmit with a new id. Cancellation of an MCP call does not stop a game job. "
               "Optional defense marks response work exempt from remote factory interruption, not local combat. "
               "Use cancel explicitly; queued hand crafting continues. All durations are game ticks."),
    "status": (obj(dict(id=NAME, after=integer(0, 9007199254740991))),
               "Read a job by id (or current job), including up to 100 events after a sequence cursor. "
               "Retains last_damage/last_death after engineer death; exposes guard state and events_lost. "
               "To page events use the last returned event seq, not the overall sequence. "
               "A client timeout does not stop the game. Reconcile uncertain submissions here."),
    "interrupt": (obj(dict(id=NAME), ("id",)),
                  "Preempt the exact active job while preserving the local combat guard. Requires controller 0.8.0."),
    "cancel": (obj(dict(id=NAME)),
               "Stop the remaining active batch and walking/mining. Pass its id to guard against "
              "cancelling another job. Also disables the reflex guard. Completed actions and queued hand crafting remain."),
    "pause": (obj(dict(value=dict(type="boolean")), ("value",)),
              "Explicitly pause (true) or resume (false) the simulation. Pauses are logged."),
    "save": (obj(dict(name=NAME), ("name",)),
             "Request a private server checkpoint by simple name. May overwrite the same name. "
             "Acknowledgement proves a save request, not completed file creation or a milestone."),
}
READ_ONLY = frozenset({"prototype", "hello", "observe", "scan", "survey", "placement", "inspect", "factory", "research_state", "status"})
