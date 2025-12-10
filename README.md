<p align="center">
  <img src="./images/float_logo.png" alt="FLOAT Logo" width="300">
</p>

# FLOAT: Fatigue-Aware Design Optimization of Wind Turbine Towers
<p align="center">
  <a href="https://arxiv.org/abs/2502.02594">
    <img src="https://img.shields.io/badge/arXiv-2502.02594-b31b1b.svg">
  </a>
  <a href="https://www.apache.org/licenses/LICENSE-2.0">
    <img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg">
  </a>
</p>

<p align="center"><strong>Fast tower fatigue estimation during design optimization, without rerunning high-fidelity simulations.</strong></p>


**FLOAT** is a **lightweight fatigue-aware tower design framework** integrated into [WISDEM](https://github.com/wisdem). It enables **fast estimation of cumulative tower fatigue damage** by scaling precomputed high-fidelity fatigue results from a reference wind turbine tower to any new tower geometry under evaluation.

This allows **fatigue-aware analysis and design optimization** to be performed **without rerunning expensive aero-hydro-servo-elastic simulations**, reducing computational cost by several orders of magnitude while maintaining validated accuracy with low error.

<p align="center">
  <img src="./images/float_workflow.png" alt="FLOAT workflow" width="1000">
</p>

### Authors: 
- **João Alves Ribeiro** (MIT & University of Porto) — [jpar@mit.edu](mailto:jpar@mit.edu)
- **Francisco Pimenta** (University of Porto)
- **Bruno Alves Ribeiro** (TU Delft & Brown University)
- **Sérgio M. O. Tavares** (University of Aveiro)
- **Faez Ahmed** (MIT) — [faez@mit.edu](mailto:faez@mit.edu)


## FLOAT Paper 

**FLOAT** is presented in the following scientific paper, where the methodology implemented in this repository is fully described and validated: [**FLOAT: Fatigue-Aware Design Optimization of Wind Turbine Towers**](https://arxiv.org/abs/2502.02594).

<p align="center">
  <img src="./images/float_paper_abstract.png" alt="FLOAT paper abstract" width="1000">
</p>

Using the **FLOAT** methodology, the [**IEA 22 MW**](https://github.com/IEAWindSystems/IEA-22-280-RWT) floating reference tower was successfully redesigned under fatigue constraints, achieving:
- **Fatigue lifetime extension:** from **~9 months to 25 years** (**~33× increase in fatigue life**)  
- **Validation accuracy:** agreement with **6,468 coupled wind–wave high-fidelity OpenFAST simulations** with a **mean relative error of −8.6%**  
- **Computational speed-up:** FLOAT removes the need to re-run full aero-hydro-servo-elastic simulations during redesign, cutting computational cost by **several orders of magnitude** compared with traditional fatigue-driven design loops.

The final redesigned tower configuration is openly available here: [**FLOAT-22-280-RWT-Semi**](https://github.com/Joao97ribeiro/FLOAT-22-280-RWT-Semi).

The paper introduces the full **FLOAT architecture**:

<p align="center">
  <img src="./images/float_paper_workflow.png" alt="FLOAT paper workflow" width="1000">
</p>

**Note:** This repository currently includes **only Module 6: the Fatigue Estimator**, which corresponds to the lightweight fatigue scaling model.

The remaining components of the full FLOAT framework:

- **1. Wind–Wave Sampler:** Probabilistic wind–wave sampling.
- **2. Numerical Simulator:** High-fidelity OpenFAST calibration and HPC-based large-scale simulation workflows.
- **3. Frequency Analyzer:** Spectral stress processing.
- **4. Fatigue Analyzer:** Fatigue damage accumulation.

are planned to be released as open-source in future updates. The **5. Design Optimizer** is already implemented in **WISDEM**.


## What FLOAT Adds to WISDEM

This repository extends the native **_TowerSE_** module of **WISDEM** with a new **fatigue-aware model** for fast tower fatigue assessment and optimization.

Key additions include:
- A new `fatigue` block in the **TowerSE modeling options input file**.
- Native integration with the **WISDEM optimization workflow** for fatigue-aware tower design and optimization.

All remaining WISDEM modules remain unchanged and follow the official upstream implementation.


## How to Use FLOAT

To activate **FLOAT**, a `fatigue` block must be added to the **TowerSE modeling options input file**, following the structure below:

```yaml
WISDEM:
  TowerSE:
    flag: True

    fatigue:
      m: ...
      k: ...
      t_ref: ...

      tower_ref:
        grid: [...]
        outer_diameter: [...]
        wall_thickness: [...]
        z: [...]
        section_damage: [...]
```

where, for a tower with $N$ sections:

- The **material fatigue properties**:
  - `m` (float): S–N curve slope  
  - `k` (float): thickness exponent  
  - `t_ref` (float): reference design lifetime [years]  

- The **reference tower geometry**:
  - `grid` (array, size $N+1$): normalized vertical coordinate at each **section transition** along the tower (0 = base, 1 = top)
  - `outer_diameter` (array, size $N+1$): outer diameter at each **section transition** of the reference tower [m]
  - `wall_thickness` (array, size $N$): wall thickness at each **tower section** [m]
  - `z` (array, size $N+1$): physical height coordinate at each **section transition** [m]

- The **high-fidelity reference fatigue damage distribution**:
  - `section_damage` (array, size $N$): cumulative fatigue damage per **tower section**, evaluated at the **section midpoint**


## Integration with the WISDEM Workflow

FLOAT integrates directly into the standard WISDEM workflow, which is based on three standard input files:

- **Modeling options file** (e.g. `modeling_options.yaml`)  
  This is where FLOAT is activated through the `fatigue` block inside the `TowerSE` section.

- **Turbine input file** (e.g. `IEA-22-280-RWT.yaml`)  
  Standard WISDEM turbine definition including geometry, materials, and main properties.

- **Analysis options file** (e.g. `analysis_options.yaml`)  
  Standard WISDEM simulation setup, load cases, and optional optimization configuration.

After defining these three files, WISDEM is executed normally.  
During the **TowerSE** execution, FLOAT automatically computes the fatigue damage for the new tower design **without re-running high-fidelity simulations**.


## Examples

The repository includes **two example cases** demonstrating how to run **fatigue-aware tower analysis with FLOAT inside WISDEM**.

Both examples use the [**IEA-22-280-RWT**](https://github.com/IEAWindSystems/IEA-22-280-RWT) reference turbine.

<p align="center">
  <img src="./images/iea_22mw.gif" alt="IEA 22 MW Floating Wind Turbine" width="300">
</p>

- [`examples/01_tower_fatigue_analysis/`](./examples/01_tower_fatigue_analysis)  
  **Fatigue-Aware Tower Analysis (IEA 22 MW)** — Performs fatigue post-processing of the reference tower using the FLOAT lightweight scaling model.

- [`examples/02_tower_fatigue_analysis/`](./examples/02_tower_fatigue_analysis)  
  **Fatigue-Aware Tower Optimization (IEA 22 MW)** — Demonstrates the integration of FLOAT inside a tower design optimization loop, where fatigue damage directly influences the optimized tower geometry.


## Documentation

The theoretical background and validation of the method are fully presented in the [**FLOAT paper**](https://arxiv.org/abs/2502.02594).  
Practical usage is demonstrated through the [`examples/`](./examples) scripts and inline docstrings provided in this repository.


## Installation

**FLOAT** runs inside a dedicated Conda environment for full compatibility with [WISDEM](https://github.com/WISDEM/WISDEM).

We recommend using [Miniforge3](https://github.com/conda-forge/miniforge) as a lightweight and more reliable alternative to [Anaconda](https://www.anaconda.com) for faster and more robust dependency resolution.


### 1. Create the Conda Environment
```bash
git clone https://github.com/Joao97ribeiro/FLOAT.git
cd FLOAT
conda env create -n float-env -f environment.yml
conda activate float-env
```
The environment name `"float-env"` is only a suggestion. You may choose any name.

### 2.  Install FLOAT in Developer Mode
```bash
pip install --no-deps -e . -v
```


## License

This project is licensed under the **Apache License 2.0**.  
See the [LICENSE](./LICENSE) file for full details or view it online at: [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0).


## Citations

If you use **FLOAT** in your work, please cite:

> *FLOAT: Fatigue-Aware Design Optimization of Wind Turbine Towers.*  
> João Alves Ribeiro, Francisco Pimenta, Bruno Alves Ribeiro, Sérgio M. O. Tavares, Faez Ahmed.  
> arXiv:2502.02594, 2025.  
> https://arxiv.org/abs/2502.02594

<details>
<summary>BibTeX</summary>

```bibtex
@article{ribeiro2025float,
  title   = {FLOAT: Fatigue-Aware Design Optimization of Wind Turbine Towers},
  author  = {Ribeiro, Jo{\~a}o Alves and Pimenta, Francisco and Ribeiro, Bruno Alves and Tavares, S{\'e}rgio M. O. and Ahmed, Faez},
  journal = {arXiv preprint arXiv:2502.02594},
  year    = {2025}
}
```
</details> 


## Maintenance & Support

For issues, questions, or feature requests related to FLOAT: [FLOAT Issues](https://github.com/Joao97ribeiro/FLOAT/issues).

## Acknowledgements
We thank [Garrett Barter](https://github.com/gbarter), [Pietro Bortolotti](https://github.com/ptrbortolotti), and [Daniel Zalkind](https://github.com/dzalkind) from the National Renewable Energy Laboratory (NREL) for their insightful discussions and technical guidance.

This work builds on a fork of [WISDEM](https://github.com/WISDEM/WISDEM). We acknowledge the WISDEM team for creating the open foundation that made this work possible.
