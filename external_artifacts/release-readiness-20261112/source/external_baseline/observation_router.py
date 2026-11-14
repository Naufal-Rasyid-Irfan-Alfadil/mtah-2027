"""A fixed observation-coverage router over two externally fitted classifiers."""
from .training import FEATURE_SETS, HGB_PARAMS
from .features import CONTEXT_NAMES

MODEL_NAMES = FEATURE_SETS['no-signed-position'] + CONTEXT_NAMES


def reliable_rows(x, home_reference, away_reference):
    """Return an observation-only mask for an (N,18) centred-metre matrix.

    C is used only when all available frames in the trailing, reset-aware
    25-frame ball window are complete, and current complete-player counts meet
    training-modal references for both teams. Counts are not player identities.
    NaN in any required field yields False. No distance/coordinate is filled.
    The window itself is computed by ContextFeatureExtractor before this call;
    its state resets at match/period/frame/time gaps. No target is an input.
    """
    import numpy as np
    if x.ndim != 2 or x.shape[1] != len(MODEL_NAMES):
        raise ValueError('router requires the ordered 18-feature observation contract')
    if any(not np.isfinite(v) or v <= 0 for v in (home_reference,away_reference)):
        raise ValueError('positive finite training coverage references required')
    return ((x[:,MODEL_NAMES.index('ball_xy_fraction_1s')]==1)
            & (x[:,MODEL_NAMES.index('home_xy_observed')]>=home_reference)
            & (x[:,MODEL_NAMES.index('away_xy_observed')]>=away_reference))


class CoverageRouter:
    """Select C/A posteriors by fixed coverage, then use the unchanged decoder.

    Both component models retain the original HGB parameters. Input is float64
    (N,18), native NaN, in MODEL_NAMES order. predict_proba returns (N,3) in
    the component estimators' common native class order. There is no fit method,
    target input, threshold search, learned blending, or persistent batch state.
    Component hashes and training-only count references belong in the protocol.
    """
    def __init__(self, baseline, context, home_reference, away_reference):
        import numpy as np
        if (baseline.get_params()!=HGB_PARAMS or context.get_params()!=HGB_PARAMS
                or baseline.n_features_in_!=14 or context.n_features_in_!=18
                or not np.array_equal(baseline.classes_,context.classes_)):
            raise ValueError('router component contracts differ')
        reliable_rows(np.empty((0,18)),home_reference,away_reference)
        self.baseline,self.context = baseline,context
        self.home_reference,self.away_reference = home_reference,away_reference
        self.classes_ = np.array(baseline.classes_,copy=True)
        self.n_features_in_ = 18

    def get_params(self):
        return dict(algorithm='coverage_router_v1',home_reference=self.home_reference,
                    away_reference=self.away_reference,baseline=self.baseline.get_params(),
                    context=self.context.get_params())

    def predict_proba(self,x):
        import numpy as np
        use = reliable_rows(x,self.home_reference,self.away_reference)
        result = np.empty((len(x),len(self.classes_)),dtype=np.float64)
        if use.any(): result[use] = self.context.predict_proba(x[use])
        if (~use).any(): result[~use] = self.baseline.predict_proba(x[~use,:14])
        return result
