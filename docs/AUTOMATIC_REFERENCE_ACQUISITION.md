# Automatic reference acquisition

The five Python distributions remain independent. The core contains only
reference abstractions, integrity checks, and provider discovery.

## Normal usage

Install the code for each reference family required by the application.
Installation and import do **not** fetch scientific data.

```bash
python -m pip install pedgrowth pedgrowth-data-who2006
```

```python
from pedgrowth import GrowthChartsCalculator
from pedgrowth.data.who2006 import WhoPlan

calculator = GrowthChartsCalculator(plan=WhoPlan())
```

On first access to a requested table, the WHO extension looks for verified
reference files. Creating a plan or legacy calculator alone does not download. When missing, it downloads the source XLSX files directly
from WHO, checks each pinned source SHA-256, normalizes the coefficients, and
compiles verified `.lmsb` files in a persistent per-user reference cache.
Subsequent uses are entirely offline. A changed or mismatching source fails
closed: the library never silently falls back to another reference version.

The WHO 2007 extension follows the same lifecycle. The CDC extension also
fetches its original, checksum-pinned **CSV** source files on first use,
normalizes them without changing their substantive numerical content, and
compiles them into the same verified LMSB cache. No CDC coefficients ship with
the provider package. Requests use a project-identifying browser-compatible user-agent. If
upstream access fails in a particular environment, failures are reported
and retried rather than silently ignored.

**INTERGROWTH does not use LMSB.** Its 43 published regression parameters are
reconstructed from the equation functions of the checksum-pinned `gigs`
v0.5.2 source archive (rOpenSci GitHub, a separately maintained software
implementation rather than the official INTERGROWTH hosting site) and verified against the existing
parameter JSON SHA-256. The download is performed when an INTERGROWTH calculation table or calculator is instantiated; merely constructing IntergrowthPlan is offline. We do not ship the 43 numerical
coefficients in its wheel or sdist.

## Optional initialization of all installed extensions

```python
from pedgrowth.data import download_missing_dependencies

installed_counts = download_missing_dependencies()
```

This proactively initializes every discovered extension that declares an
acquisition callback; results map provider names to the number of newly
installed verified resources. CDC reports its number of newly installed tables. In bulk initialization, a missing source generates a RuntimeWarning naming its table or provider, and remaining sources are still attempted. A subsequent initialization retries it. Calculations needing the unavailable table raise DataError; unrelated tables remain usable. The call is optional; there is no
separate required CLI installation step.

## Cache and security

- Downloaded data are **never** written into the Python installation or
  virtual environment. The default location is the platform's pedgrowth user
  data directory (Linux: `~/.local/share/pedgrowth/references`; Windows:
  `%LOCALAPPDATA%/pedgrowth/references`). Data are namespaced by provider and
  a digest of its audited reference manifest.
- Set `PEDGROWTH_REFERENCE_DIR` to select a specific, already provisioned
  directory. This also makes fully offline deployments possible.
- HTTPS source links, pinned source digests, normalized-content digests and
  compiled-resource digests are verified; downloads are size-bounded.
- Files are atomically installed under a provider lock, protecting concurrent
  initializations. No external code or R interpreter runs during acquisition.
- New provider versions do not silently overwrite earlier cache versions.
- Existing scientific files already tracked in Git are **not** untracked by
  `.gitignore`; the repository's current index/history must be reviewed and
  sanitized before any public GitHub release.
  Because downloaded data reside outside the installed distribution, they
  are not removed automatically by pip uninstall.

## Distribution and licensing

All four extension wheels and source distributions contain **only code,
source manifests and provenance metadata**—no scientific coefficient CSVs,
LMSB tables, or fitted INTERGROWTH parameter JSON. CDC source material is
obtained from CDC directly at first use, and separate upstream rights review
remains required.

Users still need permission under the upstream terms to download, transform,
and use these scientific references. The automatic downloader does **not**
grant new licensing rights, and public redistribution of cached data, test
fixtures, or the current private scientific-source checkout must be assessed
separately. See [provider licensing](PROVIDER_LICENSE_RELEASE.md).

Public scientific release must also validate availability and stability of
the pinned upstream endpoints in a clean, network-enabled installation.
