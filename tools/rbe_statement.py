from __future__ import annotations
RBE = 1.1
STATEMENT = "Proton doses reported as RBE-weighted using constant RBE=1.1 per ICRU 78 (Paganetti 2012)."
VARIABLE_RBE_NOTE = "Constant RBE=1.1 is a convention; variable-RBE models are a known limitation and future work."
def physical_to_rbe(dose):
    import numpy as np
    return np.asarray(dose, float) * RBE
