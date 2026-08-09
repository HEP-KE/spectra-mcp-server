"""Tests for the science tools as plain Python — no MCP layer needed."""

import numpy as np
import pytest

from tools import (
    compute_power_spectrum,
    get_eboss_data,
    list_cosmology_models,
    plot_power_spectra,
)


def test_get_eboss_data_returns_19_bins():
    result = get_eboss_data()
    assert result.status == "success"
    assert len(result.metadata["k_h_per_Mpc"]) == 19
    assert len(result.metadata["Pk_Mpc_over_h_cubed"]) == 19
    assert len(result.metadata["sigma_Pk"]) == 19


def test_eboss_k_is_converted_to_h_units():
    # File k column is 1/Mpc (mpk_compilation convention); tool must serve h/Mpc.
    k = get_eboss_data().metadata["k_h_per_Mpc"]
    assert 0.30 < k[0] < 0.32
    assert 3.70 < k[-1] < 3.80


def test_list_cosmology_models_names():
    result = list_cosmology_models()
    assert set(result.metadata["models"]) == {"lcdm", "nu_mass", "wcdm"}


def test_compute_power_spectrum_writes_csv(tmp_path):
    result = compute_power_spectrum(
        model="lcdm", output_dir=str(tmp_path), k_min=0.01, k_max=1.0, n_points=20
    )
    (csv_path,) = result.files
    assert csv_path.endswith("pk_lcdm.csv")
    first_line = open(csv_path, encoding="utf-8").readline()
    assert first_line.startswith("# label:")
    k, pk = np.loadtxt(csv_path, delimiter=",", skiprows=2).T
    assert len(k) == 20
    assert np.all(pk > 0)


def test_compute_rejects_unknown_model(tmp_path):
    with pytest.raises(Exception):
        compute_power_spectrum(model="sCDM", output_dir=str(tmp_path))


def _write_fixture_csv(path, label, scale):
    """Fake spectrum CSV so the plot test runs without classy."""
    k = np.logspace(-3, 0.5, 50)
    pk = scale * 1e4 * (k / 0.01) ** -1.8
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# label: {label}\n")
        f.write("k_h_per_Mpc,Pk_Mpc_over_h_cubed\n")
        for ki, pki in zip(k, pk):
            f.write(f"{ki},{pki}\n")


def test_plot_power_spectra_from_fixtures(tmp_path):
    files = []
    for name, scale in [("ref", 1.0), ("alt", 0.9)]:
        path = tmp_path / f"pk_{name}.csv"
        _write_fixture_csv(path, name.upper(), scale)
        files.append(str(path))

    result = plot_power_spectra(spectrum_files=files, output_dir=str(tmp_path))
    (png_path,) = result.files
    assert png_path.endswith("power_spectrum_comparison.png")
    assert result.metadata["reference"] == "REF"


def test_plot_rejects_bad_reference_index(tmp_path):
    path = tmp_path / "pk_ref.csv"
    _write_fixture_csv(path, "REF", 1.0)
    with pytest.raises(ValueError):
        plot_power_spectra(
            spectrum_files=[str(path)], output_dir=str(tmp_path), reference_index=3
        )
