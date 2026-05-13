// FLOAT project page — interactive plot driven by a picker + case toggles.

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
  margin: { l: 60, r: 30, t: 50, b: 60 },
  paper_bgcolor: "rgba(0,0,0,0)",
  plot_bgcolor: "rgba(0,0,0,0)",
  font: { family: "Helvetica, Arial, sans-serif", size: 13 },
  hovermode: "closest",
};

const DAMAGE_KEY = "towerse.fatigue_section_damage";

// Plot definitions: each one returns {traces, layout} given the data + active cases.
const PLOTS = {
  damage: {
    needs: "profiles",
    build: (d, active) => {
      const traces = active.map((tag) => ({
        x: d[tag].section_damage,
        y: d[tag].z_mean_section,
        mode: "lines+markers",
        name: LABELS[tag],
        line: { color: COLORS[tag], width: 2.5, shape: "hvh" },
        marker: { size: 6 },
      }));
      if (active.length) {
        const zs = d[active[0]].z_mean_section;
        traces.push({
          x: [1, 1],
          y: [Math.min(...zs), Math.max(...zs)],
          mode: "lines",
          name: "Upper bound (1.0)",
          line: { dash: "dash", color: "#444", width: 1.5 },
        });
      }
      return {
        traces,
        layout: {
          title: "Tower section fatigue damage",
          xaxis: { title: "Cumulative damage [-] (log)", type: "log" },
          yaxis: { title: "Tower height [m]" },
        },
      };
    },
  },
  geometry: {
    needs: "profiles",
    build: (d, active) => ({
      traces: active.map((tag) => ({
        x: d[tag].outer_diameter,
        y: d[tag].z,
        mode: "lines+markers",
        name: LABELS[tag],
        line: { color: COLORS[tag], width: 2.5 },
      })),
      layout: {
        title: "Outer diameter profile",
        xaxis: { title: "Outer diameter [m]" },
        yaxis: { title: "Tower height [m]" },
      },
    }),
  },
  thickness: {
    needs: "profiles",
    build: (d, active) => ({
      traces: active.map((tag) => ({
        x: d[tag].wall_thickness_mm,
        y: d[tag].z,
        mode: "lines+markers",
        name: LABELS[tag],
        line: { color: COLORS[tag], width: 2.5, shape: "hvh" },
      })),
      layout: {
        title: "Wall thickness profile",
        xaxis: { title: "Wall thickness [mm]" },
        yaxis: { title: "Tower height [m]" },
      },
    }),
  },
  stress: {
    needs: "profiles",
    build: (d, active) => ({
      traces: active.map((tag) => ({
        x: d[tag].stress_MPa,
        y: d[tag].z_stress,
        mode: "lines+markers",
        name: LABELS[tag],
        line: { color: COLORS[tag], width: 2.5 },
      })),
      layout: {
        title: "Axial stress profile",
        xaxis: { title: "Axial stress [MPa]" },
        yaxis: { title: "Tower height [m]" },
      },
    }),
  },
  deflection: {
    needs: "profiles",
    build: (d, active) => ({
      traces: active.map((tag) => ({
        x: d[tag].deflection,
        y: d[tag].z_deflection,
        mode: "lines+markers",
        name: LABELS[tag],
        line: { color: COLORS[tag], width: 2.5 },
      })),
      layout: {
        title: "Tower deflection profile",
        xaxis: { title: "Lateral deflection [m]" },
        yaxis: { title: "Tower height [m]" },
      },
    }),
  },
  shell_buckling: {
    needs: "profiles",
    build: (d, active) => ({
      traces: active.map((tag) => ({
        x: d[tag].shell_buckling,
        y: d[tag].z_buckling,
        mode: "lines+markers",
        name: LABELS[tag],
        line: { color: COLORS[tag], width: 2.5 },
      })),
      layout: {
        title: "Shell buckling profile",
        xaxis: { title: "Shell buckling utilisation [-]" },
        yaxis: { title: "Tower height [m]" },
      },
    }),
  },
  global_buckling: {
    needs: "profiles",
    build: (d, active) => ({
      traces: active.map((tag) => ({
        x: d[tag].global_buckling,
        y: d[tag].z_buckling,
        mode: "lines+markers",
        name: LABELS[tag],
        line: { color: COLORS[tag], width: 2.5 },
      })),
      layout: {
        title: "Global buckling profile",
        xaxis: { title: "Global buckling utilisation [-]" },
        yaxis: { title: "Tower height [m]" },
      },
    }),
  },
  objective: {
    needs: "convergence",
    build: (d, active) => ({
      traces: active
        .filter((tag) => d[tag])
        .map((tag) => ({
          x: d[tag].iterations,
          y: d[tag].objective_values,
          mode: "lines+markers",
          name: LABELS[tag],
          line: { color: COLORS[tag], width: 2.5 },
          marker: { size: 7 },
        })),
      layout: {
        title: "Objective function (tower mass) evolution",
        xaxis: { title: "Iteration", dtick: 1 },
        yaxis: { title: "Tower mass [t]" },
      },
    }),
  },
  constraint_damage: convergenceBuilder(
    DAMAGE_KEY,
    "Fatigue damage constraint evolution",
    "Fatigue damage [-]",
    1.0,
  ),
  constraint_stress: convergenceBuilder(
    "stress",
    "Stress constraint evolution",
    "Stress ratio [-]",
    1.0,
  ),
  constraint_global_buckling: convergenceBuilder(
    "global_buckling",
    "Global buckling constraint evolution",
    "Global buckling ratio [-]",
    1.0,
  ),
  constraint_shell_buckling: convergenceBuilder(
    "shell_buckling",
    "Shell buckling constraint evolution",
    "Shell buckling ratio [-]",
    1.0,
  ),
};

function convergenceBuilder(key, title, yLabel, upperBound) {
  return {
    needs: "convergence",
    build: (d, active) => {
      const traces = [];
      let maxIter = 0;
      active.forEach((tag) => {
        if (!d[tag] || !d[tag].constraints_max[key]) return;
        const cmax = d[tag].constraints_max[key];
        const cmin = d[tag].constraints_min[key];
        traces.push({
          x: d[tag].iterations,
          y: cmax,
          mode: "lines+markers",
          name: `${LABELS[tag]} max`,
          line: { color: COLORS[tag], width: 2.5 },
          marker: { size: 6 },
        });
        if (cmin) {
          traces.push({
            x: d[tag].iterations,
            y: cmin,
            mode: "lines+markers",
            name: `${LABELS[tag]} min`,
            line: { color: COLORS[tag], width: 1.5, dash: "dash" },
            marker: { size: 5, symbol: "x" },
          });
        }
        maxIter = Math.max(maxIter, ...d[tag].iterations);
      });
      if (traces.length && upperBound != null) {
        traces.push({
          x: [0, maxIter],
          y: [upperBound, upperBound],
          mode: "lines",
          name: `Upper bound (${upperBound})`,
          line: { dash: "dash", color: "#444", width: 1.5 },
        });
      }
      return {
        traces,
        layout: {
          title,
          xaxis: { title: "Iteration", dtick: 1 },
          yaxis: { title: yLabel },
        },
      };
    },
  };
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

function setupInteractivePlot(profiles, convergence) {
  const picker = document.getElementById("plot-picker");
  const checkboxes = document.querySelectorAll("#case-toggles input");
  const target = document.getElementById("plot-main");
  if (!picker || !target) return;

  function render() {
    const def = PLOTS[picker.value];
    if (!def) return;
    const data = def.needs === "convergence" ? convergence : profiles;
    const active = Array.from(checkboxes)
      .filter((c) => c.checked)
      .map((c) => c.dataset.case);
    const { traces, layout } = def.build(data, active);
    Plotly.react(
      target,
      traces,
      Object.assign({}, COMMON_LAYOUT, layout),
      { responsive: true, displaylogo: false },
    );
  }

  picker.addEventListener("change", render);
  checkboxes.forEach((c) => c.addEventListener("change", render));
  render();
}

document.addEventListener("DOMContentLoaded", () => {
  setupBibtexCopy();
  Promise.all([
    fetch("static/data/tower_profiles.json").then((r) => r.json()),
    fetch("static/data/optimization_convergence.json").then((r) => r.json()),
  ]).then(([profiles, convergence]) => {
    setupInteractivePlot(profiles, convergence);
  });
});
