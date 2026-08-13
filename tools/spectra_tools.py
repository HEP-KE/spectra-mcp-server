"""MCP tool functions for matter power spectra.

Plain Python functions — no MCP imports. The type hints, Field constraints,
and docstrings below become the MCP tool schema that agents see.

Data flows between tools as CSV file paths: compute_power_spectrum writes one
CSV per model, plot_power_spectra reads them back. Only small numbers (19
observed data points, file paths) ever pass through the LLM context.
"""

import csv
from pathlib import Path
from typing import Annotated, Any, Literal

import numpy as np
from pydantic import BaseModel, Field, validate_call

from .cosmology import MODELS, run_class

DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "DR14_pm3d_19kbins.txt"

EBOSS_LABEL = "eBOSS DR14 Ly-a forest"

# The data file comes verbatim from github.com/marius311/mpk_compilation
# (dat/lya/, the Chabanier+2019 arXiv:1905.08103 compilation): the z=0 linear
# matter power spectrum inferred from the eBOSS DR14 Ly-a forest.
# Its column convention is MIXED: k is in 1/Mpc, but P(k) and sigma are in
# (Mpc/h)^3 — the source notebook plots errorbar(k/h, Pk). Read it any other
# way and the data appears offset from theory by ~2x.
H_FIDUCIAL = 0.6736  # h used for the 1/Mpc -> h/Mpc conversion


class ArtifactResult(BaseModel):
    """Uniform result contract returned by every tool."""

    status: Literal["success"]
    files: list[str]
    message: str
    metadata: dict[str, Any]


def load_eboss_arrays() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Load the bundled DR14 data as (k [h/Mpc], Pk, sigma). Not an MCP tool."""
    k_per_mpc, pk, sigma = np.loadtxt(DATA_FILE).T
    return k_per_mpc / H_FIDUCIAL, pk, sigma


@validate_call
def get_eboss_data() -> ArtifactResult:
    """Return the bundled eBOSS DR14 Lyman-alpha forest power spectrum data.

    Use this tool to inspect the observational data: 19 bins of (k, P(k),
    sigma_P) with k in h/Mpc and P(k) in (Mpc/h)^3 — the z=0 linear matter
    power inferred from the Ly-a forest (Chabanier et al. 2019). The same data
    is drawn automatically by plot_power_spectra, so you do NOT need to pass
    these numbers to other tools.
    """
    k, pk, sigma = load_eboss_arrays()
    return ArtifactResult(
        status="success",
        files=[str(DATA_FILE)],
        message=f"Loaded {len(k)} eBOSS DR14 Ly-a P(k) bins.",
        metadata={
            "label": EBOSS_LABEL,
            "k_h_per_Mpc": k.round(4).tolist(),
            "Pk_Mpc_over_h_cubed": pk.round(2).tolist(),
            "sigma_Pk": sigma.round(2).tolist(),
        },
    )


@validate_call
def list_cosmology_models() -> ArtifactResult:
    """List the cosmological models available to compute_power_spectrum.

    Use this tool first to discover valid model names and their tunable
    parameters. Model names are lowercase ASCII keys (e.g. "lcdm").
    """
    models = {
        name: {"description": spec["description"], "tunable": spec["tunable"]}
        for name, spec in MODELS.items()
    }
    return ArtifactResult(
        status="success",
        files=[],
        message=f"{len(models)} models available: {', '.join(models)}.",
        metadata={"models": models},
    )


@validate_call
def compute_power_spectrum(
    model: Literal["lcdm", "nu_mass", "wcdm"],
    output_dir: Annotated[str, Field(min_length=1)],
    sum_mnu_eV: Annotated[float, Field(ge=0, le=1.0)] = 0.10,
    w0: Annotated[float, Field(ge=-2.0, le=-0.3)] = -0.9,
    k_min: Annotated[float, Field(gt=1e-4)] = 0.001,
    k_max: Annotated[float, Field(le=10.0)] = 4.0,
    n_points: Annotated[int, Field(ge=10, le=1000)] = 200,
    z: Annotated[float, Field(ge=0.0, le=10.0)] = 0.0,
) -> ArtifactResult:
    """Compute a linear matter power spectrum P(k) with the CLASS Boltzmann code.

    Use this tool once per cosmological model. It writes a CSV file
    (columns: k in h/Mpc, P(k) in (Mpc/h)^3) and returns its path. Pass the
    returned file path to plot_power_spectra — never copy the numbers.

    Args:
        model: Which cosmology to run: "lcdm", "nu_mass", or "wcdm"
            (see list_cosmology_models).
        output_dir: Directory where the CSV is written.
        sum_mnu_eV: Total neutrino mass in eV (0 means massless). Only used
            when model="nu_mass".
        w0: Dark energy equation of state. Only used when model="wcdm".
        k_min: Smallest wavenumber, h/Mpc.
        k_max: Largest wavenumber, h/Mpc (up to 10).
        n_points: Number of log-spaced k points.
        z: Redshift of the spectrum.
    """
    spec = MODELS[model]
    opts = {"sum_mnu_eV": sum_mnu_eV, "w0": w0}
    params = spec["build"](opts)
    params["P_k_max_h/Mpc"] = max(k_max * 1.2, 1.0)
    params["z_pk"] = z
    label = spec["label"](opts)

    k = np.logspace(np.log10(k_min), np.log10(k_max), n_points)
    pk = run_class(params, k, z=z)

    outdir = Path(output_dir).expanduser().resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    csv_path = outdir / f"pk_{model}.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        f.write(f"# label: {label}\n")
        writer = csv.writer(f)
        writer.writerow(["k_h_per_Mpc", "Pk_Mpc_over_h_cubed"])
        writer.writerows(zip(k, pk))

    return ArtifactResult(
        status="success",
        files=[str(csv_path)],
        message=f"Computed P(k) for {label} at z={z:g} ({n_points} points).",
        metadata={"model": model, "label": label, "z": z,
                  "k_range_h_per_Mpc": [k_min, k_max]},
    )


@validate_call
def plot_power_spectra(
    spectrum_files: Annotated[list[str], Field(min_length=1, max_length=6)],
    output_dir: Annotated[str, Field(min_length=1)],
    reference_index: Annotated[int, Field(ge=0)] = 0,
) -> ArtifactResult:
    """Plot model power spectra against the eBOSS DR14 Ly-a forest data.

    Use this tool after compute_power_spectrum. It reads the CSV files
    produced by that tool and draws a two-panel figure: P(k) curves with the
    observational data on top, and the ratio of every curve (and the data)
    to a reference curve on the bottom.

    Args:
        spectrum_files: Paths of CSV files written by compute_power_spectrum.
        output_dir: Directory where the PNG is written.
        reference_index: Which entry of spectrum_files is the ratio reference
            (0 = the first file, usually LCDM).
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if reference_index >= len(spectrum_files):
        raise ValueError("reference_index is out of range for spectrum_files.")

    curves = []
    for path_str in spectrum_files:
        path = Path(path_str).expanduser().resolve()
        first_line = path.read_text(encoding="utf-8").splitlines()[0]
        label = first_line.removeprefix("# label:").strip() if first_line.startswith("# label:") else path.stem
        k, pk = np.loadtxt(path, delimiter=",", skiprows=2).T
        curves.append({"label": label, "k": k, "pk": pk})

    k_obs, pk_obs, sigma_obs = load_eboss_arrays()
    ref = curves[reference_index]

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(8, 8), sharex=True,
        gridspec_kw={"height_ratios": [2, 1], "hspace": 0.06},
    )
    linestyles = ["-", "--", "-.", ":"]
    for i, c in enumerate(curves):
        ax1.loglog(c["k"], c["pk"], linestyles[i % len(linestyles)],
                   color=f"C{i}", linewidth=1.8, label=c["label"])
    ax1.errorbar(k_obs, pk_obs, yerr=sigma_obs, fmt="ko", markersize=5,
                 markerfacecolor="none", capsize=3, label=EBOSS_LABEL)
    ax1.set_ylabel(r"$P(k)\ [(\mathrm{Mpc}/h)^3]$")
    ax1.set_title("Matter power spectrum: theory vs observations")
    ax1.legend(loc="lower left", fontsize="small")

    for i, c in enumerate(curves):
        if i == reference_index:
            continue
        ratio = c["pk"] / np.interp(c["k"], ref["k"], ref["pk"])
        ax2.semilogx(c["k"], ratio, linestyles[i % len(linestyles)],
                     color=f"C{i}", linewidth=1.8)
    ref_at_obs = np.interp(k_obs, ref["k"], ref["pk"])
    ax2.errorbar(k_obs, pk_obs / ref_at_obs, yerr=sigma_obs / ref_at_obs,
                 fmt="ko", markersize=5, markerfacecolor="none", capsize=3)
    ax2.axhline(1.0, color="black", linewidth=1)
    ax2.set_xlabel(r"$k\ [h/\mathrm{Mpc}]$")
    ax2.set_ylabel(f"ratio to {ref['label']}")
    ax2.set_ylim(0.5, 1.5)

    outdir = Path(output_dir).expanduser().resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    plot_path = outdir / "power_spectrum_comparison.png"
    fig.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    return ArtifactResult(
        status="success",
        files=[str(plot_path)],
        message=f"Plotted {len(curves)} spectra against {EBOSS_LABEL}.",
        metadata={"labels": [c["label"] for c in curves],
                  "reference": ref["label"]},
    )
