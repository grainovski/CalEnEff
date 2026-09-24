"""Help content for CalEnEff — three HTML pages opened in the system browser."""
import os
import pathlib
import sys
import tempfile
import time
import webbrowser

# ── version (stamped by build.ps1 at packaging time) ────────────────────────
try:
    import build_info
    _VERSION    = build_info.VERSION
    _BUILD_DATE = build_info.BUILD_DATE
except (ImportError, AttributeError, SyntaxError):
    _VERSION    = "dev"
    _BUILD_DATE = "development build"

_GITHUB_URL = "https://github.com/grainovski/CalEnEff"

# ── shared CSS (light theme, matches SpectraTools) ───────────────────────────
_PAGE_CSS = """
  body {
    font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    max-width: 900px;
    margin: 2rem auto;
    padding: 0 1.5rem 3rem;
    line-height: 1.6;
    color: #1a1a1a;
    background: #ffffff;
  }
  h1 { font-size: 1.7rem; border-bottom: 2px solid #0066cc; padding-bottom: .4rem;
       margin-bottom: 1.4rem; }
  h2 { font-size: 1.2rem; background: #f0f4ff; border-left: 4px solid #0066cc;
       padding: .4rem .8rem; margin: 2rem 0 .8rem; }
  h3 { font-size: 1rem; color: #003388; margin: 1.2rem 0 .4rem; }
  p  { margin: .5rem 0 .9rem; }
  ul, ol { margin: .4rem 0 .9rem; padding-left: 1.6rem; }
  li { margin-bottom: .3rem; }
  code, kbd {
    font-family: "Consolas", "Cascadia Code", "Courier New", monospace;
    font-size: .9em;
  }
  code { background: #f3f4f6; border-radius: 3px; padding: .1em .35em; }
  kbd  { background: #e8e8e8; border: 1px solid #bbb; border-radius: 3px;
         padding: .05em .4em; }
  pre  { background: #f3f4f6; border: 1px solid #d0d7de; border-radius: 5px;
         padding: .9rem 1.1rem; overflow-x: auto; font-size: .88em;
         line-height: 1.5; white-space: pre; }
  table { border-collapse: collapse; width: 100%; margin: .6rem 0 1.2rem; }
  th    { background: #0066cc; color: #fff; padding: .5rem .8rem; text-align: left; }
  td    { padding: .45rem .8rem; border-bottom: 1px solid #d0d7de; }
  tr:nth-child(even) td { background: #f8f9fb; }
  .note { background: #fffbe6; border-left: 4px solid #e6ac00;
          padding: .5rem .9rem; border-radius: 0 4px 4px 0; margin: .8rem 0; }
  .formula { background: #f0f8ff; border: 1px solid #b0d0ff; border-radius: 5px;
             padding: .7rem 1.1rem; font-family: "Consolas","Courier New",monospace;
             font-size: .9em; margin: .6rem 0 1rem; white-space: pre; }
  a { color: #0055bb; }
"""


def _page(title, body_html):
    return (
        "<!doctype html>\n"
        "<html lang='en'>\n"
        "<head>\n"
        "  <meta charset='utf-8'>\n"
        "  <meta name='viewport' content='width=device-width,initial-scale=1'>\n"
        f"  <title>CalEnEff — {title}</title>\n"
        "  <style>" + _PAGE_CSS + "</style>\n"
        "</head>\n"
        "<body>\n"
        + body_html +
        "\n</body>\n</html>\n"
    )


# ── browser helper ───────────────────────────────────────────────────────────

_TMP_PREFIX  = 'caleneff_help_'
_TMP_MAX_AGE = 24 * 3600        # seconds


def _sweep_old_help_files():
    """Delete help pages left behind by earlier runs.

    The temp file cannot be deleted on close: webbrowser.open() hands the path
    to the browser and returns immediately, so deleting it here would race the
    browser's read.  Each run therefore clears the *previous* runs' files
    instead of letting them accumulate in the temp directory forever.
    """
    try:
        tmp    = tempfile.gettempdir()
        cutoff = time.time() - _TMP_MAX_AGE
        for name in os.listdir(tmp):
            if not (name.startswith(_TMP_PREFIX) and name.endswith('.html')):
                continue
            path = os.path.join(tmp, name)
            try:
                if os.path.getmtime(path) < cutoff:
                    os.remove(path)
            except OSError:
                pass            # still open, or already removed elsewhere
    except OSError:
        pass


def open_help_page(html):
    """Write html to a temp file and open it in the system browser."""
    _sweep_old_help_files()
    try:
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.html', prefix=_TMP_PREFIX,
            encoding='utf-8', delete=False,
        ) as f:
            f.write(html)
            path = f.name
    except OSError:
        return False
    # Path.as_uri() percent-encodes spaces and non-ASCII characters; the old
    # 'file:///' + backslash-swap did not, so a user profile containing a
    # space or an umlaut produced a URL the browser could not open.
    webbrowser.open(pathlib.Path(path).as_uri())
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# HowTo
# ═══════════════════════════════════════════════════════════════════════════════

def build_howto_html():
    body = """
<h1>CalEnEff — HowTo</h1>
<p>Step-by-step guide for performing energy and efficiency calibrations
   with a Ra-226 reference source.</p>

<h2>1 — Prepare your data file</h2>
<p>CalEnEff reads plain-text files with seven whitespace-separated columns:</p>
<pre>ch    Δch    N    ΔN    E[keV]    I[%]    ΔI[%]</pre>
<ul>
  <li><code>ch</code> — centroid channel of the photopeak</li>
  <li><code>Δch</code> — uncertainty on the centroid (e.g. from Gaussian fit FWHM / 2.35)</li>
  <li><code>N</code> — net peak area (counts)</li>
  <li><code>ΔN</code> — uncertainty on net area</li>
  <li><code>E</code> — known gamma-ray energy in keV</li>
  <li><code>I</code> — emission probability in % (from NNDC or BIPM)</li>
  <li><code>ΔI</code> — uncertainty on I in %</li>
</ul>
<p>Lines starting with <code>#</code> are treated as comments. A blank line or
a line with fewer than 7 numbers is skipped. Two demo files
(<code>demo1.txt</code>, <code>demo2.txt</code>) ship with the installer.</p>

<h2>2 — Load the file</h2>
<p>Click <strong>Browse</strong> (or drag-and-drop) to open a data file.
The table on the left is populated immediately. The first row of valid
data is highlighted; all rows are selected by default.</p>
<p>To exclude a line from the fit, uncheck its checkbox in the leftmost column.
Excluded rows are grayed out but remain visible for reference.</p>

<h2>3 — Energy calibration</h2>
<ol>
  <li>Select the <strong>Energy Calibration</strong> tab.</li>
  <li>Choose <em>Linear</em> or <em>Quadratic</em> from the model selector.</li>
  <li>Click <strong>Fit</strong>. The fitted curve and residuals are drawn
      immediately.</li>
  <li>Check the residual plot and the Birge ratio <em>B</em>.
      A value near 1 indicates a well-fitting model with realistic uncertainties.
      See the Knowledge Database for interpretation details.</li>
  <li>The result table shows the coefficients, their statistical
      (1-σ) uncertainties, and — when B > 1 — Birge-scaled uncertainties.</li>
</ol>
<div class='note'><strong>Tip:</strong> Start with Linear. Switch to Quadratic
only if the residuals show a clear parabolic trend or B ≫ 1.</div>

<h2>4 — Efficiency calibration</h2>
<ol>
  <li>Select the <strong>Efficiency Calibration</strong> tab.</li>
  <li>The same data file is used; measured efficiency ε<sub>i</sub> is
      computed internally from the N and I columns.</li>
  <li>Click <strong>Fit</strong>. The four-parameter model
      ε(E) = (a·E + b/E)·exp(c·E + d/E) is fitted by weighted
      non-linear least squares.</li>
  <li>Monte Carlo uncertainty propagation (10 000 trials) produces
      the parameter covariance, from which the efficiency and its
      uncertainty at any energy can be evaluated.</li>
</ol>

<h2>5 — Query a specific energy</h2>
<p>After a successful fit, type an energy in the <strong>Query</strong> field
and press <kbd>Enter</kbd> (or click <strong>Evaluate</strong>).
CalEnEff returns:</p>
<ul>
  <li>Fitted efficiency ε̂ and its ±1-σ MC uncertainty.</li>
  <li>For the energy calibration: the channel number corresponding to
      that energy, with propagated uncertainty.</li>
</ul>

<h2>6 — Export results</h2>
<p>Click <strong>Save Results</strong> to write a structured text report
to the same directory as the input file. The file contains the fit
coefficients, covariance matrix, Birge ratio, and all queried values.</p>

<h2>Keyboard shortcuts</h2>
<table>
  <tr><th>Key</th><th>Action</th></tr>
  <tr><td><kbd>F1</kbd></td><td>Open this HowTo page</td></tr>
  <tr><td><kbd>Enter</kbd></td><td>Evaluate query field</td></tr>
  <tr><td><kbd>Ctrl+O</kbd></td><td>Open file dialog</td></tr>
  <tr><td><kbd>Ctrl+S</kbd></td><td>Save results</td></tr>
</table>
"""
    return _page("HowTo", body)


# ═══════════════════════════════════════════════════════════════════════════════
# Knowledge Database
# ═══════════════════════════════════════════════════════════════════════════════

def build_knowledge_database_html():  # noqa: C901
    body = """
<h1>CalEnEff — Knowledge Database</h1>
<p>Mathematical and physical background for the calibration methods
implemented in CalEnEff, reference data for common calibration sources,
and links to nuclear data databases.</p>

<!-- ── Efficiency curve illustration ─────────────────────────── -->
<h2>Efficiency curve models — illustration</h2>
<p>The canvas below shows the typical shape of a relative detection
efficiency curve for a large-volume HPGe detector.
Both the <strong>KRF model</strong> (solid blue, 4 parameters, used by CalEnEff) and
the <strong>Radware/EFFIT model</strong> (dashed orange, 7 parameters) capture the
same physical behaviour: strong suppression at very low energies due to
window and dead-layer attenuation, a broad maximum around 200–400 keV where
the photoelectric cross-section and detector volume are both favourable,
and a smooth monotonic decline at higher energies where Compton scattering
increasingly dominates.
Curves are <em>normalized to unity at the peak</em>; shaded bands indicate
the energy ranges covered by common calibration sources.</p>
<canvas id="effCv" width="680" height="300"
  style="border:1px solid #d0d7de;border-radius:5px;display:block;margin:.8rem auto;max-width:100%;"></canvas>
<p style="font-size:.84em;color:#555;text-align:center;margin-top:.2rem;">
Illustrative curves for a typical 70% HPGe detector (normalized peak = 1).
Actual shape depends on detector geometry, cryostat window, and source distance.
Shaded bands: <span style="color:#b08000">&#9632;</span> Ba-133 (53–384 keV),
<span style="color:#227744">&#9632;</span> Eu-152 (122–1408 keV),
<span style="color:#3355cc">&#9632;</span> Ra-226 (46–2448 keV).
</p>
<script>
(function(){
  var cv=document.getElementById('effCv');
  if(!cv)return;
  var ctx=cv.getContext('2d'),W=cv.width,H=cv.height;
  var pl=54,pr=18,pt=18,pb=44;
  var pw=W-pl-pr, ph=H-pt-pb;
  var Emin=46,Emax=3000;
  function xm(E){return pl+pw*Math.log(E/Emin)/Math.log(Emax/Emin);}
  function ym(e){return pt+ph*(1-e/1.08);}
  // Source bands [Elo,Ehi,color]
  var bands=[[46,2448,'rgba(80,110,255,0.10)'],[122,1408,'rgba(30,180,90,0.13)'],[53,384,'rgba(220,190,0,0.20)']];
  bands.forEach(function(b){
    ctx.fillStyle=b[2];
    ctx.fillRect(xm(Math.max(b[0],Emin)),pt,xm(Math.min(b[1],Emax))-xm(Math.max(b[0],Emin)),ph);
  });
  // Light grid
  ctx.strokeStyle='#e0e0e0';ctx.lineWidth=1;
  [0,0.25,0.5,0.75,1.0].forEach(function(y){
    ctx.beginPath();ctx.moveTo(pl,ym(y));ctx.lineTo(pl+pw,ym(y));ctx.stroke();
  });
  [100,200,500,1000,2000].forEach(function(E){
    ctx.beginPath();ctx.moveTo(xm(E),pt);ctx.lineTo(xm(E),pt+ph);ctx.stroke();
  });
  // Curve data [E,relEff] — representative HPGe shape
  var krf=[[46,.22],[60,.31],[80,.52],[100,.70],[150,.91],[200,1.00],[300,.97],[400,.91],[500,.83],[700,.68],[1000,.52],[1500,.37],[2000,.28],[2500,.21],[3000,.16]];
  var rw= [[46,.21],[60,.30],[80,.50],[100,.69],[150,.90],[200,1.00],[300,.96],[400,.89],[500,.81],[700,.65],[1000,.50],[1500,.35],[2000,.26],[2500,.20],[3000,.15]];
  function drawCurve(pts,col,dash){
    ctx.beginPath();ctx.strokeStyle=col;ctx.lineWidth=2.5;
    ctx.setLineDash(dash?[7,4]:[]);
    pts.forEach(function(p,i){i?ctx.lineTo(xm(p[0]),ym(p[1])):ctx.moveTo(xm(p[0]),ym(p[1]));});
    ctx.stroke();ctx.setLineDash([]);
  }
  drawCurve(krf,'#0055cc',false);
  drawCurve(rw,'#cc5500',true);
  // Axes
  ctx.strokeStyle='#444';ctx.lineWidth=1.5;ctx.setLineDash([]);
  ctx.beginPath();ctx.moveTo(pl,pt);ctx.lineTo(pl,pt+ph);ctx.lineTo(pl+pw,pt+ph);ctx.stroke();
  // X ticks + labels
  ctx.fillStyle='#333';ctx.font='11px sans-serif';ctx.textAlign='center';
  [[100,'100'],[200,'200'],[500,'500'],[1000,'1000'],[2000,'2000']].forEach(function(t){
    ctx.fillText(t[1],xm(t[0]),pt+ph+15);
    ctx.beginPath();ctx.moveTo(xm(t[0]),pt+ph);ctx.lineTo(xm(t[0]),pt+ph+5);ctx.stroke();
  });
  // Y ticks + labels
  ctx.textAlign='right';
  [0,.25,.5,.75,1.0].forEach(function(y){
    ctx.fillText(y.toFixed(2),pl-6,ym(y)+4);
    ctx.beginPath();ctx.moveTo(pl-4,ym(y));ctx.lineTo(pl,ym(y));ctx.stroke();
  });
  // Axis labels
  ctx.textAlign='center';ctx.font='12px sans-serif';
  ctx.fillText('Energy (keV)',pl+pw/2,H-5);
  ctx.save();ctx.translate(12,pt+ph/2);ctx.rotate(-Math.PI/2);
  ctx.fillText('Relative efficiency',0,0);ctx.restore();
  // Legend box
  var lx=pl+pw-170,ly=pt+16;
  ctx.fillStyle='rgba(255,255,255,.88)';ctx.fillRect(lx-6,ly-14,168,52);
  ctx.strokeStyle='#ccc';ctx.lineWidth=1;ctx.strokeRect(lx-6,ly-14,168,52);
  ctx.strokeStyle='#0055cc';ctx.lineWidth=2.5;ctx.setLineDash([]);
  ctx.beginPath();ctx.moveTo(lx,ly);ctx.lineTo(lx+26,ly);ctx.stroke();
  ctx.fillStyle='#222';ctx.textAlign='left';ctx.font='11px sans-serif';
  ctx.fillText('KRF model (CalEnEff)',lx+30,ly+4);
  ctx.strokeStyle='#cc5500';ctx.setLineDash([7,4]);
  ctx.beginPath();ctx.moveTo(lx,ly+20);ctx.lineTo(lx+26,ly+20);ctx.stroke();
  ctx.setLineDash([]);ctx.fillText('Radware / EFFIT',lx+30,ly+24);
  // Band labels
  ctx.font='10px sans-serif';ctx.fillStyle='#555';ctx.textAlign='left';
  ctx.fillText('Ra-226',xm(50),pt+14);
  ctx.fillText('Eu-152',xm(130),pt+27);
  ctx.fillText('Ba-133',xm(57),pt+40);
})();
</script>

<!-- ── Data file ─────────────────────────────────────────────── -->
<h2>Data file format</h2>
<p>Each row represents one resolved photopeak:</p>
<pre>ch    Δch    N    ΔN    E[keV]    I[%]    ΔI[%]</pre>
<table>
  <tr><th>Column</th><th>Symbol</th><th>Description</th></tr>
  <tr><td><code>ch</code></td><td>c</td>
      <td>Peak centroid in ADC channels (from spectrum analysis)</td></tr>
  <tr><td><code>Δch</code></td><td>σ<sub>c</sub></td>
      <td>Uncertainty on c; use FWHM / 2.35 if from a Gaussian fit</td></tr>
  <tr><td><code>N</code></td><td>N</td>
      <td>Net peak area (background-subtracted counts)</td></tr>
  <tr><td><code>ΔN</code></td><td>σ<sub>N</sub></td>
      <td>Uncertainty on N (Poisson: √N is a lower bound for large counts)</td></tr>
  <tr><td><code>E</code></td><td>E</td>
      <td>True gamma-ray energy in keV (from nuclear data tables)</td></tr>
  <tr><td><code>I</code></td><td>I</td>
      <td>Emission probability in % per disintegration of the parent</td></tr>
  <tr><td><code>ΔI</code></td><td>σ<sub>I</sub></td>
      <td>Absolute uncertainty on I in % (same units as I)</td></tr>
</table>
<p>Lines beginning with <code>#</code> and blank lines are ignored.
All numeric values must be positive; CalEnEff skips rows that fail this
check and reports the skipped count in the status bar.</p>

<!-- ── Energy calibration ────────────────────────────────────── -->
<h2>Energy calibration</h2>
<h3>Models</h3>
<p>CalEnEff supports two polynomial models relating ADC channel to energy:</p>
<div class='formula'>Linear    :  c(E) = a + b·E

Quadratic :  c(E) = a + b·E + d·E²</div>
<p>where <em>a</em> (offset), <em>b</em> (gain), and <em>d</em> (curvature)
are the fit parameters. The linear model is adequate for most modern
ADC/MCA systems; the quadratic term corrects for detector non-linearity.</p>

<h3>Weighted least-squares fitting</h3>
<p>The fit minimises the weighted chi-squared:</p>
<div class='formula'>χ² = Σᵢ  [ cᵢ − c(Eᵢ) ]²  /  σᵢ²

where   σᵢ = σ(cᵢ)    (centroid uncertainty; nuclear energy uncertainty
                        is negligible for standard calibration sources)</div>
<p>The covariance matrix of the parameters:</p>
<div class='formula'>Cov(θ) = (AᵀWA)⁻¹     W = diag(1/σᵢ²)</div>

<h3>Reported uncertainties</h3>
<ul>
  <li><strong>Statistical (1-σ)</strong> — √diag(Cov(θ)). Valid when the
      model is correct and the input uncertainties are realistic.</li>
  <li><strong>Birge-scaled</strong> — statistical uncertainties × B.
      Applied automatically when B > 1.</li>
</ul>

<!-- ── Birge ratio ────────────────────────────────────────────── -->
<h2>Birge ratio</h2>
<div class='formula'>B = √( χ²/ndf )     ndf = n − p</div>
<table>
  <tr><th>B value</th><th>Meaning</th></tr>
  <tr><td>B ≈ 1</td>
      <td>Model fits well; input uncertainties are realistic</td></tr>
  <tr><td>B &gt; 1</td>
      <td>Residuals exceed expectation: model inadequate or σᵢ underestimated.
          CalEnEff inflates all reported uncertainties by B.</td></tr>
  <tr><td>B &lt; 1</td>
      <td>σᵢ overestimated or very few points. Statistical uncertainties
          are used as-is.</td></tr>
</table>
<div class='note'><strong>Rule of thumb:</strong> B > 2 is a warning sign.
For energy calibration, try the Quadratic model or review centroid
uncertainties. For efficiency, review the peak-area uncertainties and
check for outliers in the residual plot.</div>

<!-- ── Efficiency calibration ─────────────────────────────────── -->
<h2>Efficiency calibration</h2>

<h3>CalEnEff model (4-parameter)</h3>
<p>CalEnEff fits the semi-empirical curve:</p>
<div class='formula'>ε(E) = (a·E + b/E) · exp(c·E + d/E)</div>
<p>The <code>b/E</code> and <code>d/E</code> terms make efficiency rise at low
energies (increasing photoelectric cross-section below ~100 keV);
<code>a·E</code> and <code>c·E</code> produce the decline at high energies
(decreasing detection probability). Four parameters are enough to describe
a typical HPGe or NaI curve across the Ra-226 energy range.</p>

<h3>Radware efficiency model (7-parameter)</h3>
<p>The widely used Radware/EFFIT function (D.C. Radford, ORNL) joins two
quadratic-in-log polynomials with a smooth blending exponent G:</p>
<div class='formula'>ln ε_low (E) = A + B·ln(E/100)  + C·[ln(E/100) ]²
ln ε_high(E) = D + E·ln(E/1000) + F·[ln(E/1000)]²

ε(E) = exp{ [ (ln ε_low)^(−G) + (ln ε_high)^(−G) ]^(−1/G) }</div>
<p>Reference energies: <strong>E₁ = 100 keV</strong>, <strong>E₂ = 1 000 keV</strong>.
C is often fixed to zero in practice, giving six free parameters.
G is typically negative (e.g. G = −3 to −5), producing a smooth join
between the low- and high-energy branches.
The Radware model requires more calibration points than the 4-parameter
CalEnEff model and is preferred when the full energy range of a
high-resolution HPGe detector must be covered.
See: <a href="https://radware.phy.ornl.gov/gf3/">radware.phy.ornl.gov/gf3/</a></p>

<h3>Measured efficiency</h3>
<div class='formula'>εᵢ = Nᵢ / ( A · T · Iᵢ / 100 )

  Nᵢ  = net peak area [counts]
  A   = source activity at measurement time [Bq]
  T   = live time [s]
  Iᵢ  = emission probability [%]</div>
<p>Combined relative uncertainty (in quadrature):</p>
<div class='formula'>( σ_ε / ε )² = ( σ_N / N )² + ( σ_I / I )²</div>
<p>Activity uncertainty σ_A and live-time uncertainty are common to all
points and shift the entire curve by a constant scale factor; they do
not affect the fitted shape or the relative uncertainties.</p>

<h3>Non-linear fitting</h3>
<p>CalEnEff calls <code>scipy.optimize.curve_fit</code>
(Levenberg–Marquardt) with weights 1/σ²(εᵢ).
The returned covariance matrix <strong>C</strong> is used directly for
Monte Carlo propagation.</p>

<!-- ── Monte Carlo propagation ────────────────────────────────── -->
<h2>Monte Carlo uncertainty propagation</h2>
<p>First-order (gradient) error propagation can underestimate the true
uncertainty of a strongly non-linear function. CalEnEff instead draws
10 000 parameter vectors from the multivariate normal distribution:</p>
<div class='formula'>θ⁽ᵏ⁾ ~ 𝒩( θ̂, C )    k = 1 … 10 000</div>
<p>and evaluates ε(E*; θ⁽ᵏ⁾) for each draw, yielding an empirical
distribution at the query energy E*.</p>

<h3>What the output numbers mean</h3>
<table>
  <tr><th>Output</th><th>Definition</th><th>When to use it</th></tr>
  <tr><td><strong>Best-fit</strong> ε(E*; θ̂)</td>
      <td>Direct evaluation of the fitted curve at E*</td>
      <td>Point estimate (maximum-likelihood / least-squares result)</td></tr>
  <tr><td><strong>MC mean</strong></td>
      <td>Average of the 10 000 sampled values</td>
      <td>Bias-corrected estimate; preferred when the curve is
          strongly non-linear (Jensen's inequality shifts the mean)</td></tr>
  <tr><td><strong>MC σ</strong></td>
      <td>Standard deviation of the 10 000 sampled values</td>
      <td><strong>Recommended uncertainty to report.</strong>
          Correctly captures parameter correlations and non-linearity
          that a simple gradient propagation would miss.</td></tr>
</table>
<div class='note'>
<strong>Practical guidance:</strong>
Report the MC mean ± MC σ (1-σ, 68% coverage) as your efficiency
value with uncertainty.
If the MC distribution is visibly asymmetric (check the residual panel),
report the 16th and 84th percentiles of the sample as the ±1-σ interval
instead of the standard deviation.
For publication, also quote the Birge-scaled parameter uncertainties
from the fit result table so reviewers can judge the goodness of fit.
</div>
<p>Reference: Tellinghuisen, J., "Statistical Error Propagation,"
<em>J. Phys. Chem. A</em> 105 (2001) 3917–3921.</p>

<!-- ── Chi-squared and ndf ────────────────────────────────────── -->
<h2>Chi-squared and degrees of freedom</h2>
<table>
  <tr><th>Calibration</th><th>Free parameters p</th><th>ndf = n − p</th></tr>
  <tr><td>Energy — Linear</td><td>2 (a, b)</td><td>n − 2</td></tr>
  <tr><td>Energy — Quadratic</td><td>3 (a, b, d)</td><td>n − 3</td></tr>
  <tr><td>Efficiency (CalEnEff)</td><td>4 (a, b, c, d)</td><td>n − 4</td></tr>
  <tr><td>Efficiency (Radware)</td><td>6–7 (A…F [+G])</td><td>n − 6 or n − 7</td></tr>
</table>

<!-- ── Reference sources ─────────────────────────────────────── -->
<h2>Reference calibration sources</h2>
<p>Emission probabilities I(%) are photons per 100 disintegrations of the
parent. Values from
<a href="https://www.lnhb.fr/nuclear-data/nuclear-data-table/">LNHB/BIPM-5</a>
and
<a href="https://www.nndc.bnl.gov/nudat3/">NNDC NuDat 3</a>
(see also
<a href="https://nds.iaea.org/xgamma_standards/">IAEA NDS xgamma standards</a>).
Always verify against the database version current at the time of
your measurement.</p>

<h3>²²⁶Ra — T½ = 1 600 y — secular equilibrium with daughters</h3>
<p>Covers 46 keV – 2 448 keV; ideal for a single-source full-range
calibration. In secular equilibrium the chain includes
<strong>²²²Rn → ²¹⁴Pb → ²¹⁴Bi</strong> as the dominant gamma emitters.
The 186 keV line of ²²⁶Ra overlaps ²³⁵U at 185.7 keV and should be
excluded when measuring uranium-containing samples.
Lines below ~100 keV are sensitive to source self-absorption and geometry.</p>
<table>
  <tr><th>Energy (keV)</th><th>Daughter</th><th>I (%)</th><th>Notes</th></tr>
  <tr><td>46.52</td>   <td>²¹⁰Pb</td><td>4.25</td>   <td>Self-absorption sensitive; requires thin source</td></tr>
  <tr><td>53.23</td>   <td>²¹⁴Pb</td><td>1.06</td>   <td>Weak; low-energy calibration only</td></tr>
  <tr><td>74.82</td>   <td>²¹⁴Pb</td><td>0.25</td>   <td>Very weak</td></tr>
  <tr><td>186.21</td>  <td>²²⁶Ra</td><td>3.64(4)</td><td>Overlaps ²³⁵U 185.7 keV — exclude for U samples</td></tr>
  <tr><td>241.99</td>  <td>²¹⁴Pb</td><td>7.43</td>   <td></td></tr>
  <tr><td>295.22</td>  <td>²¹⁴Pb</td><td>18.41</td>  <td></td></tr>
  <tr><td>351.93</td>  <td>²¹⁴Pb</td><td>35.60</td>  <td>Strongest ²¹⁴Pb line</td></tr>
  <tr><td>405.75</td>  <td>²¹⁴Pb</td><td>0.531</td>  <td>Very weak</td></tr>
  <tr><td>609.31</td>  <td>²¹⁴Bi</td><td>45.49</td>  <td>Strong, well-isolated; primary calibration line</td></tr>
  <tr><td>665.45</td>  <td>²¹⁴Bi</td><td>1.530</td>  <td></td></tr>
  <tr><td>768.36</td>  <td>²¹⁴Bi</td><td>4.894</td>  <td></td></tr>
  <tr><td>806.17</td>  <td>²¹⁴Bi</td><td>1.220</td>  <td></td></tr>
  <tr><td>934.06</td>  <td>²¹⁴Bi</td><td>3.107</td>  <td></td></tr>
  <tr><td>1120.29</td> <td>²¹⁴Bi</td><td>14.91</td>  <td></td></tr>
  <tr><td>1155.19</td> <td>²¹⁴Bi</td><td>1.638</td>  <td></td></tr>
  <tr><td>1238.11</td> <td>²¹⁴Bi</td><td>5.834</td>  <td></td></tr>
  <tr><td>1280.96</td> <td>²¹⁴Bi</td><td>1.434</td>  <td></td></tr>
  <tr><td>1377.67</td> <td>²¹⁴Bi</td><td>3.985</td>  <td></td></tr>
  <tr><td>1401.50</td> <td>²¹⁴Bi</td><td>1.320</td>  <td></td></tr>
  <tr><td>1407.98</td> <td>²¹⁴Bi</td><td>2.394</td>  <td></td></tr>
  <tr><td>1509.23</td> <td>²¹⁴Bi</td><td>2.130</td>  <td></td></tr>
  <tr><td>1661.28</td> <td>²¹⁴Bi</td><td>1.046</td>  <td></td></tr>
  <tr><td>1729.60</td> <td>²¹⁴Bi</td><td>2.933</td>  <td></td></tr>
  <tr><td>1764.49</td> <td>²¹⁴Bi</td><td>15.31</td>  <td>Second strongest ²¹⁴Bi line</td></tr>
  <tr><td>1847.42</td> <td>²¹⁴Bi</td><td>2.025</td>  <td></td></tr>
  <tr><td>2118.55</td> <td>²¹⁴Bi</td><td>1.147</td>  <td></td></tr>
  <tr><td>2204.21</td> <td>²¹⁴Bi</td><td>4.985</td>  <td></td></tr>
  <tr><td>2447.86</td> <td>²¹⁴Bi</td><td>1.548</td>  <td>Highest-energy usable line</td></tr>
</table>
<p>Source: <a href="https://www.lnhb.fr/nuclear-data/nuclear-data-table/">LNHB/BIPM-5</a>;
cross-checked with <a href="https://www.nndc.bnl.gov/nudat3/">NNDC NuDat 3</a>.</p>

<h3>¹⁵²Eu — T½ = 13.537 y</h3>
<p>Excellent single-source calibration standard covering 122–1 408 keV
with 22 lines spanning the full mid-energy range.
The three strongest lines (121.8, 344.3, 1408.0 keV) cover more than a
decade in energy and are nearly always usable simultaneously.
Weak lines (&lt;1%) are listed for completeness but are rarely used alone.</p>
<table>
  <tr><th>Energy (keV)</th><th>I (%)</th><th>Notes</th></tr>
  <tr><td>121.782</td><td>28.37(15)</td><td>Primary low-energy anchor</td></tr>
  <tr><td>244.697</td><td>7.53(4)</td> <td></td></tr>
  <tr><td>295.939</td><td>0.446(3)</td><td>Weak</td></tr>
  <tr><td>344.279</td><td>26.59(12)</td><td>Second strongest line</td></tr>
  <tr><td>367.789</td><td>0.860(5)</td><td>Weak</td></tr>
  <tr><td>411.116</td><td>2.238(10)</td><td></td></tr>
  <tr><td>443.961</td><td>3.125(14)</td><td></td></tr>
  <tr><td>488.682</td><td>0.412(4)</td><td>Weak</td></tr>
  <tr><td>563.984</td><td>0.102(1)</td><td>Very weak</td></tr>
  <tr><td>586.265</td><td>0.458(4)</td><td>Weak</td></tr>
  <tr><td>678.580</td><td>0.489(4)</td><td>Weak</td></tr>
  <tr><td>688.674</td><td>0.859(5)</td><td>Weak</td></tr>
  <tr><td>778.904</td><td>12.97(6)</td><td></td></tr>
  <tr><td>867.380</td><td>4.214(20)</td><td></td></tr>
  <tr><td>964.079</td><td>14.63(6)</td><td></td></tr>
  <tr><td>1005.279</td><td>0.648(5)</td><td>Weak</td></tr>
  <tr><td>1085.837</td><td>10.21(5)</td><td></td></tr>
  <tr><td>1089.737</td><td>1.731(9)</td><td>Partially resolved from 1085.8</td></tr>
  <tr><td>1112.069</td><td>13.54(6)</td><td></td></tr>
  <tr><td>1212.948</td><td>1.415(7)</td><td></td></tr>
  <tr><td>1299.142</td><td>1.626(8)</td><td></td></tr>
  <tr><td>1408.013</td><td>20.87(9)</td><td>Primary high-energy anchor</td></tr>
</table>
<p>Source: <a href="http://www.lnhb.fr/nuclides/Eu-152_tables.pdf">LNHB Eu-152 tables</a></p>

<h3>¹³³Ba — T½ = 10.551 y</h3>
<p>Covers 53–384 keV with 9 lines. The 356 keV line (I = 63.6%) is one of
the most intense single calibration lines available and is routinely used
as a low-energy anchor below ⁶⁰Co. The 80.998 keV line is useful for
efficiency near the K-edge region of many detector materials.</p>
<table>
  <tr><th>Energy (keV)</th><th>I (%)</th><th>Notes</th></tr>
  <tr><td>53.162</td><td>2.14(6)</td>  <td>Low-energy; self-absorption sensitive</td></tr>
  <tr><td>79.614</td><td>2.63(19)</td> <td>Cs K X-ray blend region</td></tr>
  <tr><td>80.998</td><td>33.31(30)</td><td>Strong; Cs K X-ray region</td></tr>
  <tr><td>160.612</td><td>0.638(6)</td><td>Weak</td></tr>
  <tr><td>223.116</td><td>0.453(4)</td><td>Weak</td></tr>
  <tr><td>276.404</td><td>7.16(5)</td> <td></td></tr>
  <tr><td>302.851</td><td>19.10(12)</td><td></td></tr>
  <tr><td>356.013</td><td>63.63(20)</td><td>Strongest line; primary calibration point</td></tr>
  <tr><td>383.849</td><td>9.12(6)</td> <td></td></tr>
</table>
<p>Source: <a href="http://www.lnhb.fr/nuclides/Ba-133_tables.pdf">LNHB Ba-133 tables</a></p>

<h3>⁵⁷Co — T½ = 271.79 d</h3>
<p>Low-energy standard; the 122 keV line is the primary anchor below
200 keV for HPGe detectors.</p>
<table>
  <tr><th>Energy (keV)</th><th>I (%)</th></tr>
  <tr><td>122.061</td><td>85.60(17)</td></tr>
  <tr><td>136.474</td><td>10.68(8)</td></tr>
</table>
<p>Source: <a href="http://www.lnhb.fr/nuclides/Co-57_tables.pdf">LNHB Co-57 tables</a></p>

<h3>⁶⁰Co — T½ = 5.2714 y</h3>
<p>High-energy standard; both lines are near 100% intensity and
well-separated — ideal for establishing the high-energy end of the
efficiency curve.</p>
<table>
  <tr><th>Energy (keV)</th><th>I (%)</th></tr>
  <tr><td>1173.228</td><td>99.85(3)</td></tr>
  <tr><td>1332.492</td><td>99.9826(6)</td></tr>
</table>
<p>Source: <a href="https://www.nndc.bnl.gov/nudat3/">NNDC NuDat 3</a></p>

<h3>¹³⁷Cs — T½ = 30.08 y</h3>
<p>Single strong line; universally used as an energy and efficiency check
point at 662 keV (mid-range for most detectors).</p>
<table>
  <tr><th>Energy (keV)</th><th>I (%)</th></tr>
  <tr><td>661.657</td><td>85.10(20)</td></tr>
</table>
<p>Source: <a href="https://www.nndc.bnl.gov/nudat3/">NNDC NuDat 3</a></p>

<h3>⁸⁸Y — T½ = 106.63 d</h3>
<p>High-energy points; the 1836 keV line extends calibrations well above
the ⁶⁰Co range.</p>
<table>
  <tr><th>Energy (keV)</th><th>I (%)</th></tr>
  <tr><td>898.042</td><td>93.7(3)</td></tr>
  <tr><td>1836.063</td><td>99.2(3)</td></tr>
</table>
<p>Source: <a href="http://www.lnhb.fr/nuclides/Y-88_tables.pdf">LNHB Y-88 tables</a></p>

<h3>⁵⁴Mn — T½ = 312.20 d</h3>
<p>Single near-100% line at 835 keV; useful as an independent verification
point between ⁶⁰Co and ¹³⁷Cs.</p>
<table>
  <tr><th>Energy (keV)</th><th>I (%)</th></tr>
  <tr><td>834.848</td><td>99.975(1)</td></tr>
</table>
<p>Source: <a href="https://www.nndc.bnl.gov/nudat3/">NNDC NuDat 3</a></p>

<h3>¹⁸²Ta — T½ = 114.74 d</h3>
<p>Tantalum-182 provides a dense set of lines across 32–1231 keV (19 lines),
making it particularly useful for filling gaps in the low-to-mid energy
range where Ra-226 daughters are less dense.
The 67.75 keV line (~42%) is one of the most intense low-energy calibration
lines available from a sealed source.
The high-energy doublet at 1121 and 1221 keV extends calibrations well
into the ⁶⁰Co region.</p>
<table>
  <tr><th>Energy (keV)</th><th>I (%)</th><th>Notes</th></tr>
  <tr><td>31.74</td>  <td>~0.18</td><td>Very weak; X-ray region</td></tr>
  <tr><td>65.72</td>  <td>~3.1</td> <td></td></tr>
  <tr><td>67.75</td>  <td>42.4</td> <td>Strongest low-energy line</td></tr>
  <tr><td>84.68</td>  <td>~2.3</td> <td></td></tr>
  <tr><td>100.11</td> <td>14.2</td> <td></td></tr>
  <tr><td>113.67</td> <td>~3.5</td> <td></td></tr>
  <tr><td>116.42</td> <td>~0.3</td> <td>Weak</td></tr>
  <tr><td>152.43</td> <td>7.0</td>  <td></td></tr>
  <tr><td>156.39</td> <td>~2.6</td> <td></td></tr>
  <tr><td>179.39</td> <td>~3.1</td> <td></td></tr>
  <tr><td>198.35</td> <td>~1.5</td> <td></td></tr>
  <tr><td>222.11</td> <td>~7.5</td> <td></td></tr>
  <tr><td>229.32</td> <td>~3.6</td> <td></td></tr>
  <tr><td>264.08</td> <td>~3.5</td> <td></td></tr>
  <tr><td>1100.44</td><td>~1.1</td> <td>Weak</td></tr>
  <tr><td>1121.29</td><td>35.24</td><td>Strong; high-energy anchor</td></tr>
  <tr><td>1189.05</td><td>16.5</td> <td></td></tr>
  <tr><td>1221.39</td><td>27.14</td><td></td></tr>
  <tr><td>1231.02</td><td>11.46</td><td></td></tr>
</table>
<div class='note'>Values marked "~" are approximate; verify against
<a href="https://www.nndc.bnl.gov/nudat3/">NNDC NuDat 3</a> for
publication-quality data. T½ makes Ta-182 suitable for measurements
spanning several weeks.</div>
<p>Source: <a href="https://www.nndc.bnl.gov/nudat3/">NNDC NuDat 3</a></p>

<h3>²⁴¹Am — T½ = 432.2 y</h3>
<p>Americium-241 is the standard for very low-energy (below 100 keV)
detector efficiency characterisation.
The 59.537 keV line (~36%) is the primary calibration point and is
uniquely valuable for efficiency calibration of thin-window HPGe and
silicon detectors below 100 keV.
The 26.345 keV line enables calibration into the X-ray region but is
strongly affected by source encapsulation and detector window attenuation.</p>
<table>
  <tr><th>Energy (keV)</th><th>I (%)</th><th>Notes</th></tr>
  <tr><td>26.345</td><td>2.27</td> <td>Np L X-ray region; geometry sensitive</td></tr>
  <tr><td>33.196</td><td>0.126</td><td>Very weak</td></tr>
  <tr><td>43.420</td><td>0.073</td><td>Very weak</td></tr>
  <tr><td>59.537</td><td>35.92</td><td>Primary calibration line</td></tr>
</table>
<p>Source: <a href="https://www.lnhb.fr/nuclides/Am-241_tables.pdf">LNHB Am-241 tables</a>;
<a href="https://www.nndc.bnl.gov/nudat3/">NNDC NuDat 3</a></p>

<h3>²⁴³Am — T½ = 7 370 y (+ ²³⁹Np daughter, T½ = 2.356 d)</h3>
<p>Americium-243 in secular equilibrium with its ²³⁹Np daughter provides
11 lines spanning 43–334 keV — an excellent complement to ¹³³Ba in the
low-to-mid energy range.
The 74.663 keV Am-243 line (~57%) and the 106.12 keV line (~25%) are the
primary calibration points; the Np-239 daughter contributes additional
lines at 86, 144, 209, 228, and 277 keV.
Note: fresh Am-243 sources require ~3 half-lives of Np-239 (~7 days) to
reach secular equilibrium.</p>
<table>
  <tr><th>Energy (keV)</th><th>Emitter</th><th>I (%)</th><th>Notes</th></tr>
  <tr><td>43.53</td> <td>²⁴³Am</td><td>5.9</td> <td></td></tr>
  <tr><td>61.47</td> <td>²³⁹Np</td><td>0.26</td><td>Weak</td></tr>
  <tr><td>74.663</td><td>²⁴³Am</td><td>57.0</td><td>Strongest Am-243 line</td></tr>
  <tr><td>86.496</td><td>²³⁹Np</td><td>3.14</td><td></td></tr>
  <tr><td>106.12</td><td>²⁴³Am+²³⁹Np</td><td>~25</td><td>Blend; use with care</td></tr>
  <tr><td>144.62</td><td>²³⁹Np</td><td>0.61</td><td>Weak</td></tr>
  <tr><td>174.01</td><td>²³⁹Np</td><td>0.26</td><td>Weak</td></tr>
  <tr><td>209.76</td><td>²³⁹Np</td><td>3.91</td><td></td></tr>
  <tr><td>228.18</td><td>²³⁹Np</td><td>11.5</td><td></td></tr>
  <tr><td>277.60</td><td>²³⁹Np</td><td>14.3</td><td></td></tr>
  <tr><td>334.29</td><td>²³⁹Np</td><td>0.023</td><td>Very weak</td></tr>
</table>
<p>Source: <a href="https://www.nndc.bnl.gov/nudat3/">NNDC NuDat 3</a>;
<a href="https://nds.iaea.org/xgamma_standards/">IAEA NDS xgamma standards</a></p>

<h3>⁵⁶Co — T½ = 77.27 d</h3>
<p>Cobalt-56 extends efficiency calibrations well beyond the ⁶⁰Co range
with 14 lines from 847 keV to 3 451 keV, including the highest-energy
gamma line routinely used for HPGe efficiency calibration (3 451 keV).
The 846.77 keV line (≈100%) is one of the most intense calibration lines
at any energy. Co-56 is produced by proton irradiation of iron and is
available as a sealed calibration source.</p>
<table>
  <tr><th>Energy (keV)</th><th>I (%)</th><th>Notes</th></tr>
  <tr><td>846.771</td> <td>99.93</td><td>Near-100%; primary anchor</td></tr>
  <tr><td>1037.843</td><td>13.99</td><td></td></tr>
  <tr><td>1175.099</td><td>2.23</td> <td></td></tr>
  <tr><td>1238.281</td><td>66.74</td><td>Second strongest line</td></tr>
  <tr><td>1360.196</td><td>4.28</td> <td></td></tr>
  <tr><td>1771.341</td><td>15.42</td><td></td></tr>
  <tr><td>2034.761</td><td>7.77</td> <td></td></tr>
  <tr><td>2598.445</td><td>16.97</td><td></td></tr>
  <tr><td>3009.577</td><td>0.95</td> <td>Weak</td></tr>
  <tr><td>3201.946</td><td>3.09</td> <td></td></tr>
  <tr><td>3253.419</td><td>7.55</td> <td></td></tr>
  <tr><td>3272.984</td><td>1.86</td> <td></td></tr>
  <tr><td>3369.986</td><td>0.62</td> <td>Weak</td></tr>
  <tr><td>3451.119</td><td>0.94</td> <td>Highest usable line</td></tr>
</table>
<p>Source: <a href="https://www.lnhb.fr/nuclides/Co-56_tables.pdf">LNHB Co-56 tables</a>;
<a href="https://www.nndc.bnl.gov/nudat3/">NNDC NuDat 3</a></p>

<h3>⁷⁵Se — T½ = 119.78 d</h3>
<p>Selenium-75 provides 9 lines from 66 to 401 keV, covering the
critical 100–300 keV region with high-intensity lines at 136 keV (58.8%)
and 264.7 keV (59.4%) — both nearly equal in intensity, which makes
Se-75 self-consistent for efficiency shape validation.
The 279.5 keV line (25.2%) is a useful cross-check point.</p>
<table>
  <tr><th>Energy (keV)</th><th>I (%)</th><th>Notes</th></tr>
  <tr><td>66.061</td><td>0.99</td> <td>Weak; low-energy region</td></tr>
  <tr><td>96.734</td><td>3.40</td> <td></td></tr>
  <tr><td>121.115</td><td>17.32</td><td></td></tr>
  <tr><td>136.000</td><td>58.76</td><td>Primary anchor</td></tr>
  <tr><td>198.606</td><td>1.35</td> <td>Weak</td></tr>
  <tr><td>264.658</td><td>59.35</td><td>Co-equal with 136 keV; useful self-check</td></tr>
  <tr><td>279.542</td><td>25.16</td><td></td></tr>
  <tr><td>303.924</td><td>1.31</td> <td>Weak</td></tr>
  <tr><td>400.657</td><td>11.53</td><td></td></tr>
</table>
<p>Source: <a href="https://www.nndc.bnl.gov/nudat3/">NNDC NuDat 3</a>;
<a href="https://nds.iaea.org/xgamma_standards/">IAEA NDS xgamma standards</a></p>

<!-- ── Nuclear data databases ─────────────────────────────────── -->
<h2>Nuclear data databases</h2>
<table>
  <tr><th>Database</th><th>URL</th><th>What it provides</th></tr>
  <tr><td><strong>NNDC NuDat 3</strong></td>
      <td><a href="https://www.nndc.bnl.gov/nudat3/">nndc.bnl.gov/nudat3</a></td>
      <td>Half-lives, gamma energies, emission probabilities from ENSDF;
          searchable by nuclide, energy, or decay mode</td></tr>
  <tr><td><strong>NNDC ENSDF</strong></td>
      <td><a href="https://www.nndc.bnl.gov/ensdf/">nndc.bnl.gov/ensdf</a></td>
      <td>Full evaluated nuclear structure and decay data files
          (authoritative US source)</td></tr>
  <tr><td><strong>LNHB / BIPM-5</strong></td>
      <td><a href="https://www.lnhb.fr/nuclear-data/nuclear-data-table/">lnhb.fr/nuclear-data</a></td>
      <td>DDEP-evaluated decay data for individual nuclides; highest-accuracy
          recommended values for metrology; individual PDF tables per nuclide</td></tr>
  <tr><td><strong>BIPM Monograph BIPM-5</strong></td>
      <td><a href="https://www.bipm.org/en/publications/monographie-ri-5">bipm.org/…/monographie-ri-5</a></td>
      <td>Peer-reviewed international recommended nuclear decay data;
          the primary reference for I(%) values used in activity measurements</td></tr>
  <tr><td><strong>IAEA NDS — γ standards</strong></td>
      <td><a href="https://nds.iaea.org/xgamma_standards/">nds.iaea.org/xgamma_standards</a></td>
      <td>Recommended gamma and X-ray emission probabilities specifically
          for calibration sources; consolidated from DDEP and ENSDF</td></tr>
  <tr><td><strong>IAEA NDS main</strong></td>
      <td><a href="https://nds.iaea.org/">nds.iaea.org</a></td>
      <td>Hosts ENDF, EXFOR, JEFF sub-libraries and gamma-spectroscopy
          reference spectra; also the IAEA nuclear level properties file</td></tr>
</table>
<div class='note'>For calibration and activity measurement, use
<strong>LNHB/BIPM-5</strong> as the primary source — it carries the
smallest evaluated uncertainties on I(%). Cross-check with IAEA NDS
xgamma_standards if no LNHB table exists for your nuclide.</div>
"""
    return _page("Knowledge Database", body)


# ═══════════════════════════════════════════════════════════════════════════════
# About
# ═══════════════════════════════════════════════════════════════════════════════

def build_about_html():
    body = f"""
<h1>About CalEnEff</h1>
<table>
  <tr><th>Field</th><th>Value</th></tr>
  <tr><td>Version</td><td>{_VERSION}</td></tr>
  <tr><td>Build date</td><td>{_BUILD_DATE}</td></tr>
  <tr><td>Author</td><td>Georgi Rainovski</td></tr>
  <tr><td>Copyright</td><td>Copyright © 2026 Georgi Rainovski</td></tr>
  <tr><td>Repository</td><td><a href="{_GITHUB_URL}">{_GITHUB_URL}</a></td></tr>
  <tr><td>Python</td><td>{sys.version}</td></tr>
  <tr><td>Platform</td><td>{sys.platform}</td></tr>
</table>

<p><em>This application is created using AI Claude Code.</em></p>

<h2>Description</h2>
<p>CalEnEff is a desktop tool for gamma-ray energy and efficiency calibration
using a Ra-226 reference source. It performs weighted polynomial fitting
for energy calibration and weighted non-linear fitting of a four-parameter
semi-empirical efficiency model, with Monte Carlo uncertainty propagation.</p>

<h2>Dependencies</h2>
<ul>
  <li>Python 3.x</li>
  <li>NumPy — array operations and linear algebra</li>
  <li>SciPy — non-linear curve fitting (<code>curve_fit</code>)</li>
  <li>Matplotlib — calibration and residual plots</li>
  <li>Tkinter — GUI framework (bundled with Python)</li>
</ul>

<h2>License</h2>
<p>MIT License — see <a href="{_GITHUB_URL}/blob/main/LICENSE">LICENSE</a>
on GitHub.</p>
"""
    return _page("About", body)
