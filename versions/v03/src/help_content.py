"""Help HTML pages for CalEnEff — opened in the system browser via webbrowser."""

_APP_VERSION = "3.0"
_GITHUB_URL  = "https://github.com/grainovski/CalEnEff"

_CSS = """
:root {
    --bg:     #1e1e2e;
    --panel:  #2a2a3e;
    --panel2: #25253a;
    --accent: #89b4fa;
    --green:  #a6e3a1;
    --red:    #f38ba8;
    --yellow: #f9e2af;
    --text:   #cdd6f4;
    --muted:  #9090a8;
    --border: #45475a;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    background: var(--bg);
    color: var(--text);
    font-family: 'Segoe UI', system-ui, sans-serif;
    font-size: 15px;
    line-height: 1.65;
    max-width: 860px;
    margin: 0 auto;
    padding: 36px 28px 60px;
}
h1 { color: var(--accent); font-size: 1.9em; margin-bottom: 4px; }
.subtitle { color: var(--muted); margin-bottom: 36px; font-size: 0.95em; }
h2 {
    color: var(--accent);
    font-size: 1.15em;
    border-bottom: 1px solid var(--border);
    padding-bottom: 6px;
    margin-top: 36px;
    margin-bottom: 14px;
}
h3 { color: var(--green); font-size: 1em; margin: 18px 0 6px; }
p { margin-bottom: 10px; }
ul, ol { padding-left: 22px; margin-bottom: 10px; }
li { margin-bottom: 5px; }
a { color: var(--accent); }
code {
    background: var(--panel);
    color: var(--yellow);
    padding: 1px 6px;
    border-radius: 3px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 0.88em;
}
.formula {
    background: var(--panel);
    color: var(--green);
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 0.93em;
    padding: 10px 16px;
    border-radius: 5px;
    margin: 8px 0 12px;
    overflow-x: auto;
}
.note {
    background: var(--panel);
    border-left: 3px solid var(--accent);
    padding: 10px 16px;
    border-radius: 0 5px 5px 0;
    margin: 12px 0;
    font-size: 0.93em;
    color: var(--muted);
}
.note b { color: var(--text); }
table {
    border-collapse: collapse;
    width: 100%;
    margin: 10px 0 14px;
    font-size: 0.91em;
}
th {
    background: var(--panel);
    color: var(--accent);
    padding: 8px 12px;
    text-align: left;
    border: 1px solid var(--border);
}
td { padding: 7px 12px; border: 1px solid var(--border); }
tr:nth-child(even) td { background: var(--panel2); }
.steps { list-style: none; padding: 0; }
.steps li {
    display: flex;
    gap: 14px;
    align-items: flex-start;
    margin-bottom: 14px;
}
.sn {
    background: var(--accent);
    color: var(--bg);
    font-weight: 700;
    font-size: 0.85em;
    min-width: 26px;
    height: 26px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    margin-top: 2px;
}
.steps li > div > b { color: var(--accent); }
"""


def build_howto_html():
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CalEnEff — HowTo</title>
<style>{_CSS}</style>
</head>
<body>
<h1>CalEnEff</h1>
<p class="subtitle">Energy &amp; Efficiency Calibration &mdash; Monte Carlo Fit &nbsp;&mdash;&nbsp; v{_APP_VERSION} HowTo</p>

<h2>Quick Start</h2>
<ol class="steps">
  <li><div class="sn">1</div><div>
    <b>Read calibration data</b> &mdash; click the button and select your 7-column
    calibration file. The raw data scatter plots update immediately.
  </div></li>
  <li><div class="sn">2</div><div>
    <b>Make calibration</b> &mdash; runs energy (linear &amp; quadratic) and efficiency
    Monte Carlo fits (10&thinsp;000 iterations each, ~10&ndash;20&thinsp;s). Parameters
    appear in the left panel; residual and efficiency curves update.
  </div></li>
  <li><div class="sn">3</div><div>
    <b>Query energy</b> &mdash; enter a channel centroid <i>ch&#8320;</i> and its
    uncertainty <i>&Delta;ch&#8320;</i>, then press <code>Enter</code> or
    &ldquo;Calculate Energy&rdquo;. MC-propagated energy and uncertainty appear in the
    energy result panel; any previous efficiency query is cleared.
  </div></li>
  <li><div class="sn">4</div><div>
    <b>Query efficiency</b> &mdash; enter an energy <i>E&#8320;</i> (keV), then press
    <code>Enter</code> or &ldquo;Get Efficiency&rdquo;. Results show MC mean &plusmn;
    1&sigma; and best-fit value, in a.u. or %; any previous energy query is cleared.
  </div></li>
  <li><div class="sn">5</div><div>
    <b>Clear</b> &mdash; either <code>&times; Clear</code> button resets both query
    panels without re-running the calibration.
  </div></li>
  <li><div class="sn">6</div><div>
    <b>Save a figure</b> &mdash; <b>right-click a subplot</b> &rarr; Save As
    (that panel only). <b>Right-click the figure margin</b> &rarr; Save As (full
    figure). Formats: PNG, PDF, SVG, EPS, PS, JPEG, TIFF, WebP.
  </div></li>
  <li><div class="sn">7</div><div>
    <b>Toggle theme</b> &mdash; <code>&#9728; Light / &#127769; Dark</code> button
    (top-right corner) switches between colour palettes without reloading data.
  </div></li>
</ol>

<h2>Data File Format</h2>
<p>Plain text, space- or tab-separated, <b>7 columns</b>, no header row,
<b>absolute</b> uncertainties (1&sigma;):</p>
<table>
  <tr><th>#</th><th>Column</th><th>Unit</th><th>Description</th></tr>
  <tr><td>1</td><td>ch</td><td>channels</td><td>Peak centroid channel</td></tr>
  <tr><td>2</td><td>&Delta;ch</td><td>channels</td><td>Centroid uncertainty (absolute)</td></tr>
  <tr><td>3</td><td>N</td><td>counts</td><td>Net peak area</td></tr>
  <tr><td>4</td><td>&Delta;N</td><td>counts</td><td>Area uncertainty (absolute)</td></tr>
  <tr><td>5</td><td>E</td><td>keV</td><td>Literature gamma-ray energy</td></tr>
  <tr><td>6</td><td>I</td><td>%</td><td>Emission intensity (relative)</td></tr>
  <tr><td>7</td><td>&Delta;I</td><td>%</td><td>Intensity uncertainty (absolute)</td></tr>
</table>
<div class="note">
  <b>Derived quantities computed internally:</b><br>
  Measured efficiency: &epsilon; = N&thinsp;/&thinsp;I<br>
  Propagated uncertainty: &Delta;&epsilon; = &epsilon;&thinsp;&sdot;&thinsp;&radic;[(ΔN/N)&sup2; + (&Delta;I/I)&sup2;]
</div>

<h2>Energy Calibration</h2>
<p>Two models are fitted simultaneously by weighted least squares and shown in the
calibration plot together with residuals:</p>
<div class="formula">Linear:    ch(E) = a + b&middot;E
Quadratic: ch(E) = a + b&middot;E + c&middot;E&sup2;</div>

<h3>Parameter uncertainties</h3>
<table>
  <tr><th>Label</th><th>Formula</th><th>Meaning</th></tr>
  <tr><td>stat</td><td>&radic;diag(C)</td><td>1&sigma; from the covariance matrix</td></tr>
  <tr><td>Birge</td><td>stat &times; B</td><td>Uncertainty scaled by the Birge ratio B = &radic;(&chi;&sup2;/ndf)</td></tr>
</table>
<p>The <b>Birge ratio</b> B diagnoses fit quality relative to stated uncertainties:</p>
<ul>
  <li>B &asymp; 1 &mdash; scatter matches stated &sigma; (fit is consistent)</li>
  <li>B &gt; 1 &mdash; data scatter more than expected (uncertainties inflated by B)</li>
  <li>B &lt; 1 &mdash; stated uncertainties are conservative</li>
</ul>

<h2>Efficiency Calibration</h2>
<p>A semi-empirical model is fitted by weighted non-linear least squares:</p>
<div class="formula">&epsilon;(E) = (a&middot;E + b/E) &middot; exp(c&middot;E + d/E)</div>
<p>Monte Carlo propagation (10&thinsp;000 trials) draws parameter vectors from the
covariance matrix and evaluates &epsilon; at the query energy, producing a mean,
standard deviation, and best-fit value. Results can be displayed in a.u. (the
natural units of N/I) or converted to % using the toggle below the result panel.</p>

<h2>Saving Results</h2>
<p>A results text file is written automatically alongside the loaded data file
whenever a query completes. Use &ldquo;Save results&rdquo; to write it manually at
any point. The filename includes a date/time stamp so successive runs do not
overwrite each other.</p>

<h2>Tips</h2>
<ul>
  <li>Always click <b>Make calibration</b> after loading a new data file &mdash;
      results are not carried forward from a previous run.</li>
  <li>If the quadratic term <i>c</i> is consistent with zero, prefer the linear
      model for energy queries (smaller parameter uncertainty).</li>
  <li>Right-click directly on a curve or data point in the efficiency plot to save
      that panel at full resolution for publications.</li>
  <li>The default data file (<code>226Ra_En_Area.txt</code>, if present in the
      application folder) is loaded automatically on startup.</li>
</ul>
</body>
</html>
"""


def build_about_html():
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CalEnEff — About</title>
<style>{_CSS}
.card {{
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 24px 28px;
    margin-top: 20px;
}}
.kv {{ display: flex; gap: 12px; margin-bottom: 8px; font-size: 0.95em; }}
.kv .key {{ color: var(--muted); min-width: 110px; flex-shrink: 0; }}
.kv .val {{ color: var(--text); }}
</style>
</head>
<body>
<h1>CalEnEff</h1>
<p class="subtitle">Energy &amp; Efficiency Calibration &mdash; Monte Carlo Fit</p>

<div class="card">
  <div class="kv"><div class="key">Version</div><div class="val">{_APP_VERSION}</div></div>
  <div class="kv"><div class="key">Purpose</div><div class="val">Energy and efficiency calibration of HPGe gamma-ray spectrometers using Ra-226 reference sources, with full Monte Carlo uncertainty propagation.</div></div>
  <div class="kv"><div class="key">Source</div><div class="val"><a href="{_GITHUB_URL}" target="_blank">{_GITHUB_URL}</a></div></div>
  <div class="kv"><div class="key">Author</div><div class="val">RIG (grainovski)</div></div>
</div>

<h2>Methods</h2>

<h3>Energy calibration</h3>
<div class="formula">Linear:    ch(E) = a + b&middot;E
Quadratic: ch(E) = a + b&middot;E + c&middot;E&sup2;</div>
<p>Weighted least-squares fit. Uncertainties reported as stat (from covariance
matrix) and Birge-scaled (stat &times; &radic;(&chi;&sup2;/ndf)).</p>

<h3>Efficiency calibration</h3>
<div class="formula">&epsilon;(E) = (a&middot;E + b/E) &middot; exp(c&middot;E + d/E)</div>
<p>Weighted non-linear least-squares fit followed by Monte Carlo propagation
(10&thinsp;000 trials). Each trial draws parameters from a multivariate normal
distribution defined by the covariance matrix and evaluates &epsilon; at the query
energy to produce MC mean, 1&sigma; standard deviation, and best-fit value.</p>

<h3>Birge ratio</h3>
<div class="formula">B = &radic;(&chi;&sup2; / ndf)</div>
<p>Scale factor applied to covariance-based uncertainties when the data scatter
exceeds the stated measurement errors. B &asymp; 1 indicates a consistent fit;
B &gt; 1 indicates under-estimated input uncertainties.</p>

<h2>Dependencies</h2>
<table>
  <tr><th>Package</th><th>Used for</th></tr>
  <tr><td>NumPy, SciPy</td><td>Numerical fitting and Monte Carlo sampling</td></tr>
  <tr><td>Matplotlib</td><td>Interactive plots and figure export</td></tr>
  <tr><td>Tkinter</td><td>GUI framework (bundled with Python)</td></tr>
</table>
</body>
</html>
"""
