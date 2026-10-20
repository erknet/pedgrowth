# pedgrowth-data-cdc

Optional **code-only** extension providing CDC 2000 and 2022 growth-reference
table definitions, age/measurement selection policies, and verified on-demand
acquisition of the original CDC reference CSVs.

Install the package with \`pip install pedgrowth-data-cdc\`. No scientific
coefficient files are included in its wheel or source distribution. When a
calculation requires a table for the first time, the extension downloads its
pinned original CDC CSV, checks source/normalized/LMSB SHA-256 values and stores
the binary under the user's pedgrowth reference cache. If a particular CSV is
unavailable, that table fails explicitly and can be retried; other tables
remain usable.

To check and retrieve all available registered references in advance:

\`\`\`python
from pedgrowth.data import download_missing_dependencies
download_missing_dependencies()
\`\`\`

**License:** independently authored Python code is MIT, copyright © 2026
ERKNet. Original CDC scientific datasets are **not licensed under MIT by this
project**. Most CDC materials are U.S. federal public-domain works subject to
specific CDC use conditions, third-party exceptions, and potential
international limitations. Attribute CDC as the source; do not imply CDC/HHS
endorsement. The original reference data are freely available at
[CDC Growth Charts](https://www.cdc.gov/growthcharts/cdc-data-files.htm) and
[2022 Extended BMI](https://www.cdc.gov/growthcharts/extended-bmi-data-files.htm).

**Redistribution and automated-use rights review is still pending.**
See [SOURCE_RIGHTS.md](SOURCE_RIGHTS.md) for scope, attribution, the
non-endorsement statement, and the official CDC policy.
