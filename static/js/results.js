// FLOAT project page — interactive plots powered by Plotly.
//
// Loads pre-extracted JSON data from static/data/ and renders the headline
// charts that mirror the paper's comparison and convergence plots.

const COLORS = {
  ref: "#888888",
  opt1: "#1f77b4",
  opt2: "#d62728",
};

const LABELS = {
  ref: "Reference",
  opt1: "Opt1",
  opt2: "Opt2",
};

const COMMON_LAYOUT = {
  margin: { l: 60, r: 20, t: 50, b: 50 },
  paper_bgcolor: "rgba(0,0,0,0)",
  plot_bgcolor: "rgba(0,0,0,0)",
  font: { family: "Helvetica, Arial, sans-serif", size: 12 },
  hovermode: "closest",
};

function lineTrace(x, y, tag, name) {
  return {
    x: x,
    y: y,
    mode: "lines+markers",
    name: name || LABELS[tag],
    line: { color: COLORS[tag], width: 2.5 },
    marker: { size: 5 },
  };
}

function loadJSON(path) {
  return fetch(path).then((r) => r.json());
}

function setupBibtexCopy() {
  const btn = document.getElementById("copy-bibtex");
  const code = document.getElementById("bibtex-content");
  if (!btn || !code) return;
  btn.addEventListener("click", () => {
    navigator.clipboard
      .writeText(code.innerText)
      .then(() => {
        btn.innerHTML =
          '<span class="icon"><i class="fas fa-check"></i></span><span>Copied!</span>';
        btn.classList.add("is-success");
        setTimeout(() => {
          btn.innerHTML =
            '<span class="icon"><i class="fas fa-copy"></i></span><span>Copy</span>';
          btn.classList.remove("is-success");
        }, 1800);
      })
      .catch((err) => console.error("Copy failed", err));
  });
}

document.addEventListener("DOMContentLoaded", () => {
  setupBibtexCopy();
  loadJSON("static/data/tower_profiles.json").then((d) => {
    // Damage profile
    const damageTraces = ["ref", "opt1", "opt2"].map((tag) => ({
      x: d[tag].section_damage,
      y: d[tag].z_mean_section,
      mode: "lines+markers",
      name: LABELS[tag],
      line: { color: COLORS[tag], width: 2.5, shape: "hvh" },
      marker: { size: 5 },
    }));
    damageTraces.push({
      x: [1, 1],
      y: [Math.min(...d.ref.z_mean_section), Math.max(...d.ref.z_mean_section)],
      mode: "lines",
      name: "Upper bound (1.0)",
      line: { dash: "dash", color: "#444", width: 1.5 },
    });
    Plotly.newPlot(
      "plot-damage",
      damageTraces,
      Object.assign({}, COMMON_LAYOUT, {
        title: "Tower section fatigue damage",
        xaxis: { title: "Cumulative damage [-]", type: "log" },
        yaxis: { title: "Tower height [m]" },
      }),
      { responsive: true },
    );

    // Geometry: outer diameter vs height
    Plotly.newPlot(
      "plot-geometry",
      ["ref", "opt1", "opt2"].map((tag) =>
        lineTrace(d[tag].outer_diameter, d[tag].z, tag),
      ),
      Object.assign({}, COMMON_LAYOUT, {
        title: "Outer diameter profile",
        xaxis: { title: "Outer diameter [m]" },
        yaxis: { title: "Tower height [m]" },
      }),
      { responsive: true },
    );

    // Wall thickness
    Plotly.newPlot(
      "plot-thickness",
      ["ref", "opt1", "opt2"].map((tag) =>
        lineTrace(d[tag].wall_thickness_mm, d[tag].z, tag),
      ),
      Object.assign({}, COMMON_LAYOUT, {
        title: "Wall thickness profile",
        xaxis: { title: "Wall thickness [mm]" },
        yaxis: { title: "Tower height [m]" },
      }),
      { responsive: true },
    );

    // Stress
    Plotly.newPlot(
      "plot-stress",
      ["ref", "opt1", "opt2"].map((tag) =>
        lineTrace(d[tag].stress_MPa, d[tag].z_stress, tag),
      ),
      Object.assign({}, COMMON_LAYOUT, {
        title: "Axial stress profile",
        xaxis: { title: "Axial stress [MPa]" },
        yaxis: { title: "Tower height [m]" },
      }),
      { responsive: true },
    );
  });

  loadJSON("static/data/optimization_convergence.json").then((d) => {
    // Objective function convergence
    const objTraces = ["opt1", "opt2"].map((tag) => ({
      x: d[tag].iterations,
      y: d[tag].objective_values.map((v) => v / 1000),
      mode: "lines+markers",
      name: LABELS[tag],
      line: { color: COLORS[tag], width: 2.5 },
      marker: { size: 6 },
    }));
    Plotly.newPlot(
      "plot-objective",
      objTraces,
      Object.assign({}, COMMON_LAYOUT, {
        title: "Objective function (tower mass) evolution",
        xaxis: { title: "Iteration" },
        yaxis: { title: "Tower mass [t]" },
      }),
      { responsive: true },
    );

    // Fatigue damage constraint evolution (max value)
    const damKey = "towerse.fatigue_section_damage";
    const constraintTraces = [];
    ["opt1", "opt2"].forEach((tag) => {
      const cmax = d[tag].constraints_max[damKey];
      const cmin = d[tag].constraints_min[damKey];
      if (cmax) {
        constraintTraces.push({
          x: d[tag].iterations,
          y: cmax,
          mode: "lines+markers",
          name: `${LABELS[tag]} max`,
          line: { color: COLORS[tag], width: 2.5 },
          marker: { size: 5 },
        });
      }
      if (cmin) {
        constraintTraces.push({
          x: d[tag].iterations,
          y: cmin,
          mode: "lines+markers",
          name: `${LABELS[tag]} min`,
          line: { color: COLORS[tag], width: 1.5, dash: "dash" },
          marker: { size: 4, symbol: "x" },
        });
      }
    });
    constraintTraces.push({
      x: [0, Math.max(...d.opt1.iterations, ...d.opt2.iterations)],
      y: [1, 1],
      mode: "lines",
      name: "Upper bound (1.0)",
      line: { dash: "dash", color: "#444", width: 1.5 },
    });
    Plotly.newPlot(
      "plot-constraint-damage",
      constraintTraces,
      Object.assign({}, COMMON_LAYOUT, {
        title: "Fatigue damage constraint evolution",
        xaxis: { title: "Iteration" },
        yaxis: { title: "Fatigue damage [-]" },
      }),
      { responsive: true },
    );
  });
});
