import numpy as np
from bop_twin.criteria.pe_acceptance import acceptance_hold_drop

def main():
    t = np.linspace(0, 600, 601)
    p = np.linspace(200e5, 198e5, 601)  # queda de ~1%
    r = acceptance_hold_drop(t, p, window_s=300, max_drop_percent=1.0)
    print("acceptance:", r)

if __name__ == "__main__":
    main()