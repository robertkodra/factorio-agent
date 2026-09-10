import unittest
from client.factory_defense import FactoryDefense


def factory(tick,health):
    return dict(tick=tick,entities=[dict(id=1,name='transport-belt',type='transport-belt',
        health=health,position=dict(x=100,y=100)),dict(id=2,name='gun-turret',type='ammo-turret',
        health=400,position=dict(x=98,y=98),ammo=[dict(name='firearm-magazine',count=20)])])


class FactoryDefenseTests(unittest.TestCase):
    def test_bounded_native_alarm_retains_recently_updated_entity(self):
        d=FactoryDefense()
        for seq in range(1,33):
            d.event(dict(seq=seq,tick=seq,id=seq,health=100))
        update=dict(seq=33,tick=33,id=1,health=50)
        d.event(update)
        self.assertFalse(d.event(update))
        d.event(dict(seq=34,tick=34,id=33,health=100))
        damage=d.state['alarm']['damage']
        self.assertEqual(len(damage),32)
        self.assertEqual([e['id'] for e in damage],list(range(3,33))+[1,33])
        self.assertEqual(damage[-2]['health'],50)

    def test_bounded_health_alarm_retains_recently_updated_entity(self):
        d=FactoryDefense()
        f=dict(tick=1,entities=[dict(id=i,name='transport-belt',type='transport-belt',
               health=100,position=dict(x=i,y=0)) for i in range(1,34)])
        d.observe(f)
        for seq in range(1,33):
            d.event(dict(seq=seq,tick=seq,id=seq,health=100))
        f['tick']=34
        f['entities'][0]['health']=50
        f['entities'][-1]['health']=90
        d.observe(f)
        damage=d.state['alarm']['damage']
        self.assertEqual(len(damage),32)
        self.assertEqual([e['id'] for e in damage],list(range(3,33))+[1,33])
        self.assertEqual(damage[-2]['health'],50)

    def test_remote_damage_detected_without_engineer_damage_and_repair_is_not_attack(self):
        d=FactoryDefense()
        self.assertEqual(d.observe(factory(10,100)),[])
        self.assertEqual(d.observe(factory(40,90))[0]['lost'],10)
        self.assertEqual(d.observe(factory(70,100)),[])
        self.assertEqual(d.state['alarm']['tick'],40)

    def test_dispatch_requires_loaded_station_and_holds_until_quiet(self):
        d=FactoryDefense();d.observe(factory(10,100));f=factory(40,90);d.observe(f)
        site=dict(id='station',entity='gun-turret',position=dict(x=98,y=98),stand=dict(x=96,y=98))
        plan=dict(sites=[site],defense_stations=['station'])
        o=dict(position=dict(x=0,y=0),tick=40)
        self.assertEqual(d.response(o,f,plan)['actions'][0]['type'],'walk')
        o['position']=site['stand'];self.assertEqual(d.response(o,f,plan)['key'],'factory-defense:hold')
        o['tick']=641;self.assertIsNone(d.response(o,f,plan));self.assertIsNone(d.state['alarm'])
        d.observe(factory(650,80));f['entities'][1]['ammo']=[]
        self.assertEqual(d.response(o,f,plan)['key'],'factory-defense:uncovered')

    def test_removed_entity_is_not_invented_damage_event(self):
        d=FactoryDefense();d.observe(factory(10,100))
        self.assertEqual(d.observe(dict(tick=20,entities=[])),[])
        with self.assertRaises(RuntimeError):d.observe(factory(19,100))

    def test_native_destruction_survives_missing_entity_and_deduplicates(self):
        d=FactoryDefense()
        record=dict(seq=3,tick=30,id=9,entity='transport-belt',position=dict(x=1,y=2),kind='destroyed')
        self.assertTrue(d.event(record))
        self.assertFalse(d.event(record))
        d.observe(dict(tick=35,entities=[]))
        self.assertEqual(d.state['alarm']['damage'][0]['id'],9)
        self.assertEqual(d.state['alarm']['tick'],30)

    def test_health_poll_preserves_other_pending_native_destruction(self):
        d=FactoryDefense();d.observe(factory(10,100))
        d.event(dict(seq=1,tick=20,id=9,entity='stone-furnace',
                     position=dict(x=110,y=100),kind='destroyed'))
        d.observe(factory(30,90))
        alarm={e['id']:e for e in d.state['alarm']['damage']}
        self.assertEqual(set(alarm),{1,9})
        self.assertEqual(alarm[9]['kind'],'destroyed')
        self.assertEqual(d.state['alarm']['tick'],30)
