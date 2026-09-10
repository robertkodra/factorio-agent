"""Exercise the real Lua progress tracker with stationary and oscillating traces."""
import shutil
import subprocess
import unittest
from client.agent import ROOT


class NavigationTests(unittest.TestCase):
    def test_lua_underground_placement(self):
        lua = shutil.which('lua5.2') or shutil.which('lua') or shutil.which('luajit')
        if not lua:
            self.skipTest('Install Lua to run underground placement tests')
        result = subprocess.run([lua, 'tests/underground_test.lua'], cwd=ROOT,
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_lua_manufacturing_observations(self):
        lua = shutil.which('lua5.2') or shutil.which('lua') or shutil.which('luajit')
        if not lua:
            self.skipTest('Install Lua to run manufacturing observation tests')
        result = subprocess.run([lua, 'tests/manufacturing_test.lua'], cwd=ROOT,
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_lua_job_history(self):
        lua = shutil.which('lua5.2') or shutil.which('lua') or shutil.which('luajit')
        if not lua:
            self.skipTest('Install Lua to run receipt tests')
        result = subprocess.run([lua, 'tests/job_history_test.lua'], cwd=ROOT,
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_lua_rocket_evidence(self):
        lua = shutil.which('lua5.2') or shutil.which('lua') or shutil.which('luajit')
        if not lua:
            self.skipTest('Install Lua to run rocket evidence tests')
        result = subprocess.run([lua, 'tests/rocket_test.lua'], cwd=ROOT,
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_lua_reflex_controller(self):
        lua = shutil.which('lua5.2') or shutil.which('lua') or shutil.which('luajit')
        if not lua:
            self.skipTest('Install Lua 5.2 or LuaJIT to run reflex tests')
        result = subprocess.run([lua, 'tests/reflex_test.lua'], cwd=ROOT,
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_lua_combat_observations(self):
        lua = shutil.which('lua5.2') or shutil.which('lua') or shutil.which('luajit')
        if not lua:
            self.skipTest('Install Lua 5.2 or LuaJIT to run combat observation tests')
        result = subprocess.run([lua, 'tests/combat_observation_test.lua'], cwd=ROOT,
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_lua_inventory_routing(self):
        lua = shutil.which('lua5.2') or shutil.which('lua') or shutil.which('luajit')
        if not lua:
            self.skipTest('Install Lua 5.2 or LuaJIT to run inventory tests')
        result = subprocess.run([lua, 'tests/inventory_test.lua'], cwd=ROOT,
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_lua_player_crafting(self):
        lua = shutil.which('lua5.2') or shutil.which('lua') or shutil.which('luajit')
        if not lua:
            self.skipTest('Install Lua 5.2 or LuaJIT to run the player crafting test')
        result = subprocess.run([lua, 'tests/crafting_test.lua'], cwd=ROOT,
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_lua_observation_boundaries(self):
        lua = shutil.which('lua5.2') or shutil.which('lua') or shutil.which('luajit')
        if not lua:
            self.skipTest('Install Lua 5.2 or LuaJIT to run observation boundary tests')
        result = subprocess.run([lua, 'tests/observations_test.lua'], cwd=ROOT,
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_lua_progress_tracker(self):
        lua = shutil.which('lua5.2') or shutil.which('lua') or shutil.which('luajit')
        if not lua:
            self.skipTest('Install Lua 5.2 or LuaJIT to run the navigation trace test')
        result = subprocess.run([lua, 'tests/navigation_test.lua'], cwd=ROOT,
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        result = subprocess.run([lua, '-e', "assert(loadfile('mod/codex-controller/control.lua'))"],
                                cwd=ROOT, text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
