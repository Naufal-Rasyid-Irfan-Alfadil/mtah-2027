"""External-only diagnosis and one predeclared refinement; no import-time I/O."""
import argparse
from pathlib import Path
import json

from .prepare import REPO, sha256
from .training import load_split
from .v2 import MODEL_NAMES, PROJECT, score, guard_metrics
from .robustness import SCENARIOS, stress_feature_matrices
from .observation_router import reliable_rows, CoverageRouter
from .multimatch import write_json, validate_match, feature_half
from .inference_bundle import load_bundle, verify_experiment_sources, build_v2

SCENARIO_NAMES = tuple(s['name'] for s in SCENARIOS)
ASSESSMENT_MATCH = 'DFL-MAT-J03WMX'


def sources():
    """Hash explicit algorithm modules and the pure evaluator, without data I/O."""
    result = {p.relative_to(REPO).as_posix():sha256(p) for p in (REPO/'external_baseline').glob('*.py')}
    result['evaluation/possession_metrics.py'] = sha256(REPO/'evaluation/possession_metrics.py')
    return result


def read_json(path):
    return json.loads(Path(path).read_text())


def verify_outputs(directory):
    """Validate ready, explicitly named local external outputs, never recurse."""
    from .inference_bundle import safe_path
    directory = Path(directory)
    manifest = read_json(directory/'manifest.json')
    if manifest.get('status')!='ready': raise ValueError('ready external artifact required')
    for name,digest in manifest['outputs_sha256'].items():
        if Path(name).name!=name or sha256(safe_path(directory,name))!=digest:
            raise ValueError('external artifact checksum mismatch')
    return manifest


def select_refinement(metrics,minimum_gain=.01):
    """Apply the original .01 F1 guards to exactly A/R and all seven scenarios.

    No missing scenario, nonfinite score, or omitted half may silently pass.
    minimum_gain=.01 is development selection; the predeclared additional
    assessment uses zero clean Spell gain and unchanged regression safeguards.
    Thresholds are absolute F1 units, not percentages or accuracy.
    """
    import math
    if set(metrics)!={'A','R'}: raise ValueError('exactly A/R scores required')
    for scenarios in metrics.values():
        if set(scenarios)!=set(SCENARIO_NAMES): raise ValueError('all paired scenarios required')
        for scopes in scenarios.values():
            if set(scopes)!={'overall','half_1','half_2'}: raise ValueError('both halves and pooled score required')
            for m in scopes.values():
                m['transitions'] = {int(k):v for k,v in m['transitions'].items()}
                required = [m['macro_f1'],m['spell_f1_mean'],m['per_class']['D']['f1'],
                            m['transitions'][12]['f1'],m['transitions'][25]['f1']]
                if any(not math.isfinite(v) for v in required): raise ValueError('nonfinite selection score')
    failures = []
    for scenario in SCENARIO_NAMES:
        a,c = metrics['A'][scenario]['overall'],metrics['R'][scenario]['overall']
        failures.extend(scenario+':'+name for name in guard_metrics(c,a))
        if scenario=='clean':
            if c['spell_f1_mean'] < a['spell_f1_mean']+minimum_gain-1e-12:
                failures.append('clean:spell_gain')
            for half in ('half_1','half_2'):
                if metrics['R'][scenario][half]['spell_f1_mean'] < metrics['A'][scenario][half]['spell_f1_mean']-.01-1e-12:
                    failures.append(half+':spell')
        elif c['spell_f1_mean'] < a['spell_f1_mean']-.01-1e-12:
            failures.append(scenario+':spell')
    return dict(selected='A' if failures else 'R',violations={'R':failures},
                independent_generalization=False,historical_assessment_used=False)


def plan(output):
    """Persist one fixed router protocol before computing any new predictions.

    Inputs are the verified parent experiment and training-modal player counts.
    Output contains source/model/input hashes, the unchanged regression gates,
    and a prospective additional-match assessment policy with unknown legacy
    history explicitly recorded. No real model is fitted or scored here.
    """
    output=Path(output).resolve()
    output.relative_to(REPO/'external_artifacts/v2')
    if output.exists(): raise FileExistsError(output)
    parent=REPO/'external_artifacts/v2/run1'
    parent_manifest=verify_outputs(parent)
    from .v2 import verify_inputs
    matches,hashes,bundle,descriptor=verify_inputs()
    diagnosis_path=REPO/'external_artifacts/v2/refinement-diagnosis-v1/diagnosis.json'
    diagnosis=read_json(diagnosis_path)
    counts=diagnosis['training_modal_complete_players']
    home={v['home_xy_observed'] for v in counts.values()};away={v['away_xy_observed'] for v in counts.values()}
    if len(home)!=1 or len(away)!=1: raise ValueError('training count modes disagree; no automatic threshold choice')
    routing=dict(home_reference=home.pop(),away_reference=away.pop(),
                 policy='C if trailing available ball window complete and current complete teams meet training modes; else A')
    hashes.update({str(parent/name):digest for name,digest in parent_manifest['outputs_sha256'].items()
                   if name.endswith('.npz') or name in ('model_C.joblib','metrics.json','protocol.json')})
    hashes[str(parent/'manifest.json')]=sha256(parent/'manifest.json')
    hashes[str(diagnosis_path)]=sha256(diagnosis_path)
    protocol=dict(version=1,algorithm='coverage_router_v1',routing=routing,
        training=[m['match_id'] for m in matches[:2]],validation=matches[2]['match_id'],
        parent_experiment=str(parent.relative_to(REPO)),baseline_bundle=str(bundle.relative_to(REPO)),
        source_sha256=sources(),inputs_sha256=hashes,packages=descriptor['packages'],
        features=list(MODEL_NAMES),candidates=['A','R'],classifier_fitting=False,
        decoder='unchanged training-only V1; no grid, prior or threshold fitting',
        minimum_spell_gain=.01,maximum_regression=.01,scenarios=list(SCENARIOS),
        prospective_assessment=dict(match_id=ASSESSMENT_MATCH,minimum_spell_gain=0.,
            maximum_regression=.01,history='no use found in available repository/docs/artifact names/Git; legacy project unknown',
            untouched_test_claim=False,scenarios=list(SCENARIOS),
            policy='one assessment after development selection; no adaptation after results'),
        official_inputs=False,official_aggregate_used_for_selection=False)
    output.mkdir(parents=True)
    write_json(output/'protocol.json',protocol)
    print('Protocol fixed: '+str(output/'protocol.json'),flush=True)
    return protocol


def aligned_truth(data,truth):
    """Join predictions to external targets using original frame and timestamps."""
    keys,stamps,_,y,valid=truth
    lookup={k.source_frame:i for i,k in enumerate(keys)}
    indices=[lookup[int(f)] for f in data['source_frame']]
    k=[keys[i] for i in indices];t=[stamps[i] for i in indices]
    if t!=data['timestamp_us'].tolist(): raise ValueError('external target timestamp mismatch')
    return k,t,y[indices],valid[indices]


def score_saved(output,truths,candidates):
    """Score persisted predictions only after all scenario/half arrays exist."""
    import numpy as np
    metrics={name:{} for name in candidates}
    for scenario in SCENARIO_NAMES:
        for candidate in candidates:
            scopes={};pooled=[[],[],[],[],[]]
            for period in (1,2):
                with np.load(output/f'half{period}-{scenario}.npz',allow_pickle=False) as data:
                    k,t,y,valid=aligned_truth(data,truths[period]);labels=data[candidate]
                    scopes[f'half_{period}']=score(k,t,y,valid,labels)
                    for target,values in zip(pooled,(k,t,y,valid,labels)): target.extend(values)
            scopes['overall']=score(*pooled)
            metrics[candidate][scenario]=scopes
    return metrics


def evaluate(output):
    """Evaluate exactly one fixed router on reused external development arrays.

    Component posteriors are reused from verified parent NPZs, in H/A/D order.
    Original keys, gaps, native NaNs and half resets are preserved. Selection
    uses all original guards; failure retains A and never triggers another sweep.
    """
    import joblib
    import numpy as np
    from .training import predict_raw
    from .temporal import decode_probabilities
    from .contracts import FrameKey
    output=Path(output).resolve()
    if (output/'manifest.json').exists() or (output/'model_R.joblib').exists(): raise FileExistsError(output)
    protocol=read_json(output/'protocol.json')
    if protocol['source_sha256']!=sources(): raise ValueError('source changed after protocol')
    # Historical absolute paths are never used: this protocol was created here.
    if any(sha256(Path(p))!=h for p,h in protocol['inputs_sha256'].items()): raise ValueError('protocol input changed')
    baseline,decoder=load_bundle(REPO/protocol['baseline_bundle'])
    parent=REPO/protocol['parent_experiment']
    context=joblib.load(parent/'model_C.joblib')['model']
    routing=protocol['routing']
    router=CoverageRouter(baseline,context,routing['home_reference'],routing['away_reference'])
    joblib.dump(dict(model=router,feature_names=MODEL_NAMES,algorithm='coverage_router_v1',config=protocol),output/'model_R.joblib',compress=3)
    restored=joblib.load(output/'model_R.joblib')['model']
    coverage={}
    for period in (1,2):
        for scenario in SCENARIO_NAMES:
            print(f'Development fixed router: half {period}, {scenario}',flush=True)
            with np.load(parent/f'half{period}-{scenario}.npz',allow_pickle=False) as data:
                x=data['X'][:,PROJECT]
                use=reliable_rows(x,routing['home_reference'],routing['away_reference'])
                probs=np.where(use[:,None],data['probabilities_C'],data['probabilities_A'])
                keys=[FrameKey(protocol['validation'],period,int(f)) for f in data['source_frame']]
                labels=decode_probabilities(keys,data['timestamp_us'],probs,decoder)
                # Sample both sides of routing and compare actual serialized execution.
                probe=np.unique(np.r_[np.flatnonzero(use)[:16],np.flatnonzero(~use)[:16]])
                for model in (router,restored):
                    _,actual=predict_raw(model,x[probe])
                    if not np.allclose(actual,probs[probe],atol=1e-12,rtol=1e-12):
                        raise ValueError('router serialization/projection differs from paired posteriors')
                np.savez_compressed(output/f'half{period}-{scenario}.npz',source_frame=data['source_frame'],
                    timestamp_us=data['timestamp_us'],probabilities_R=probs,R=labels,
                    route_C=use)
                coverage[f'half{period}:{scenario}']=dict(frames=len(use),route_C=int(use.sum()))
    truths={p:load_split(REPO/'external_artifacts/J03WQQ-features-v1/features.sqlite',
                        REPO/'external_artifacts/J03WQQ-prepared-v1/targets.sqlite',p) for p in (1,2)}
    metrics=score_saved(output,truths,['R'])
    metrics['A']=read_json(parent/'metrics.json')['A']
    selection=select_refinement(metrics)
    for name,value in (('metrics',metrics),('selection',selection),('selected_decoder',decoder),
                       ('diagnosis',dict(coverage=coverage,origin='one fixed router from external diagnosis'))):
        write_json(output/(name+'.json'),value)
    if sources()!=protocol['source_sha256']: raise ValueError('source changed during experiment')
    write_json(output/'manifest.json',dict(status='ready',v2_version=2,refinement_version=1,
        source_sha256=protocol['source_sha256'],inputs_sha256=protocol['inputs_sha256'],selection=selection,
        outputs_sha256={p.name:sha256(p) for p in output.iterdir() if p.is_file()}))
    print(json.dumps(selection,indent=2),flush=True)
    return selection


def assess(experiment,prepared,features,output):
    """Run the frozen router once on additional external J03WMX, without fitting.

    Predict both models/scenarios/halves before loading assessment target arrays.
    Original external frames/times are retained, not official 199319 indexing.
    Persist a pre-score hash protocol, full metrics and release qualification;
    unknown legacy usage prevents any untouched-test/generalization claim.
    """
    import numpy as np
    import joblib
    from .training import predict_raw
    from .temporal import decode_probabilities
    experiment,output=Path(experiment).resolve(),Path(output).resolve()
    if output.exists(): raise FileExistsError(output)
    manifest=verify_outputs(experiment)
    verify_experiment_sources(experiment,manifest)
    if read_json(experiment/'selection.json')['selected']!='R': raise ValueError('router failed development selection')
    parent_protocol=read_json(experiment/'protocol.json')
    match=validate_match(prepared,features)
    if match['match_id']!=parent_protocol['prospective_assessment']['match_id'] or match['match_id'] in parent_protocol['training']+[parent_protocol['validation']]:
        raise ValueError('assessment match differs from predeclared disjoint match')
    output.mkdir(parents=True)
    protocol=dict(version=1,match_id=match['match_id'],fitting=False,tuning=False,
        experiment_manifest_sha256=sha256(experiment/'manifest.json'),model_sha256=sha256(experiment/'model_R.joblib'),
        source_sha256=sources(),qualification=parent_protocol['prospective_assessment'],
        inputs_sha256={str(p):sha256(p) for p in match['paths']},official_inputs=False)
    write_json(output/'protocol.json',protocol)
    router=joblib.load(experiment/'model_R.joblib')['model']
    baseline,decoder=load_bundle(REPO/parent_protocol['baseline_bundle'])
    for period in (1,2):
        keys,stamps,matrices,retained,_=stress_feature_matrices(match['observations'],period,2027,context=True)
        original_keys,original_stamps,original=feature_half(match,period)
        if keys!=original_keys or stamps!=original_stamps or not np.array_equal(original,matrices['clean'][:,:16],equal_nan=True):
            raise ValueError('assessment observation replay mismatch')
        for scenario in SCENARIO_NAMES:
            print(f'Frozen additional assessment: half {period}, {scenario}',flush=True)
            use=retained[scenario];x=matrices[scenario][use]
            k=[v for v,keep in zip(keys,use) if keep];t=[v for v,keep in zip(stamps,use) if keep]
            _,pa=predict_raw(baseline,x[:,:16][:,[i for i in range(16) if i not in (4,5)]])
            _,pr=predict_raw(router,x[:,PROJECT])
            a=decode_probabilities(k,t,pa,decoder);r=decode_probabilities(k,t,pr,decoder)
            np.savez_compressed(output/f'half{period}-{scenario}.npz',source_frame=[v.source_frame for v in k],
                                timestamp_us=t,A=a,R=r,probabilities_A=pa,probabilities_R=pr)
        del matrices
    truths={p:load_split(match['features'],match['targets'],p) for p in (1,2)}
    metrics=score_saved(output,truths,['A','R'])
    decision=select_refinement(metrics,minimum_gain=0.)
    decision['release_passed']=decision['selected']=='R'
    decision['untouched_test_claim']=False
    decision['legacy_history']='unknown'
    write_json(output/'metrics.json',metrics);write_json(output/'decision.json',decision)
    if sources()!=protocol['source_sha256'] or any(sha256(Path(p))!=h for p,h in protocol['inputs_sha256'].items()):
        raise ValueError('assessment source/input changed')
    write_json(output/'manifest.json',dict(status='ready',release_passed=decision['release_passed'],
        experiment_manifest_sha256=protocol['experiment_manifest_sha256'],untouched_test_claim=False,
        match_id=match['match_id'],source_sha256=protocol['source_sha256'],
        outputs_sha256={p.name:sha256(p) for p in output.iterdir() if p.is_file()}))
    print(json.dumps(decision,indent=2),flush=True)
    return decision


def freeze(experiment,assessment,output):
    """Package only a qualified fixed candidate, with assessment provenance."""
    build_v2(experiment,output,assessment=assessment)
    load_bundle(output)
    print('Verified release bundle: '+str(output),flush=True)


def diagnose(experiment, output):
    """Summarize existing DFL errors before defining a refinement protocol.

    Input: trusted V2 external NPZs (20 observation columns; H/A/D posteriors)
    and J03WQQ targets keyed by match/period/source frame. Output: JSON error
    strata, without fitting or parameter search. Missing stays NaN; temporal
    context is the existing causal one-second window, reset at real gaps.
    """
    import numpy as np
    experiment, output = Path(experiment), Path(output)
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    manifest = json.loads((experiment/'manifest.json').read_text())
    truths = {p: load_split(REPO/'external_artifacts/J03WQQ-features-v1/features.sqlite',
                           REPO/'external_artifacts/J03WQQ-prepared-v1/targets.sqlite',p) for p in (1,2)}
    result = {}
    for scenario in ('clean','ball_drop_burst2s','player_drop_iid20'):
        strata = {}
        for period in (1,2):
            path = experiment/f'half{period}-{scenario}.npz'
            if sha256(path) != manifest['outputs_sha256'][path.name]:
                raise ValueError('diagnosis input checksum mismatch')
            with np.load(path,allow_pickle=False) as d:
                keys,stamps,_,y,valid = truths[period]
                if [k.source_frame for k in keys] != d['source_frame'].tolist() or stamps != d['timestamp_us'].tolist():
                    raise ValueError('diagnosis requires exact external timeline')
                x = d['X']
                conditions = dict(all=np.ones(len(y),dtype=bool),
                    ball_complete=x[:,3]==1, ball_incomplete=x[:,3]==0,
                    full_ball_window=x[:,16]==1, incomplete_ball_window=x[:,16]<1,
                    full_teams=(x[:,8]>=11)&(x[:,10]>=11),
                    reduced_teams=(x[:,8]<11)|(x[:,10]<11))
                for name,use in conditions.items():
                    use &= valid
                    row = strata.setdefault(name,dict(frames=0,A_raw_errors=0,C_raw_errors=0,
                        A_errors=0,C_errors=0,A_correct_C_wrong=0,C_correct_A_wrong=0,
                        true_D=0,A_D_to_alive=0,C_D_to_alive=0))
                    row['frames'] += int(use.sum())
                    for candidate in ('A','C'):
                        row[candidate+'_raw_errors'] += int((use & (d['raw_'+candidate]!=y)).sum())
                        row[candidate+'_errors'] += int((use & (d[candidate]!=y)).sum())
                        row[candidate+'_D_to_alive'] += int((use & (y=='D') & (d[candidate]!='D')).sum())
                    row['true_D'] += int((use & (y=='D')).sum())
                    row['A_correct_C_wrong'] += int((use & (d['A']==y) & (d['C']!=y)).sum())
                    row['C_correct_A_wrong'] += int((use & (d['C']==y) & (d['A']!=y)).sum())
        result[scenario] = strata
    # Roster observation reference is estimated from training observations only.
    references = {}
    for identity,feature_dir in (('J03WOH','J03WOH-features-run2'),('J03WPY','J03WPY-features-v1')):
        from .multimatch import read_only
        from contextlib import closing
        with closing(read_only(REPO/'external_artifacts'/feature_dir/'features.sqlite')) as db:
            references[identity] = {name:db.execute('SELECT '+name+',COUNT(*) n FROM features GROUP BY '+name+' ORDER BY n DESC LIMIT 1').fetchone()[0]
                                    for name in ('home_xy_observed','away_xy_observed')}
    report = dict(version=1,source='DFL J03WQQ development only',diagnosis=result,
                  training_modal_complete_players=references, official_inputs=False)
    (output/'diagnosis.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps(report,indent=2),flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['diagnose','plan','evaluate','assess','freeze'])
    parser.add_argument('--experiment',type=Path)
    parser.add_argument('--assessment',type=Path)
    parser.add_argument('--prepared',type=Path)
    parser.add_argument('--features',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    if args.stage=='diagnose': diagnose(args.experiment,args.output)
    elif args.stage=='plan': plan(args.output)
    elif args.stage=='evaluate': evaluate(args.output)
    elif args.stage=='assess': assess(args.experiment,args.prepared,args.features,args.output)
    else: freeze(args.experiment,args.assessment,args.output)


if __name__ == '__main__':
    main()
