"""Prevent truth leakage, misleading empty scores and broken fresh-checkout tools."""
import copy,json,os,shutil,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'faultbench/src'))
sys.path.insert(0,str(ROOT))

class GroundTruthAndPublication(unittest.TestCase):
    def test_catalog_truth_and_evidence_match_source_bytes(self):
        import hashlib
        records=[json.loads(line) for line in (ROOT/'ground_truth/scenarios.jsonl').read_text().splitlines()]
        self.assertEqual(len(records),json.loads((ROOT/'ground_truth/audit.json').read_text())['scenarios'])
        self.assertGreaterEqual(len(records),11)
        self.assertEqual(len({r['scenario_id'] for r in records}),len(records))
        self.assertTrue(all(r['root_cause_and_reference'] for r in records))
        for r in records:self.assertEqual(hashlib.sha256((ROOT/r['source_path']).read_bytes()).hexdigest(),r['source_sha256'])
        controls=[r for r in records if r['scenario_id'] in ['jiayuan75-false-premise-internal-application','nika92-false-premise-pod1-web']]
        self.assertEqual(len(controls),2)
        self.assertTrue(all(not r['expected_anomaly'] and not r['injection']['command'] for r in controls))

    def test_all_team_inventories_cover_actual_constructed_labs(self):
        from faultbench.ground_truth import get_labs
        from faultbench.inventory import apply_roles
        from types import SimpleNamespace
        inventories=json.loads((ROOT/'ground_truth/topologies.json').read_text())
        labs,errors=get_labs({r['topology'] for r in inventories});self.assertFalse(errors)
        for name,lab in labs.items():
            lab.name=name
            api=SimpleNamespace(lab=lab)
            self.assertTrue(apply_roles(api,topology=name),name)
            self.assertEqual(len(api.routers)+len(api.switches)+len(api.hosts)+sum(len(x) for x in api.servers.values()),len(lab.machines))

    def test_scoped_catalog_contains_complete_delivery_cases(self):
        from faultbench.ground_truth import build
        names={'Kath5_Jiayuan_75Devices','NIKA_Clos_Jiayuan_92Devices'}
        data=build(names)
        expected={p.stem for folder in ('jiayuan75_Q','nika92_Q') for p in (ROOT/'dataset'/folder/'custom').glob('*.txt')}
        self.assertEqual({r['scenario_id'] for r in data['records']},expected)
        self.assertEqual({t['topology'] for t in data['topologies']},names)
        self.assertFalse(data['parse_errors'])
        self.assertFalse(data['topology_errors'])

    def test_nika_export_is_independent_of_unpublished_prototype(self):
        from tools import extend_nika_clos as generator
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            (root/'SADE-NetworkAgent').symlink_to(ROOT/'SADE-NetworkAgent',target_is_directory=True)
            shutil.copytree(ROOT/'tools/soft3888-templates',root/'tools/soft3888-templates')
            with patch.object(generator,'ROOT',root):files=generator.render()
            self.assertFalse((root/'topology_kathara/Clos_Jiayuan_41Devices').exists())
            for rel,text in files.items():self.assertEqual(text,(ROOT/'topology_kathara/NIKA_Clos_Jiayuan_92Devices'/rel).read_text(),rel)

    def test_agent_prompt_contains_no_reference_truth_or_catalog(self):
        from faultbench.scenario import parse_scenario
        from faultbench.orchestrator import _build_agent_prompt
        sc=parse_scenario(ROOT/'dataset/nika92_Q/custom/nika92-lb1-wrong-backend-ports.txt')
        prompt=_build_agent_prompt(sc)
        self.assertNotIn('[GROUND-TRUTH]',prompt)
        self.assertNotIn('forwards to port81',prompt)
        self.assertNotIn('ground_truth/scenarios.jsonl',prompt)
        self.assertIn(sc.prompt_to_agent,prompt)

class EvaluationMetrics(unittest.TestCase):
    def fixture(self,identifier,truth,observed,status='scored'):
        return ('unit-test-only',dict(scenario=dict(scenario_id=identifier,topology='unit-fixture',scenario_class='base' if truth else 'false-premise',scoring_axes=['assert-identifies: r1'] if truth else ['assert-no-anomaly']),result=dict(agent='fixture-agent',run_id=identifier,timestamp='fixture',submitted=observed is not None,is_anomaly=observed,faulty_devices=['r1'] if observed else [],status=status,cost_usd=.1,wall_seconds=20),phases=dict(agent=dict(wall_seconds=3),score=dict(per_axis=[dict(kind='must',axis='must-identify-mechanism: test fixture',score=1)]))))

    def test_confusion_matrix_and_abstention_are_separate(self):
        from faultbench.evaluation import aggregate
        fixtures=[self.fixture('tp',True,True),self.fixture('tn',False,False),self.fixture('fp',False,True),self.fixture('fn',True,False),self.fixture('missing',True,None,'agent_error')]
        result=aggregate(fixtures)[0]
        self.assertEqual([result[k] for k in ['tp','tn','fp','fn']],[1,1,1,1])
        self.assertEqual(result['accuracy'],.5);self.assertEqual(result['classification_coverage'],.8)
        self.assertEqual(result['mean_agent_seconds'],3);self.assertEqual(result['mean_lifecycle_seconds'],20)
        self.assertIsNone(result['judge_cost_usd'])

    def test_unrun_experiments_have_no_accuracy_or_cost(self):
        from faultbench.evaluation import summarize
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);r=summarize(root/'absent',root/'report.json')
            self.assertEqual(r['status'],'not_run');self.assertEqual(r['summary'],[])

    def test_missing_credentials_never_call_orchestrator(self):
        from faultbench.evaluation import execute
        from faultbench.preflight import require_credentials
        with patch.dict(os.environ,{},clear=True),patch('faultbench.envfile.ENV_FILE',ROOT/'nonexistent'),patch('faultbench.preflight.load_env'),patch('faultbench.orchestrator.run_one') as runner,tempfile.TemporaryDirectory() as directory:
            result=execute(ROOT/'faultbench/benchmarks/soft3888_pilot.csv',['sade','react-full'],Path(directory),run=True)
            self.assertEqual(result['status'],'blocked_missing_credentials');self.assertEqual(result['executed_runs'],[])
            runner.assert_not_called()
            with self.assertRaises(RuntimeError):require_credentials(['sade'])

    def test_orchestrator_archives_actual_result_row_and_phase_times(self):
        from contextlib import ExitStack
        from faultbench.orchestrator import run_one
        from faultbench.runners.base import AgentResult
        from faultbench.scoring import ScoreResult
        from faultbench.inject import InjectionResult
        from faultbench.checks import CheckResult
        from faultbench.scenario import parse_scenario
        scenario=ROOT/'dataset/jiayuan75_Q/custom/jiayuan75-false-premise-internal-application.txt'
        sc=parse_scenario(scenario)
        with ExitStack() as stack,tempfile.TemporaryDirectory() as directory:
            for target,value in [('require_credentials',None),('snapshot_runtime',{'unit_fixture':True}),('lstart',75),('kathara_container_count',75),('time.sleep',None),('lclean',None)]:
                stack.enter_context(patch('faultbench.orchestrator.'+target,return_value=value))
            stack.enter_context(patch('faultbench.orchestrator.run_checks',return_value=[CheckResult(sc.pre_check[0],True,'fixture','unit test')]))
            stack.enter_context(patch('faultbench.orchestrator.apply_injection',return_value=InjectionResult(False,'no fault',None,'')))
            stack.enter_context(patch.dict('faultbench.orchestrator.AGENT_RUNNERS',{'sade':lambda **kw:AgentResult(diagnosis_text='Unit-test fixture, not a real model response.',is_anomaly=False,parsed_ok=True)}))
            stack.enter_context(patch('faultbench.orchestrator.score_submission',return_value=ScoreResult()))
            row=run_one(scenario,'sade',Path(directory),converge_wait=0,stream=False)
            detail=json.loads(next(Path(directory).rglob('result.json')).read_text())
            self.assertEqual(detail['result'],row)
            self.assertGreaterEqual(row['agent_wall_seconds'],0)
            self.assertGreaterEqual(row['judge_wall_seconds'],0)
            self.assertEqual(detail['phases']['agent']['wall_seconds'],row['agent_wall_seconds'])

    def test_missing_runtime_never_spends_model_budget(self):
        from faultbench.evaluation import execute
        with patch('faultbench.evaluation.missing_credentials',return_value=[]),patch('faultbench.evaluation.runtime_preflight',return_value=[{'topology':'unit fixture','error':'missing image fixture'}]),patch('faultbench.orchestrator.run_one') as runner,tempfile.TemporaryDirectory() as directory:
            result=execute(ROOT/'faultbench/benchmarks/soft3888_pilot.csv',['sade'],Path(directory),run=True)
            self.assertEqual(result['status'],'blocked_runtime');runner.assert_not_called()

    def test_bounded_unreachable_ping_summary_is_down(self):
        from faultbench.inventory import parse_ping_error_statistics
        stats=parse_ping_error_statistics('2 packets transmitted, 0 received, 100% packet loss, time 1001ms')
        self.assertEqual(stats['status'],'down');self.assertEqual(stats['rx'],0)

    def test_failed_disk_preflight_preserves_an_existing_lab(self):
        from faultbench.lab import lstart
        with patch('faultbench.lab._is_nika_topology',return_value=False),patch('faultbench.runtime.prepare_lab_runtime'),patch('faultbench.lab.check_storage_budget',side_effect=RuntimeError('unit disk budget fixture')),patch('faultbench.lab.lclean') as cleanup:
            with self.assertRaises(RuntimeError):lstart('Kath5_Jiayuan_75Devices')
            cleanup.assert_not_called()

    def test_nika_service_adapter_preserves_source_configuration(self):
        from faultbench.ground_truth import get_labs
        from faultbench.lab import prepare_nika_startup_runtime
        lab=get_labs({'simple_bgp'})[0]['simple_bgp']
        before=lab.fs.readtext('/router1/etc/frr/frr.conf')
        original=(ROOT/'SADE-NetworkAgent/src/nika/net_env/interdomain_routing/simple_bgp/router1.startup').read_text()
        changed=prepare_nika_startup_runtime(lab)
        self.assertEqual(len(changed),2)
        self.assertIn('/etc/init.d/frr start',lab.fs.readtext('/router1.startup'))
        self.assertEqual(before,lab.fs.readtext('/router1/etc/frr/frr.conf'))
        self.assertEqual(original,(ROOT/'SADE-NetworkAgent/src/nika/net_env/interdomain_routing/simple_bgp/router1.startup').read_text())
        self.assertEqual(prepare_nika_startup_runtime(lab),[])

    def test_no_fault_diagnosis_cannot_name_a_faulty_device(self):
        from faultbench.evaluation import aggregate
        fixture=self.fixture('tn-but-blames-router',False,False)
        fixture[1]['result']['faulty_devices']=['r1']
        r=aggregate([fixture])[0]
        self.assertEqual(r['device_exact_accuracy'],0)

if __name__=='__main__':unittest.main()
