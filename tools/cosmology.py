"""Cosmological parameter sets and the CLASS call.

Plain Python — no MCP imports. Parameters follow Planck 2018 (arXiv:1807.06209),
passed to CLASS as physical densities (omega = Omega * h^2).
"""

import numpy as np


def base_params() -> dict:
    """Flat LCDM baseline parameters (Planck 2018 best fit)."""
    return {
        "output": "mPk",
        "P_k_max_h/Mpc": 5.0,
        "z_pk": 0.0,
        "h": 0.6736,
        "omega_b": 0.02237,
        "omega_cdm": 0.1200,
        "A_s": 2.100e-9,
        "n_s": 0.9649,
    }


def lcdm() -> dict:
    """Flat LCDM: cold dark matter + cosmological constant (w = -1)."""
    return base_params()


def nu_mass(sum_mnu_eV: float = 0.10) -> dict:
    """LCDM + one massive neutrino species of total mass sum_mnu_eV.

    Massive neutrinos free-stream and suppress the small-scale power spectrum.
    """
    p = base_params()
    p.update(
        {
            "N_ur": 2.0308,  # remaining massless species (3.044 - 1)
            "N_ncdm": 1,
            "m_ncdm": sum_mnu_eV,
            "T_ncdm": 0.71611,
        }
    )
    return p


def wcdm(w0: float = -0.9) -> dict:
    """Dark energy as a fluid with constant equation of state w0 (w != -1).

    Changes late-time growth, shifting the power spectrum amplitude.
    """
    p = base_params()
    p.update({"Omega_Lambda": 0.0, "w0_fld": w0, "wa_fld": 0.0})
    return p


# Registry the tools expose to agents: ASCII keys only.
MODELS = {
    "lcdm": {
        "build": lambda opts: lcdm(),
        "label": lambda opts: "LCDM",
        "description": "Flat LCDM baseline (Planck 2018, w = -1).",
        "tunable": {},
    },
    "nu_mass": {
        "build": lambda opts: nu_mass(opts["sum_mnu_eV"]),
        "label": lambda opts: f"LCDM + massive nu ({opts['sum_mnu_eV']:g} eV)",
        "description": "LCDM plus massive neutrinos; suppresses small-scale power.",
        "tunable": {"sum_mnu_eV": "total neutrino mass in eV (default 0.10)"},
    },
    "wcdm": {
        "build": lambda opts: wcdm(opts["w0"]),
        "label": lambda opts: f"wCDM (w0 = {opts['w0']:g})",
        "description": "Constant-w dark energy fluid; alters late-time growth.",
        "tunable": {"w0": "dark energy equation of state (default -0.9)"},
    },
}


def run_class(params: dict, k: np.ndarray, z: float = 0.0) -> np.ndarray:
    """Compute the linear matter power spectrum P(k) with CLASS.

    Args:
        params: CLASS parameter dictionary (from the model builders above).
        k: wavenumbers in h/Mpc.
        z: redshift.

    Returns:
        P(k) in (Mpc/h)^3, same length as k.
    """
    # Imported here, not at module scope: a host that dispatches this kernel
    # to an HPC site never needs CLASS installed locally.
    from classy import Class

    h = params["h"]
    cosmo = Class()
    cosmo.set(params)
    cosmo.compute()
    try:
        # classy wants k in 1/Mpc and returns P(k) in Mpc^3; convert to h units.
        return np.array([cosmo.pk(ki * h, z) * h**3 for ki in k])
    finally:
        cosmo.struct_cleanup()
        cosmo.empty()
