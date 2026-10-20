"""Offline regression tests; they do not certify live Kath3 connectivity."""
import unittest
from unittest.mock import Mock,patch
import validate_client_demo as demo
from faultbench.scenario import classify_scenario, discover_scenarios

class ClientDemoTests(unittest.TestCase):
 def test_native_scenarios_and_manifest(self):
  cases=demo.specs()
  self.assertEqual(set(cases),{'healthy','gateway','filter','compound'})
  self.assertIsNone(cases['healthy'].injection.command)
  self.assertEqual(cases['healthy'].scenario_class,'false-premise')
 def test_existing_complex_topology_inventory(self):
  inventory=demo.topology_inventory()
  self.assertEqual(inventory['device_count'],32)
  nodes=inventory['devices']
  self.assertEqual(sum(n.startswith('router') for n in nodes),7)
  self.assertEqual(sum('switch' in n for n in nodes),10)
  self.assertTrue(all(len(ends)>1 for ends in inventory['connected_segments'].values()))
 def test_new_cases_do_not_enter_published_scopes(self):
  custom={s.source_path for s in demo.specs().values()}
  self.assertFalse(custom.intersection(discover_scenarios('all')))
 def test_healthy_and_fault_patterns_are_distinct(self):
  expected={case:{cmd:expect for _,cmd,expect in demo.checks(case)} for case in demo.IDS}
  ping='ping -W2 -c2 172.16.10.4'
  self.assertEqual(expected['gateway'][ping],'loss>0')
  self.assertEqual(expected['filter'][ping],'0% loss')
 def test_two_consecutive_passes_required(self):
  with patch.object(demo,'run_stage',side_effect=[True,False,True,True]) as stage,patch.object(demo.time,'sleep'):
   demo.converge(Mock(),{},'baseline',[],60)
  self.assertEqual(stage.call_count,4)
 def test_baseline_failure_prevents_injection(self):
  lab=Mock()
  with patch.object(demo,'converge',side_effect=RuntimeError('baseline failed')):
   with self.assertRaises(RuntimeError):demo.cycle(lab,{},'gateway',Mock(),1)
  lab.mutate.assert_not_called()
 def test_fault_failure_still_repairs(self):
  lab=Mock();sc=Mock(injection=Mock(command='inject'),post_inject_check=[])
  with patch.object(demo,'converge',side_effect=[None,RuntimeError('check failed')]),patch.object(demo,'restore') as restore:
   with self.assertRaises(RuntimeError):demo.cycle(lab,{},'gateway',sc,1)
  restore.assert_called_once_with(lab)
 def test_both_repairs_attempted_if_first_fails(self):
  lab=Mock();lab.mutate.side_effect=[RuntimeError('route failure'),None]
  with self.assertRaises(RuntimeError):demo.restore(lab)
  self.assertEqual(lab.mutate.call_count,2)
  self.assertNotIn('iptables -F',str(lab.mutate.call_args_list))
 def test_filter_injection_is_idempotent_and_tagged(self):
  command=demo.specs()['filter'].injection.command
  self.assertIn('iptables -C',command)
  self.assertIn('haosenpeng-compound-icmp',command)
  self.assertIn('iptables -I OUTPUT 1',command)

if __name__=='__main__':unittest.main()
