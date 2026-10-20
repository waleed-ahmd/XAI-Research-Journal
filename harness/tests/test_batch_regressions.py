from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock

import pytest
import yaml
from click.testing import CliRunner

from harness import cli
from harness.batch import collect_openai_batch, collect_anthropic_batch, pending_batch_keys, submit_openai_batch
from harness.data.loader import load_all_questions, question_index
from harness.data.selection import select_questions, select_questions_balanced, selection_settings, validate_saved_selection, write_selected_questions
from harness.runner import build_plan


def setup_run(tmp_path, config, data_dir):
    for name in ('anthropic', 'openai'):
        model = getattr(config.models, name)
        model.price_per_million_input_tokens = 4
        model.price_per_million_output_tokens = 20
    cfg = tmp_path / 'config.yaml'
    cfg.write_text(yaml.safe_dump(config.model_dump()))
    selected = select_questions(config, data_dir)
    path = tmp_path / 'selected.json'
    write_selected_questions(selected, path)
    Path(str(path) + '.metadata.json').write_text(json.dumps(selection_settings(config)))
    raw = tmp_path / 'raw'
    raw.mkdir()
    args = ['--config', str(cfg), '--data-dir', str(data_dir), '--selected-path', str(path), '--results-dir', str(raw)]
    return selected, raw, args


def test_batch_submit_reaches_both_mocked_providers(tmp_path, small_config, fixture_data_dir, monkeypatch):
    _, raw, args = setup_run(tmp_path, small_config, fixture_data_dir)
    providers = []
    for name in ('anthropic', 'openai'):
        stub = Mock(return_value={'batch_id': name + '-test'})
        monkeypatch.setattr(cli, 'submit_' + name + '_batch', stub)
        providers.append(stub)
    result = CliRunner().invoke(cli.main, args + ['batch-submit', '--completed-manifest', str(tmp_path/'none'), '--limit-new-questions', '2', '--yes'])
    assert result.exit_code == 0, result.output
    for stub in providers:
        assert len(stub.call_args.args[0]) == 6
        assert stub.call_args.kwargs['batch_dir'] == raw.parent/'batches'


def test_partial_result_does_not_skip_other_calls_or_model(tmp_path, small_config, fixture_data_dir):
    selected, raw, _ = setup_run(tmp_path, small_config, fixture_data_dir)
    index = question_index(load_all_questions(small_config.questions.tasks, fixture_data_dir))
    pc = build_plan(selected, index, small_config, 'anthropic')[0]
    (raw/'anthropic.jsonl').write_text(json.dumps({'key': pc.key, 'question_id': pc.question.question_id})+'\n')
    plans = cli._build_new_batch_plans(NS(obj={'results_dir':raw}), small_config, selected, index, ['anthropic','openai'], tmp_path/'none')
    assert sum(p.question.question_id==pc.question.question_id for p in plans['anthropic']) == 2
    assert sum(p.question.question_id==pc.question.question_id for p in plans['openai']) == 3


def test_unknown_prices_abort_before_any_submission(tmp_path, small_config, fixture_data_dir, monkeypatch):
    _, _, args = setup_run(tmp_path, small_config, fixture_data_dir)
    cfg = Path(args[1]); value = yaml.safe_load(cfg.read_text()); value['models']['openai']['price_per_million_input_tokens'] = None; cfg.write_text(yaml.safe_dump(value))
    a = Mock(); b = Mock(); monkeypatch.setattr(cli, 'submit_anthropic_batch', a); monkeypatch.setattr(cli, 'submit_openai_batch', b)
    result = CliRunner().invoke(cli.main, args + ['batch-submit','--yes'])
    assert result.exit_code != 0 and 'prices are required' in result.output
    a.assert_not_called(); b.assert_not_called()


def manifest(tmp_path, count=1):
    calls = [dict(key=f'k{i}',question_id=f't:{i}', task='t',idx=i,condition='original', model_name='openai',run_index=0,gold_letter='A',cued_letter='B',prompt='q',request_params={}) for i in range(count)]
    return dict(manifest_path=str(tmp_path/'openai-b.json'),results_path=str(tmp_path/'raw.jsonl'),batch_id='b',model_id='m',request_count=count,calls=calls)


def success(key):
    return dict(custom_id=key,response=dict(status_code=200,body={'model':'m','status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':'The best answer is: (A)'}]}]}),error=None)


def client(status, output=None, errors=None):
    return NS(batches=NS(retrieve=lambda _: NS(status=status,output_file_id='out' if output is not None else None,error_file_id='err' if errors is not None else None)),files=NS(content=lambda key:NS(text='\n'.join(json.dumps(x) for x in (output if key=='out' else errors)))))


@pytest.mark.parametrize('status', ['expired','cancelled','completed'])
def test_collect_partial_terminal_batch_and_retry_only_errors(tmp_path,status):
    m=manifest(tmp_path,2)
    error=dict(custom_id='k1',response=None,error={'code':'expired'})
    result=collect_openai_batch(m,client=client(status,[success('k0')],[error]))
    assert result['collected']==1 and result['failed']==1 and result['missing']==0
    assert m['collected_at'] and pending_batch_keys(tmp_path,'openai')==set()
    again=collect_openai_batch(m,client=client(status,[success('k0')],[error]))
    assert again['collected']==0 and len(Path(m['results_path']).read_text().splitlines())==1


def test_http_error_is_not_completed(tmp_path):
    m=manifest(tmp_path)
    error=dict(custom_id='k0',response={'status_code':500,'body':{'error':{'message':'retry'}}})
    result=collect_openai_batch(m,client=client('completed',[error]))
    assert result['failed']==1 and result['collected']==0
    assert not Path(m['results_path']).exists()


def test_all_errors_no_output_file_is_collected(tmp_path):
    m=manifest(tmp_path)
    result=collect_openai_batch(m,client=client('completed',None,[dict(custom_id='k0',error={'code':'bad_request'})]))
    assert result['failed']==1 and m['collected_at']


def test_missing_results_remain_reserved(tmp_path):
    m=manifest(tmp_path,2)
    result=collect_openai_batch(m,client=client('completed',[success('k0')]))
    assert result['missing']==1 and not m.get('collected_at')
    assert pending_batch_keys(tmp_path,'openai')=={'k0','k1'}


@pytest.mark.parametrize('entries', [[success('unknown')],[success('k0'),success('k0')]])
def test_unknown_and_duplicate_ids_fail_before_writing(tmp_path,entries):
    m=manifest(tmp_path)
    with pytest.raises(RuntimeError,match='Unknown or duplicate'):
        collect_openai_batch(m,client=client('completed',entries))
    assert not Path(m['results_path']).exists()


def test_ambiguous_submission_reserves_keys(tmp_path,small_config,fixture_data_dir):
    selected=select_questions(small_config,fixture_data_dir)
    plan=build_plan(selected,question_index(load_all_questions(small_config.questions.tasks,fixture_data_dir)),small_config,'openai')[:1]
    stub=NS(files=NS(create=lambda **kw:NS(id='file')), batches=NS(create=Mock(side_effect=TimeoutError('unknown outcome'))))
    with pytest.raises(TimeoutError):
        submit_openai_batch(plan,small_config.models.openai,batch_dir=tmp_path,results_path=tmp_path/'raw/results.jsonl',protocol_version='v1',client=stub)
    assert pending_batch_keys(tmp_path,'openai')=={plan[0].key}


def test_corrupt_reservation_blocks_resubmit(tmp_path):
    (tmp_path/'openai-broken.json').write_text('{')
    with pytest.raises(RuntimeError,match='repair'):
        pending_batch_keys(tmp_path,'openai')


def test_duplicate_source_ids_use_fingerprints_in_planning(tmp_path,small_config,fixture_data_dir):
    from harness.data.models import Question
    a=Question(task='fake_task_a',idx=1,parsed_inputs='first',multiple_choice_targets=['a','b'],multiple_choice_scores=[1,0])
    b=a.model_copy(update={'parsed_inputs':'second','multiple_choice_scores':[0,1]})
    data=tmp_path/'data'; folder=data/'fake_task_a'; folder.mkdir(parents=True)
    (folder/'val_data.json').write_text(json.dumps({'data':[a.model_dump(),b.model_dump()]}))
    config=small_config.model_copy(deep=True); config.questions.tasks=['fake_task_a']; config.questions.total_count=2; config.questions.counts_by_task={'fake_task_a':2}
    selected=select_questions_balanced(config,data)
    path=tmp_path/'selected.json'; write_selected_questions(selected,path); Path(str(path)+'.metadata.json').write_text(json.dumps(selection_settings(config)))
    validate_saved_selection(selected,config,data,path)
    plan=build_plan(selected,question_index([a,b]),config,'openai')
    assert len({pc.key for pc in plan})==6
    assert {pc.prompt.splitlines()[0] for pc in plan}=={'first','second'}
    assert len({pc.question.question_id for pc in plan})==2


def test_historical_fingerprint_mismatch_is_not_silently_replaced(small_config,fixture_data_dir):
    config=small_config.model_copy(deep=True); config.questions.counts_by_task={'fake_task_a':5,'fake_task_b':5}
    with pytest.raises(ValueError,match='missing or changed'):
        select_questions_balanced(config,fixture_data_dir,existing_question_ids={'fake_task_a:0'},existing_question_fingerprints={'fake_task_a:0':'wrong'})


def test_anthropic_failed_items_retry_without_poisoning_results(tmp_path):
    m=manifest(tmp_path,2); m['manifest_path']=str(tmp_path/'anthropic-b.json')
    items=[{'custom_id':'k0','result':{'type':'succeeded','message':{'content':[{'type':'text','text':'The best answer is: (A)'}]}}}, {'custom_id':'k1','result':{'type':'errored','error':{'message':'retry'}}}]
    stub=NS(messages=NS(batches=NS(retrieve=lambda _:NS(processing_status='ended'),results=lambda _:iter(NS(model_dump=lambda value=x:value) for x in items))))
    result=collect_anthropic_batch(m,client=stub)
    assert result['collected']==1 and result['failed']==1 and m['collected_at']
    assert len(Path(m['results_path']).read_text().splitlines())==1


def test_historical_import_is_separate_idempotent_and_preflighted(tmp_path,monkeypatch):
    from harness.historical import import_historical
    from harness import historical
    def git(command,**kw):
        provider='anthropic' if 'anthropic.jsonl' in command[-1] else 'openai'
        experiment=1 if 'experiment-01' in command[-1] else 2
        records=[dict(key=f'{provider}:{experiment}:{i}',question_id=f'{experiment}:{i}',condition='original',run_index=0,model_name=provider) for i in range(90)]
        return NS(stdout='\n'.join(json.dumps(r) for r in records))
    monkeypatch.setattr(historical.subprocess,'run',git)
    output=tmp_path/'historical'
    assert import_historical(tmp_path,output)=={'anthropic':180,'openai':180}
    saved=(output/'openai.jsonl').read_bytes()
    assert import_historical(tmp_path,output)=={'anthropic':180,'openai':180}
    assert (output/'openai.jsonl').read_bytes()==saved
    def missing(*args,**kwargs): raise RuntimeError('missing commit')
    monkeypatch.setattr(historical.subprocess,'run',missing)
    with pytest.raises(RuntimeError): import_historical(tmp_path,output)
    assert (output/'openai.jsonl').read_bytes()==saved
    with pytest.raises(ValueError,match='separate'): import_historical(tmp_path,tmp_path/'raw')


def test_analyze_combines_historical_and_live_results_once(tmp_path,small_config,fixture_data_dir,monkeypatch):
    import sys
    _,raw,args=setup_run(tmp_path,small_config,fixture_data_dir)
    old=tmp_path/'historical'; old.mkdir()
    r=dict(key='same',model_name='openai',question_id='t:0',condition='original',run_index=0,gold_letter='A',cued_letter='B',answer_text='The best answer is: (A)')
    for p in [raw/'openai.jsonl',old/'openai.jsonl']: p.write_text(json.dumps(r)+'\n')
    monkeypatch.setitem(sys.modules,'harness.analysis.figures',NS(plot_accuracy=lambda *a:None,plot_flip_rates=lambda *a:None))
    output=tmp_path/'summary'
    result=CliRunner().invoke(cli.main,args+['analyze','--historical-dir',str(old),'--summary-dir',str(output)])
    assert result.exit_code==0,result.output
    import csv
    with (output/'metrics_summary.csv').open() as f: metrics=list(csv.DictReader(f))
    assert next(m for m in metrics if m['metric']=='accuracy')['n']=='1'


def test_negative_budget_rejected_without_provider_calls(tmp_path,small_config,fixture_data_dir):
    _,_,args=setup_run(tmp_path,small_config,fixture_data_dir)
    result=CliRunner().invoke(cli.main,args+['batch-submit','--openai-budget','-1','--yes'])
    assert result.exit_code!=0 and 'Invalid value' in result.output


def test_historical_exclusion_requires_matching_generation_settings(tmp_path,small_config,fixture_data_dir):
    from harness.providers.openai_provider import build_request
    from harness.prompts import VISIBLE_EXPLANATION_INSTRUCTION, SUGGESTED_ANSWER_TEMPLATE
    selected, raw, _ = setup_run(tmp_path,small_config,fixture_data_dir)
    q = selected[0]
    saved = {'questions':{q.source_question_id:{'fingerprint':q.fingerprint}},'conditions':small_config.conditions,'run_indices':[0], 'output_instruction':VISIBLE_EXPLANATION_INSTRUCTION,'cue_template':SUGGESTED_ANSWER_TEMPLATE,'request_settings':{'openai':{k:v for k,v in build_request(small_config.models.openai,'').items() if k!='input'}}}
    path=tmp_path/'historical.json'; path.write_text(json.dumps(saved))
    index=question_index(load_all_questions(small_config.questions.tasks,fixture_data_dir)); ctx=NS(obj={'results_dir':raw})
    plans=cli._build_new_batch_plans(ctx,small_config,selected,index,['openai'],path)
    assert all(p.question.question_id!=q.question_id for p in plans['openai'])
    small_config.models.openai.reasoning.effort='low'
    plans=cli._build_new_batch_plans(ctx,small_config,selected,index,['openai'],path)
    assert sum(p.question.question_id==q.question_id for p in plans['openai'])==3


def test_anthropic_submission_timeout_also_stays_reserved(tmp_path,small_config,fixture_data_dir):
    from harness.batch import submit_anthropic_batch
    selected=select_questions(small_config,fixture_data_dir)
    plan=build_plan(selected,question_index(load_all_questions(small_config.questions.tasks,fixture_data_dir)),small_config,'anthropic')[:1]
    stub=NS(messages=NS(batches=NS(create=Mock(side_effect=TimeoutError('unknown')))))
    with pytest.raises(TimeoutError):
        submit_anthropic_batch(plan,small_config.models.anthropic,batch_dir=tmp_path,results_path=tmp_path/'raw/results.jsonl',protocol_version='v1',client=stub)
    assert pending_batch_keys(tmp_path,'anthropic')=={plan[0].key}
