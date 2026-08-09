"""Science tool package. Only names in __all__ become MCP tools.

The power-spectrum example lives in spectra_tools.py; add your own modules
here and extend __all__ to expose new tools — nothing else changes.
"""

from .spectra_tools import (
    ArtifactResult,
    compute_power_spectrum,
    get_eboss_data,
    list_cosmology_models,
    plot_power_spectra,
)

__all__ = [
    "get_eboss_data",
    "list_cosmology_models",
    "compute_power_spectrum",
    "plot_power_spectra",
]
