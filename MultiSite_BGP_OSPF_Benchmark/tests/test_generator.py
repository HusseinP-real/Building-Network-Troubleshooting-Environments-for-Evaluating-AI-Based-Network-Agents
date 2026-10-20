import json,unittest,ipaddress
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class TopologyTest(unittest.TestCase):
 def setUp(self):self.d=json.loads((ROOT/'inventory.json').read_text())
 def test_counts(self):self.assertEqual((self.d['router_count'],self.d['switch_count'],self.d['endpoint_count']),(18,20,42))
 def test_subnets(self):
  for h,d in self.d['hosts'].items():
   subnet=self.d['external_networks'][d['site']] if d['site'] in self.d['external_networks'] else self.d['site_networks'][d['site']]
   self.assertIn(ipaddress.ip_address(d['ip']),ipaddress.ip_network(subnet))
   self.assertIn(ipaddress.ip_address(d['gateway']),ipaddress.ip_network(subnet))
 def test_no_duplicate_addresses(self):
  values=[x['addr'] for entries in self.d['interfaces'].values() for x in entries if x['addr']]
  self.assertEqual(len(values),len(set(values)))
 def test_all_three_faults(self):
  for fid in ('F01','F02','F03'):
   self.assertTrue((ROOT/'scenarios'/fid/'ground_truth.json').is_file())
   self.assertEqual(len(json.loads((ROOT/'scenarios'/fid/'tickets.json').read_text())),4)
 def test_router_forwarding_at_container_creation(self):
  conf=(ROOT/'lab.conf').read_text()
  startup=(ROOT/'e1.startup').read_text()
  self.assertIn('e1[sysctl]="net.ipv4.ip_forward=1"',conf)
  self.assertNotIn('sysctl -w net.ipv4.ip_forward',startup)
  self.assertIn('ROUTER_STARTUP_COMPLETE',startup)
if __name__=='__main__':unittest.main()
