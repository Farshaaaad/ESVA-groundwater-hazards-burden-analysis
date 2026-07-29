# ESVA Groundwater Hazards and Infrastructure Burden Analysis

Python and ArcPy workflows supporting the manuscript:

**Linking climate-driven groundwater hazards to human exposure and infrastructure burdens in a rural coastal region**

**Author:** Farshad Hesamfar  
**Affiliation:** Department of Civil and Environmental Engineering, University of Virginia  
**Contact:** wky7xx@virginia.edu  
**ORCID:** 0000-0002-5733-8868

## Overview

This repository contains the post-processing and analytical workflows used to calculate and summarize census-block-level groundwater hazard, exposure, risk-intensity, absolute-burden, and equity-weighted-burden metrics for the Eastern Shore of Virginia.

The manuscript provides the scientific rationale and methodological description. This repository provides the executable implementation, quality-assurance outputs, table-generation code, and selected figure-generation code.

The interactive ArcGIS Online layer is a visualization product. The versioned code release and the archived analytical dataset are the reproducibility records.

## Repository contents

```text
.
├── README.md
├── CITATION.cff
├── LICENSE
├── CHANGELOG.md
├── requirements.txt
├── .zenodo.json
├── code/
│   ├── common.py
│   ├── 00_area_weighted_block_aggregation_arcpy.py
│   ├── 01_calculate_swi.py
│   ├── 02_calculate_risk_and_burden.py
│   ├── 03_generate_service_status_tables.py
│   ├── 04_calculate_representation_ratios.py
│   ├── 05_create_swi_exposure_figures.py
│   ├── 99_make_checksums.py
│   └── run_tabular_workflow.py
├── data/
│   └── README.md
├── documentation/
│   ├── data_dictionary_core.csv
│   ├── provenance_inventory_template.csv
│   ├── WORKFLOW.md
│   └── REPOSITORY_CHECKLIST.md
├── outputs/
│   └── .gitkeep
└── tests/
    └── README.md
```

## Software environments

### ArcGIS processing

The following scripts require the Python environment installed with ArcGIS Pro:

- `00_area_weighted_block_aggregation_arcpy.py`
- `01_calculate_swi.py`

Record the ArcGIS Pro version used for the final manuscript release in `documentation/WORKFLOW.md`.

### Tabular analysis and figures

The remaining scripts require Python 3.10 or later and the packages in `requirements.txt`.

```bash
python -m pip install -r requirements.txt
```

## Workflow

### Step 1. Area-weighted groundwater summaries

When the model-grid and census-block intersection are available, calculate block-area-weighted groundwater fields with:

```bash
python code/00_area_weighted_block_aggregation_arcpy.py   --intersect-fc "path/to/model_block_intersection"   --blocks-fc "path/to/census_blocks"   --value-fields "field_1;field_2;field_3"   --output-table "path/to/output.gdb/AreaWeightedStats"   --join-results
```

The repository may instead begin with the final archived block-level groundwater summaries when restricted or very large upstream model files cannot be redistributed.

### Step 2. Calculate annual and peak SWI classifications

Run the publication version in the ArcGIS Pro Python environment:

```bash
python code/01_calculate_swi.py   --feature-class "path/to/analysis.gdb/ESVA_blocks"   --qa-output "outputs/swi_recalculation_qa.csv"
```

The script:

- evaluates 2030, 2040, 2050, 2060, and 2080;
- processes SSP2-4.5 and SSP5-8.5;
- selects the maximum block-level chloride concentration across the model fields for each year and pathway;
- assigns the highest SWI class indicated by projected concentration, absolute increase, or relative increase;
- applies the small-denominator filter described in the manuscript;
- calculates annual and peak SWI fields; and
- records changes to pre-existing output fields in the QA CSV.

The relative-change classes are continuous:

- Slight: 5% to less than 10%
- Early: 10% to less than 20%
- Moderate: 20% to less than 250%
- High: 250% to less than 500%
- Extreme: 500% or greater

Relative change is set to zero when the 2023 baseline chloride concentration is below 10 mg/L or the absolute increase is below 10 mg/L.

### Step 3. Export the corrected analytical feature

Export the corrected feature class as a CSV, Excel workbook, GeoPackage, or zipped file geodatabase. The tabular scripts accept CSV and Excel inputs.

### Step 4. Recalculate metrics and source tables

```bash
python code/run_tabular_workflow.py   --input "data/ESVA_block_analysis_final.xlsx"   --sheet "ESVA_GW_Hazards_Analysis_Social"   --output-dir "outputs"   --make-figures
```

For CSV input, omit `--sheet`.

This workflow creates:

- recalculated risk-intensity fields;
- absolute-burden fields;
- equity-weighted-burden fields;
- a risk/burden QA comparison;
- populated-block service-status tables;
- all-block service-status tables;
- severe-SWI representation ratios; and
- optional SWI composite exposure figures.

## Burden definitions

- **Risk intensity** combines hazard intensity, social vulnerability, and the relevant public-utility deficit. Waterlogging risk does not use a utility-service multiplier.
- **Absolute burden** is hazard intensity multiplied by the relevant exposed population or infrastructure count.
- **Equity-weighted burden** is risk intensity multiplied by the relevant exposed population or infrastructure count.

Burden outputs are weighted units, not literal counts of failed systems or affected people.

## Data availability

The GitHub repository contains only code and documentation.

The final analytical data will be archived in a trusted repository such as the University of Virginia LibraData repository and cited using its permanent DOI. We will replace the placeholder below after the record is created:

**Data DOI:**  [https://doi.org/10.5281/zenodo.21693760](https://doi.org/10.5281/zenodo.21693760)

The ArcGIS Online item may be linked as an interactive, read-only visualization, but it does not replace the archived analytical data.
[https://uvalibrary.maps.arcgis.com/home/item.html?id=80765d3e6e274c168e38e3184800f534](https://uvalibrary.maps.arcgis.com/home/item.html?id=80765d3e6e274c168e38e3184800f534)

```bash
python code/99_make_checksums.py --root .
```

## Citation

Use the citation generated by the WRR paper and [https://doi.org/10.5281/zenodo.21693760](https://doi.org/10.5281/zenodo.21693760).

## License

The software is released under the MIT License. Source datasets retain the licenses and restrictions imposed by their original custodians.
