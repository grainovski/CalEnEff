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
  /* Radicals: the overbar spans the whole radicand, so the square root of
     chi2/ndf cannot be misread as the root of chi2 divided by ndf. */
  .sqrt { white-space: nowrap; }
  .sqrt .rs  { font-family: "Cambria Math", "STIX Two Math", "Segoe UI Symbol",
               "Segoe UI", serif; font-size: 1.1em; margin-right: -.04em; }
  .sqrt .rad { display: inline-block; line-height: 1.05;
               border-top: .075em solid currentColor; padding: .06em .1em 0 .08em; }
  .nb  { white-space: nowrap; }
  .fig { margin: .8rem 0 1.2rem; }
  .fig svg { width: 100%; max-width: 680px; height: auto; display: block;
             background: #fbfcfe; border: 1px solid #d0d7de; border-radius: 5px; }
  figcaption { font-size: .88em; color: #555; margin: .35rem 0 0; }
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
<p>CalEnEff reads plain-text files with seven whitespace-separated columns,
one row per photopeak, and an optional eighth:</p>
<pre>ch    Δch    N    ΔN    E[keV]    I[%]    ΔI[%]    [ΔE keV]</pre>
<ul>
  <li><code>ch</code> — centroid channel of the photopeak</li>
  <li><code>Δch</code> — uncertainty on the centroid (from the peak fit; it is the energy fit's weight)</li>
  <li><code>N</code> — net peak area (counts)</li>
  <li><code>ΔN</code> — uncertainty on the net area (never below <span class="sqrt"><span class="rs">√</span><span class="rad">N</span></span>)</li>
  <li><code>E</code> — reference gamma-ray energy in keV</li>
  <li><code>I</code> — emission probability in %</li>
  <li><code>ΔI</code> — uncertainty on I in %</li>
  <li><code>ΔE</code> — <em>optional</em> uncertainty of the reference energy in keV.
      Without it the energies are treated as exact; with it the energy fit
      uses the effective variance σ² = Δch² + (dch/dE · ΔE)².</li>
</ul>
<p>Lines starting with <code>#</code> are comments and blank lines are
ignored. Every other line must have the same number of columns (7 or 8);
a file that does not is rejected with the offending row named, as are
non-positive Δch, E, N or I and negative uncertainties. At least 4 lines
are needed; the Radware model needs 5 (6 for a Birge ratio).
<code>226Ra_En_Area.txt</code> loads automatically at start-up; two more
samples, <code>demo1.txt</code> (Ba-133) and <code>demo2.txt</code>
(Eu-152), ship with the program.</p>

<h2>2 — Load the file</h2>
<p>Click <strong>📂 Read calibration data</strong>, or use
<strong>File ▾ → Open…</strong> (<kbd>Ctrl+O</kbd>). The status bar
reports the number of peaks and the energy and channel ranges. All lines in
the file are used; to leave a line out, comment it with <code>#</code>
and load the file again.</p>

<h2>3 — Calibrate</h2>
<p>Click <strong>⚙ Make calibration</strong>. This runs both calibrations
in one go, with a progress bar:</p>
<ul>
  <li><strong>Energy</strong>: linear and quadratic ch(E) by weighted least
      squares, plus 10 000 Monte Carlo refits.</li>
  <li><strong>Efficiency</strong>: ε = N/I fitted with KRF and Radware, each
      with 10 000 Monte Carlo refits (a few seconds to a minute).</li>
</ul>
<p>The left plot shows the energy calibration and its residuals, the right
plot ε(E) with both curves, their 1σ bands and the residuals. The status
bar reports how many Monte Carlo refits succeeded and any warning. Check
the residuals and the Birge ratio <em>B</em> = <span class="sqrt"><span class="rs">√</span><span class="rad">χ²/ndf</span></span>: <em>B</em> ≈ 1 means
the scatter matches the stated uncertainties; <em>B</em> ≫ 1 means it does
not, and the bands are widened by <em>B</em>.</p>
<p>The results file <code>&lt;data file&gt;_Res.txt</code> is written beside
the data file (or in Documents when that folder is read-only). It holds the
fitted parameters with their statistical and Birge-scaled uncertainties,
χ²/ndf, the Monte Carlo checks, the observed and fitted points, a
<strong>NOTES</strong> section with any caveats about the fits, and every
query you make afterwards.</p>

<h2>4 — Energy from a channel</h2>
<p>Enter <strong>ch₀</strong> and its uncertainty <strong>Δch₀</strong> and
press <kbd>Enter</kbd> or <strong>⟶ Calculate Energy</strong>. For the
linear and the quadratic calibration you get the <strong>best-fit</strong>
energy (the value to report), its <strong>1σ</strong> (your Δch₀ plus the
calibration's own uncertainty, the latter scaled by <em>B</em>), and the
Monte Carlo median as a check. A channel outside the calibrated range is
flagged as extrapolated.</p>

<h2>5 — Efficiency at an energy</h2>
<p>Enter <strong>E₀</strong> in keV and press <kbd>Enter</kbd> or
<strong>⟶ Get Efficiency</strong>. For each model you get the
<strong>best-fit</strong> efficiency, its asymmetric 1σ (the same rule the
band uses), and the Monte Carlo median with its bias check <em>z</em>. The
query log also records the KRF − Radware difference, a model uncertainty
that neither 1σ contains. <strong>a.u. → %</strong> switches the display to
percent of the KRF maximum inside the data. Energies outside the
calibrated range are flagged as extrapolated.</p>

<h2>6 — Save and export</h2>
<ul>
  <li><strong>File ▾ → Save</strong> (<kbd>Ctrl+S</kbd>) confirms or re-writes
      the results file; <strong>Save as…</strong> copies it under a new name
      and appends later queries there.</li>
  <li><strong>File ▾ → Export for SpectraTools…</strong> writes the energy
      coefficients and the relative efficiency per channel and per peak.</li>
  <li>Right-click a plot panel to save that panel (PNG, PDF, SVG, EPS, …);
      right-click the figure margin to save the whole figure.</li>
  <li><strong>✕ Clear</strong> removes the query markers from both plots.</li>
</ul>

<h2>Keyboard shortcuts</h2>
<table>
  <tr><th>Key</th><th>Action</th></tr>
  <tr><td><kbd>F1</kbd></td><td>Open this HowTo page</td></tr>
  <tr><td><kbd>Enter</kbd></td><td>In ch₀ / Δch₀: calculate energy; in E₀: get efficiency</td></tr>
  <tr><td><kbd>Ctrl+O</kbd></td><td>Open a data file</td></tr>
  <tr><td><kbd>Ctrl+S</kbd></td><td>Save the results file</td></tr>
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
<pre>ch    Δch    N    ΔN    E[keV]    I[%]    ΔI[%]    [ΔE keV]</pre>
<table>
  <tr><th>Column</th><th>Symbol</th><th>Description</th></tr>
  <tr><td><code>ch</code></td><td>c</td>
      <td>Peak centroid in ADC channels (from spectrum analysis)</td></tr>
  <tr><td><code>Δch</code></td><td>σ<sub>c</sub></td>
      <td>Uncertainty on c; use FWHM / 2.35 if from a Gaussian fit</td></tr>
  <tr><td><code>N</code></td><td>N</td>
      <td>Net peak area (background-subtracted counts)</td></tr>
  <tr><td><code>ΔN</code></td><td>σ<sub>N</sub></td>
      <td>Uncertainty on N (Poisson: <span class="sqrt"><span class="rs">√</span><span class="rad">N</span></span> is a lower bound for large counts)</td></tr>
  <tr><td><code>E</code></td><td>E</td>
      <td>True gamma-ray energy in keV (from nuclear data tables)</td></tr>
  <tr><td><code>I</code></td><td>I</td>
      <td>Emission probability in % per disintegration of the parent</td></tr>
  <tr><td><code>ΔI</code></td><td>σ<sub>I</sub></td>
      <td>Absolute uncertainty on I in % (same units as I)</td></tr>
  <tr><td><code>ΔE</code></td><td>σ<sub>E</sub></td>
      <td><em>Optional 8th column.</em> Uncertainty of the reference energy,
          keV. Used by effective variance in the energy fit,
          σ² = Δch² + (dch/dE · ΔE)²; without it energies are exact.</td></tr>
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
are the fit parameters. The linear model is usually adequate for identifying
peaks; the quadratic term corrects a smooth curvature. Neither can follow the
small-scale integral non-linearity of an ADC: if the residual plot shows a
wavy pattern rather than random scatter, the calibration is only as accurate
as its RMS residual (logged with every energy query), whatever the parameter
uncertainties say.</p>

<h3>Weighted least-squares fitting</h3>
<p>The fit minimises the weighted chi-squared:</p>
<div class='formula'>χ² = Σᵢ  [ cᵢ − c(Eᵢ) ]²  /  σᵢ²

where   σᵢ = σ(cᵢ)    (centroid uncertainty only; the reference
                        energies Eᵢ are treated as exact)</div>
<p>Treating Eᵢ as exact is valid only while σ(cᵢ) is well above b·σ(Eᵢ).
Tabulated energies carry 0.002–0.1 keV uncertainties, and for a strong peak
with a realistic centroid uncertainty the energy term can dominate — the
²¹⁴Pb 839.06 keV line, for example, is known only to ±0.09 keV. Prefer lines
with small energy uncertainties, and never quote a centroid uncertainty below
its statistical minimum <span class="nb">σ_peak/<span class="sqrt"><span class="rs">√</span><span class="rad">N</span></span></span>.</p>
<p>The covariance matrix of the parameters:</p>
<div class='formula'>Cov(θ) = (AᵀWA)⁻¹     W = diag(1/σᵢ²)</div>

<h3>Reported uncertainties</h3>
<ul>
  <li><strong>Statistical (1-σ)</strong> — <span class="sqrt"><span class="rs">√</span><span class="rad">diag(Cov(θ))</span></span>. Valid when the
      model is correct and the input uncertainties are realistic.</li>
  <li><strong>Birge-scaled</strong> — statistical uncertainties × B.
      Applied automatically when B > 1.</li>
  <li><strong>Query results</strong> — energy and efficiency queries carry the
      same Birge scaling as the plotted bands. For an energy query only the
      calibration's share is scaled; your own Δch₀ is not.</li>
</ul>

<!-- ── Birge ratio ────────────────────────────────────────────── -->
<h2>Birge ratio</h2>
<div class='formula'>B = <span class="sqrt"><span class="rs">√</span><span class="rad">χ²/ndf</span></span>     χ² = Σ ( (yᵢ − f(xᵢ; θ̂)) / σᵢ )²     ndf = n − p</div>
<p>The Birge ratio (R. T. Birge, <em>Phys. Rev.</em> 40 (1932) 207) compares
the scatter of the points about the fitted curve with the uncertainties you
stated for them. If the model is right and every σᵢ is a true 1σ, each
residual is on average σᵢ in size, χ² averages ndf, and B ≈ 1. B is
therefore a single number answering one question: <em>are the stated
uncertainties consistent with how far the points actually lie from the
curve?</em></p>

<h3>How close to 1 is "1"?</h3>
<p>Even with a perfect model and honest uncertainties, B fluctuates from one
measurement to the next. Its spread is about <span class="nb">1/<span class="sqrt"><span class="rs">√</span><span class="rad">2·ndf</span></span></span>:</p>
<table>
  <tr><th>ndf</th><th>typical B (68 %)</th><th>B still plausible by chance (95 %)</th></tr>
  <tr><td>5</td><td>0.7 – 1.3</td><td>up to ≈ 1.5</td></tr>
  <tr><td>10</td><td>0.8 – 1.2</td><td>up to ≈ 1.4</td></tr>
  <tr><td>20</td><td>0.85 – 1.15</td><td>up to ≈ 1.3</td></tr>
</table>
<p>So B = 1.2 on a 23-line calibration says nothing; B = 1.8 does. With very
few points (a 5-line Radware fit has ndf = 0) B is undefined or meaningless,
and CalEnEff says so in the results file.</p>

<h3>What a large B means</h3>
<table>
  <tr><th>B value</th><th>Meaning</th></tr>
  <tr><td>B ≈ 1</td>
      <td>The model describes the data and the stated uncertainties are
          realistic. The statistical uncertainties can be used as they
          are.</td></tr>
  <tr><td>B &gt; 1</td>
      <td>The points scatter more than their uncertainties allow. One or
          more of: (1) the σᵢ are <strong>too small</strong> — a peak area
          quoted better than <span class="sqrt"><span class="rs">√</span><span class="rad">N</span></span>, a centroid better than <span class="nb">σ_peak/<span class="sqrt"><span class="rs">√</span><span class="rad">N</span></span></span>, a
          reference energy treated as exact; (2) the <strong>model is
          inadequate</strong> — ADC non-linearity a polynomial cannot
          follow, an efficiency shape the function cannot take; (3) a
          <strong>systematic effect</strong> acts on some lines —
          true-coincidence summing, a wrong emission probability, an
          interfering peak; (4) a single <strong>outlier</strong>.</td></tr>
  <tr><td>B &lt; 1</td>
      <td>The points agree better than their uncertainties suggest: the σᵢ
          are conservative, or there are too few points for B to mean much.
          CalEnEff does <em>not</em> shrink anything in this case (see
          below).</td></tr>
</table>

<h3>How CalEnEff uses it</h3>
<p>When B &gt; 1, every reported uncertainty is multiplied by B: the
Birge-scaled parameter uncertainties in the results table, the plotted 1σ
bands and the query results. This is the standard "scale factor" practice
(the Particle Data Group's S factor): it amounts to saying that the true
uncertainties of the points were B times larger than stated, uniformly,
and re-deriving the result's uncertainty on that basis.</p>
<ul>
  <li><strong>Inflate only.</strong> B &lt; 1 is treated as 1. Shrinking the
      interval below what the stated uncertainties imply has no
      statistical justification — with few points a small B is often
      luck — so it would understate the uncertainty.</li>
  <li><strong>Each model has its own B</strong>: linear and quadratic energy
      fits, KRF and Radware efficiency fits are scaled independently.</li>
  <li><strong>Energy queries</strong> scale only the calibration's share of
      the uncertainty, σ² = σ_total² + (B² − 1)·σ_cal². The Δch₀ you type is
      your own measurement and is not inflated.</li>
  <li><strong>Efficiency queries and bands</strong> scale the Monte Carlo
      spread. This was checked against the alternative of re-running the
      Monte Carlo with every input uncertainty multiplied by B: the two
      agree within 1 % for KRF and within 3–8 % for Radware.</li>
</ul>

<h3>What Birge scaling cannot fix</h3>
<p>Scaling by B assumes the excess scatter is <strong>random and the same
everywhere</strong>. When it is systematic, B tells you that something is
wrong but the scaled uncertainty is in the wrong places: too large at lines
that fit well, too small at the lines that cause the problem. Look at the
residual plot:</p>
<ul>
  <li><strong>Residuals scattered randomly about zero</strong> — B is
      plausibly underestimated uncertainties; Birge scaling is appropriate.</li>
  <li><strong>Residuals following a smooth pattern</strong> (a wave, a
      trend at one end) — the model is inadequate. The real error at an
      energy is closer to the fit's RMS residual, which CalEnEff logs with
      every energy query.</li>
  <li><strong>A few lines far off, the rest fine</strong> — a systematic
      effect on those lines. For Ra-226 the usual cause is true-coincidence
      summing: lines fed through cascades sit above the curve at close
      geometry. Correct the effect, or remove the affected lines, rather
      than rely on B.</li>
</ul>
<p>CalEnEff adds a note to the results file when B &gt; 3, where systematic
scatter is the likely explanation.</p>

<h3>Examples from the bundled dataset</h3>
<ul>
  <li><strong>Energy, B₁ = 1.80.</strong> The reference energies are treated
      as exact by default. Giving them a realistic uncertainty in the
      optional 8th column (ΔE = 0.02 keV) brings B₁ to 1.18 — the "excess"
      was the energy uncertainty that had been left out.</li>
  <li><strong>Efficiency, B ≈ 5.</strong> The lines fed through two-step
      cascades sit 6–7 % above the curve: uncorrected coincidence summing,
      a systematic effect. The bands are widened ×5 as if it were random;
      for those lines in particular, the band is not a reliable
      uncertainty.</li>
</ul>
<div class='note'><strong>Rule of thumb:</strong> compare B with the table
above before acting on it. If it is clearly too large, check the input
uncertainties first — the commonest cause is an uncertainty that is
physically too small — then the residual plot for a pattern or outliers.
Quote B (or χ²/ndf) with your result so readers can judge the fit.</div>

<!-- ── Efficiency calibration ─────────────────────────────────── -->
<h2>Efficiency calibration</h2>

<h3>CalEnEff model (4-parameter)</h3>
<p>CalEnEff fits the semi-empirical curve:</p>
<div class='formula'>ε(E) = (a·E + b/E) · exp(c·E + d/E)</div>
<p>The <code>b/E</code> and <code>d/E</code> terms shape the low-energy turnover:
efficiency rises towards lower energy as the photoelectric cross-section
grows, then falls again below ~100–200 keV as absorption in the source,
cryostat window and dead layer takes over;
<code>a·E</code> and <code>c·E</code> produce the decline at high energies
(decreasing detection probability). Four parameters are enough to describe
a typical HPGe or NaI curve across the Ra-226 energy range.</p>

<h3>Radware efficiency model (EFFIT; 5 free parameters)</h3>
<p>The widely used Radware/EFFIT function (D.C. Radford, ORNL) joins two
quadratic-in-log polynomials with a smooth blending exponent G:</p>
<div class='formula'>ln ε_low (E) = A + B·ln(E/100)  + C·[ln(E/100) ]²
ln ε_high(E) = D + E·ln(E/1000) + F·[ln(E/1000)]²

ε(E) = exp{ [ (ln ε_low)^(−G) + (ln ε_high)^(−G) ]^(−1/G) }</div>
<p>Reference energies: <strong>E₁ = 100 keV</strong>, <strong>E₂ = 1 000 keV</strong>.
CalEnEff follows Radford's default procedure in <code>effit.c</code>:
C = 0 and G = 15 are fixed, leaving five free parameters (A, B, D, E, F).
G sets how sharply the two branches join. Neither branch is constrained
beyond the calibration lines: with no line below ~150 keV the low-energy
branch rests on a handful of points, and extrapolating it is meaningless.
The Radware model requires more calibration points than the 4-parameter
CalEnEff model and is preferred when the full energy range of a
high-resolution HPGe detector must be covered.
See: <a href="https://radware.phy.ornl.gov/gf3/">radware.phy.ornl.gov/gf3/</a></p>
<p><strong>Units.</strong> The combination acts on ln ε itself, so it is
not indifferent to the unit of ε: rescaling ε shifts both branches by the
same constant and changes how they join. CalEnEff's ε = N/I is in arbitrary
units (they depend on live time, activity and whether I is in % or a
fraction), so before fitting it rescales ε to a fixed convention —
geometric mean e<sup>9.5</sup> — and divides the scale back out
afterwards. The factor <em>k</em> is listed with the parameters. Without it,
data with ε of order 1 (ln ε crossing 0) were fitted badly: on the example
dataset scaled that way, χ² rose from 452 to 525 and ε(843 keV) moved 10 %.</p>

<h3>Measured efficiency</h3>
<p>CalEnEff fits the <em>relative</em> efficiency, in arbitrary units:</p>
<div class='formula'>εᵢ = Nᵢ / Iᵢ

  Nᵢ  = net peak area [counts]
  Iᵢ  = emission probability [%]  (any common scale will do, but every
        line must be on the same one, taken from one evaluation)</div>
<p>The absolute efficiency is Nᵢ / (A · T · Iᵢ/100), with A the source
activity and T the live time; both are common to every line and only
rescale the curve.</p>
<p>Combined relative uncertainty (in quadrature):</p>
<div class='formula'>( σ_ε / ε )² = ( σ_N / N )² + ( σ_I / I )²</div>
<p>Activity uncertainty σ_A and live-time uncertainty are common to all
points and shift the entire curve by a constant scale factor; they do
not affect the fitted shape or the relative uncertainties. σ_N must include
counting statistics — it can never be below <span class="sqrt"><span class="rs">√</span><span class="rad">N</span></span> — plus the background
subtraction.</p>

<h3>Non-linear fitting</h3>
<p>CalEnEff calls <code>scipy.optimize.curve_fit</code>
(Levenberg–Marquardt) with weights 1/σ²(εᵢ).
Its covariance matrix <strong>C</strong> gives the <em>stat</em> parameter
uncertainties in the results table.</p>

<!-- ── Monte Carlo propagation ────────────────────────────────── -->
<h2>Monte Carlo uncertainty propagation</h2>
<p>First-order (gradient) error propagation can underestimate the true
uncertainty of a strongly non-linear function. CalEnEff instead uses a
parametric bootstrap: 10 000 times it redraws every input from its stated
uncertainty and <em>refits</em> the model —</p>
<div class='formula'>Nᵢ⁽ᵏ⁾ ~ 𝒩( Nᵢ, σ_Nᵢ ),   Iᵢ⁽ᵏ⁾ ~ 𝒩( Iᵢ, σ_Iᵢ )   →   θ⁽ᵏ⁾ = fit( … )
k = 1 … 10 000      (energy calibration: cᵢ⁽ᵏ⁾ ~ 𝒩( cᵢ, σᵢ ))</div>
<p>— and evaluates ε(E*; θ⁽ᵏ⁾) for each refit, yielding an empirical
distribution at the query energy E*. Refitting captures the non-linearity
of the fit itself, which sampling θ from a linearised covariance would not.
The spread is then multiplied by the model's Birge ratio when B > 1.</p>
<p>A drawn N or I that comes out zero or negative is redrawn on its own,
which truncates that point's distribution at zero — the physical
constraint. (Earlier versions discarded the whole replicate, which with
50 % area uncertainties threw away 42 % of the replicates and biased the
rest.) Each refit starts from the model's best fit, so it stays in the same
χ² minimum as the plotted curve.</p>
<p><strong>What the Monte Carlo does not include.</strong> The emission
probabilities are drawn independently; correlations between them (a common
normalisation, or lines sharing a decay branch) are not in the input file
and are therefore ignored. A common normalisation error cancels in a
relative efficiency. Systematic effects — true-coincidence summing above
all — are not random scatter: when they inflate the Birge ratio, the band is
widened as if they were, and the results file says so in its NOTES.</p>
<p>Every refit starts from the model's own best fit. The start is the same
fixed point for every refit — not the previous refit's result — so the
samples stay independent, and each refit converges in the same χ² minimum
as the plotted curve. That matters for Radware, whose χ² surface has several
minima: in v4.8 and earlier each Radware refit started from a fresh
<code>parset()</code> seed, and on data whose lowest line lies well above
100 keV that seed lands in a different, worse minimum (102 χ² units worse on
the v4.8 example data), so the band described a different curve from the
one drawn. <code>parset()</code> is now only a fallback for refits whose
warm start is rejected.</p>

<h3>Definition: the percentiles p16, p50 and p84</h3>
<p>Every Monte Carlo refit gives one value of the efficiency at the query
energy E*. Call the N finite values ε₁, ε₂, …, ε<sub>N</sub> (N = 10 000
refits; non-finite values from runaway refits are dropped, and with fewer
than 10 left the result is reported as NaN).</p>
<p>The <strong>empirical cumulative distribution</strong> F̂(x) is the fraction
of those values that are ≤ x:</p>
<div class='formula'>F̂(x) = (number of ε<sub>k</sub> ≤ x) / N          rises from 0 to 1</div>
<p>The <strong>q-th percentile</strong> p<sub>q</sub> is the value at which
that fraction reaches q — the inverse of F̂:</p>
<div class='formula'>F̂(p<sub>q</sub>) = q         "a fraction q of the refits gave ε ≤ p<sub>q</sub>"</div>
<p>CalEnEff uses three of them. The labels are rounded; the probability
levels are exact:</p>
<table>
  <tr><th>Symbol</th><th>Probability level q</th><th>Meaning</th></tr>
  <tr><td><strong>p16</strong></td><td>0.1587 = Φ(−1)</td>
      <td>15.87 % of the refits lie below it</td></tr>
  <tr><td><strong>p50</strong></td><td>0.5000 = Φ(0)</td>
      <td>half lie below it: the <strong>median</strong></td></tr>
  <tr><td><strong>p84</strong></td><td>0.8413 = Φ(+1)</td>
      <td>84.13 % of the refits lie below it</td></tr>
</table>
<p>Φ is the cumulative distribution of the standard normal; why exactly these
three levels is explained in the section on percentiles below.</p>
<div class='note'><strong>p16, p50 and p84 are efficiencies, not
probabilities.</strong> They carry the units of ε (a.u. or %, whatever the
display shows). The probabilities are the levels q = 0.1587, 0.5 and 0.8413
that define them.</div>
<p><strong>How they are computed.</strong> The N values are sorted,
ε<sub>(1)</sub> ≤ ε<sub>(2)</sub> ≤ … ≤ ε<sub>(N)</sub>, and p<sub>q</sub> is
read at rank 1 + q·(N − 1), interpolating linearly between the two
neighbouring values when the rank is not a whole number (NumPy's default
percentile method). With N = 10 000 that is rank 1 587.84 for p16,
5 000.5 for p50 and 8 413.16 for p84.</p>
<figure class="fig"><svg viewBox="0 0 680 300" role="img" aria-label="Empirical cumulative distribution of the KRF Monte Carlo values at 843 keV with the 15.87, 50 and 84.13 percent levels" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI, Helvetica, Arial, sans-serif"><polyline points="87.3,248.0 156.3,247.5 170.3,247.1 182.2,246.6 191.2,246.1 195.4,245.7 202.0,245.2 206.5,244.8 210.6,244.3 215.9,243.8 218.5,243.4 220.2,242.9 223.5,242.5 225.6,242.0 227.5,241.5 230.0,241.1 232.5,240.6 235.1,240.2 236.6,239.7 238.3,239.2 240.1,238.8 241.3,238.3 242.4,237.9 244.1,237.4 245.2,236.9 246.4,236.5 247.3,236.0 248.7,235.6 250.0,235.1 251.0,234.6 252.1,234.2 253.2,233.7 254.1,233.3 254.9,232.8 255.7,232.3 257.1,231.9 258.0,231.4 258.9,231.0 259.7,230.5 260.5,230.0 261.3,229.6 262.3,229.1 263.0,228.7 263.9,228.2 265.2,227.7 266.2,227.3 267.2,226.8 267.7,226.4 268.5,225.9 269.3,225.4 270.1,225.0 271.1,224.5 271.9,224.1 272.6,223.6 273.5,223.1 274.2,222.7 275.1,222.2 275.8,221.8 276.6,221.3 277.2,220.8 278.0,220.4 278.8,219.9 279.8,219.5 280.5,219.0 281.1,218.5 281.9,218.1 282.4,217.6 283.0,217.2 283.7,216.7 284.0,216.2 284.5,215.8 285.1,215.3 285.7,214.9 286.3,214.4 287.2,213.9 287.9,213.5 288.6,213.0 289.2,212.6 289.8,212.1 290.5,211.6 291.0,211.2 291.7,210.7 292.6,210.3 293.1,209.8 293.6,209.3 294.0,208.9 294.6,208.4 294.9,208.0 295.3,207.5 296.0,207.0 296.6,206.6 297.2,206.1 297.9,205.7 298.7,205.2 299.3,204.7 299.7,204.3 300.3,203.8 300.7,203.4 301.1,202.9 301.8,202.4 302.2,202.0 302.8,201.5 303.2,201.1 303.5,200.6 303.9,200.1 304.3,199.7 304.8,199.2 305.3,198.8 305.7,198.3 306.2,197.8 306.7,197.4 307.2,196.9 307.7,196.5 308.2,196.0 308.9,195.5 309.2,195.1 309.7,194.6 310.3,194.2 310.8,193.7 311.2,193.2 311.6,192.8 312.0,192.3 312.3,191.9 312.8,191.4 313.3,190.9 313.6,190.5 314.2,190.0 314.7,189.6 315.1,189.1 315.7,188.6 316.2,188.2 316.5,187.7 316.8,187.3 317.2,186.8 317.7,186.3 318.1,185.9 318.4,185.4 318.9,185.0 319.2,184.5 319.6,184.0 319.9,183.6 320.4,183.1 321.0,182.7 321.5,182.2 321.8,181.7 322.3,181.3 322.7,180.8 323.1,180.4 323.5,179.9 323.8,179.4 324.1,179.0 324.6,178.5 325.0,178.1 325.5,177.6 325.8,177.1 326.2,176.7 326.7,176.2 327.2,175.8 327.4,175.3 327.7,174.8 328.2,174.4 328.5,173.9 328.9,173.5 329.4,173.0 329.7,172.5 329.9,172.1 330.3,171.6 330.7,171.2 331.2,170.7 331.6,170.2 332.1,169.8 332.6,169.3 333.1,168.9 333.5,168.4 333.8,167.9 334.2,167.5 334.7,167.0 335.3,166.6 335.7,166.1 336.1,165.6 336.5,165.2 336.9,164.7 337.2,164.3 337.6,163.8 338.0,163.3 338.3,162.9 338.7,162.4 339.1,162.0 339.3,161.5 339.6,161.0 339.9,160.6 340.2,160.1 340.5,159.7 340.7,159.2 341.2,158.7 341.5,158.3 341.8,157.8 342.2,157.4 342.6,156.9 343.2,156.4 343.6,156.0 343.9,155.5 344.3,155.1 344.6,154.6 344.9,154.1 345.3,153.7 345.6,153.2 346.0,152.8 346.4,152.3 346.8,151.8 347.2,151.4 347.5,150.9 347.9,150.5 348.3,150.0 348.6,149.5 349.2,149.1 349.5,148.6 350.0,148.2 350.3,147.7 350.6,147.2 351.0,146.8 351.2,146.3 351.6,145.9 351.9,145.4 352.2,144.9 352.7,144.5 352.9,144.0 353.3,143.6 353.7,143.1 354.0,142.6 354.2,142.2 354.6,141.7 355.0,141.3 355.4,140.8 355.8,140.3 356.1,139.9 356.5,139.4 357.0,139.0 357.4,138.5 357.8,138.0 358.2,137.6 358.4,137.1 358.9,136.7 359.3,136.2 359.7,135.7 360.1,135.3 360.6,134.8 360.8,134.4 361.3,133.9 361.7,133.4 362.0,133.0 362.3,132.5 362.5,132.1 362.9,131.6 363.2,131.1 363.5,130.7 363.9,130.2 364.3,129.8 364.7,129.3 365.0,128.8 365.4,128.4 365.6,127.9 365.9,127.5 366.3,127.0 366.7,126.5 367.1,126.1 367.5,125.6 367.8,125.2 368.1,124.7 368.6,124.2 369.0,123.8 369.3,123.3 369.7,122.9 370.1,122.4 370.5,121.9 370.8,121.5 371.2,121.0 371.6,120.6 371.9,120.1 372.4,119.6 372.8,119.2 373.3,118.7 373.6,118.3 373.9,117.8 374.2,117.3 374.6,116.9 375.0,116.4 375.3,116.0 375.5,115.5 375.9,115.0 376.4,114.6 376.7,114.1 377.1,113.7 377.4,113.2 377.8,112.7 378.1,112.3 378.6,111.8 378.9,111.4 379.3,110.9 379.7,110.4 379.9,110.0 380.3,109.5 380.9,109.1 381.3,108.6 381.5,108.1 381.8,107.7 382.2,107.2 382.4,106.8 382.8,106.3 383.2,105.8 383.5,105.4 383.8,104.9 384.1,104.5 384.4,104.0 384.7,103.5 385.2,103.1 385.4,102.6 385.8,102.2 386.2,101.7 386.5,101.2 387.0,100.8 387.4,100.3 387.9,99.9 388.2,99.4 388.5,98.9 389.0,98.5 389.5,98.0 389.8,97.6 390.3,97.1 390.9,96.6 391.3,96.2 391.8,95.7 392.3,95.3 392.7,94.8 393.1,94.3 393.4,93.9 393.8,93.4 394.4,93.0 394.9,92.5 395.2,92.0 395.7,91.6 396.0,91.1 396.4,90.7 396.7,90.2 397.1,89.7 397.5,89.3 397.9,88.8 398.2,88.4 398.6,87.9 399.1,87.4 399.5,87.0 399.8,86.5 400.2,86.1 400.6,85.6 401.2,85.1 401.4,84.7 401.9,84.2 402.3,83.8 402.7,83.3 403.1,82.8 403.3,82.4 403.7,81.9 404.0,81.5 404.4,81.0 404.9,80.5 405.3,80.1 405.6,79.6 405.9,79.2 406.3,78.7 406.6,78.2 407.3,77.8 407.8,77.3 408.2,76.9 408.8,76.4 409.3,75.9 409.8,75.5 410.2,75.0 410.6,74.6 411.1,74.1 411.6,73.6 412.1,73.2 412.6,72.7 413.1,72.3 413.6,71.8 414.4,71.3 414.9,70.9 415.4,70.4 415.9,70.0 416.1,69.5 416.4,69.0 416.8,68.6 417.3,68.1 417.6,67.7 418.1,67.2 418.6,66.7 419.4,66.3 419.9,65.8 420.7,65.4 421.3,64.9 422.0,64.4 422.3,64.0 422.7,63.5 423.3,63.1 423.9,62.6 424.3,62.1 424.7,61.7 425.3,61.2 425.8,60.8 426.2,60.3 427.0,59.8 427.6,59.4 428.0,58.9 428.4,58.5 429.1,58.0 429.6,57.5 429.9,57.1 430.6,56.6 430.9,56.2 431.5,55.7 431.9,55.2 432.5,54.8 433.1,54.3 433.5,53.9 434.3,53.4 435.0,52.9 435.5,52.5 436.2,52.0 436.8,51.6 437.3,51.1 437.8,50.6 438.4,50.2 439.1,49.7 439.8,49.3 440.4,48.8 441.0,48.3 441.6,47.9 442.6,47.4 443.2,47.0 444.0,46.5 444.8,46.0 445.3,45.6 445.8,45.1 446.4,44.7 447.2,44.2 448.0,43.7 448.8,43.3 449.3,42.8 450.0,42.4 450.8,41.9 451.8,41.4 452.6,41.0 453.1,40.5 454.2,40.1 454.9,39.6 455.9,39.1 456.5,38.7 457.4,38.2 458.1,37.8 459.4,37.3 460.2,36.8 461.0,36.4 462.1,35.9 463.1,35.5 464.5,35.0 465.7,34.5 466.4,34.1 468.2,33.6 469.2,33.2 470.2,32.7 471.5,32.2 473.3,31.8 474.1,31.3 474.9,30.9 476.0,30.4 477.0,29.9 478.3,29.5 479.5,29.0 481.0,28.6 482.4,28.1 484.2,27.6 485.5,27.2 487.7,26.7 488.9,26.3 491.2,25.8 492.9,25.3 494.8,24.9 496.3,24.4 498.6,24.0 502.2,23.5 504.3,23.0 507.5,22.6 508.9,22.1 513.1,21.7 516.4,21.2 519.9,20.7 524.1,20.3 529.9,19.8 535.9,19.4 542.8,18.9 560.5,18.4" fill="none" stroke="#1a1a1a" stroke-width="1.8"/><line x1="64" y1="248.0" x2="660" y2="248.0" stroke="#1a1a1a"/><line x1="64" y1="248.0" x2="64" y2="18.0" stroke="#1a1a1a"/><text paint-order="stroke" stroke="#fbfcfe" stroke-width="4" stroke-linejoin="round" x="56" y="252.0" font-size="12" text-anchor="end" fill="#1a1a1a">0</text><text paint-order="stroke" stroke="#fbfcfe" stroke-width="4" stroke-linejoin="round" x="56" y="137.0" font-size="12" text-anchor="end" fill="#1a1a1a">0.5</text><text paint-order="stroke" stroke="#fbfcfe" stroke-width="4" stroke-linejoin="round" x="56" y="22.0" font-size="12" text-anchor="end" fill="#1a1a1a">1</text><line x1="286.8" y1="248.0" x2="286.8" y2="253.0" stroke="#1a1a1a"/><text paint-order="stroke" stroke="#fbfcfe" stroke-width="4" stroke-linejoin="round" x="286.8" y="266.0" font-size="12" text-anchor="middle" fill="#1a1a1a">10 000</text><line x1="523.2" y1="248.0" x2="523.2" y2="253.0" stroke="#1a1a1a"/><text paint-order="stroke" stroke="#fbfcfe" stroke-width="4" stroke-linejoin="round" x="523.2" y="266.0" font-size="12" text-anchor="middle" fill="#1a1a1a">10 200</text><text paint-order="stroke" stroke="#fbfcfe" stroke-width="4" stroke-linejoin="round" x="362.0" y="292" font-size="12" text-anchor="middle" fill="#888888">KRF efficiency ε(843 keV), a.u. — 10 000 Monte Carlo refits of the bundled dataset</text><text paint-order="stroke" stroke="#fbfcfe" stroke-width="4" stroke-linejoin="round" x="14" y="133.0" font-size="12" text-anchor="middle" fill="#888888" transform="rotate(-90 14 133.0)">fraction of refits ≤ ε</text><line x1="64" y1="211.5" x2="290.7" y2="211.5" stroke="#0066cc" stroke-width="1.4" stroke-dasharray="5,3"/><line x1="290.7" y1="211.5" x2="290.7" y2="248.0" stroke="#0066cc" stroke-width="1.4" stroke-dasharray="5,3"/><circle cx="290.7" cy="211.5" r="3.5" fill="#0066cc"/><text paint-order="stroke" stroke="#fbfcfe" stroke-width="4" stroke-linejoin="round" x="70" y="206.5" font-size="12" fill="#0066cc">0.1587</text><text paint-order="stroke" stroke="#fbfcfe" stroke-width="4" stroke-linejoin="round" x="283.7" y="204.5" font-size="12" text-anchor="end" fill="#0066cc" font-weight="600">p16 = 10 003.3</text><line x1="64" y1="133.0" x2="362.0" y2="133.0" stroke="#d9730d" stroke-width="1.4" stroke-dasharray="5,3"/><line x1="362.0" y1="133.0" x2="362.0" y2="248.0" stroke="#d9730d" stroke-width="1.4" stroke-dasharray="5,3"/><circle cx="362.0" cy="133.0" r="3.5" fill="#d9730d"/><text paint-order="stroke" stroke="#fbfcfe" stroke-width="4" stroke-linejoin="round" x="70" y="128.0" font-size="12" fill="#d9730d">0.5000</text><text paint-order="stroke" stroke="#fbfcfe" stroke-width="4" stroke-linejoin="round" x="355.0" y="126.0" font-size="12" text-anchor="end" fill="#d9730d" font-weight="600">p50 = 10 063.6</text><line x1="64" y1="54.5" x2="433.0" y2="54.5" stroke="#0066cc" stroke-width="1.4" stroke-dasharray="5,3"/><line x1="433.0" y1="54.5" x2="433.0" y2="248.0" stroke="#0066cc" stroke-width="1.4" stroke-dasharray="5,3"/><circle cx="433.0" cy="54.5" r="3.5" fill="#0066cc"/><text paint-order="stroke" stroke="#fbfcfe" stroke-width="4" stroke-linejoin="round" x="70" y="49.5" font-size="12" fill="#0066cc">0.8413</text><text paint-order="stroke" stroke="#fbfcfe" stroke-width="4" stroke-linejoin="round" x="426.0" y="47.5" font-size="12" text-anchor="end" fill="#0066cc" font-weight="600">p84 = 10 123.6</text></svg>
<figcaption>Figure 1. CalEnEff's own Monte Carlo for the bundled dataset: the
cumulative distribution of the KRF efficiency at 843 keV over 10 000 refits.
Each percentile is read where the curve crosses its probability level:
p16 = 10 003.3, p50 = 10 063.6, p84 = 10 123.6 a.u.</figcaption></figure>
<p><strong>From the percentiles to the reported result</strong> (same
example, best fit 10 062.1 a.u., Birge ratio B = 5.08):</p>
<div class='formula'>lower 1σ = B · (p50 − p16) = 5.08 × (10 063.6 − 10 003.3) = 306.6
upper 1σ = B · (p84 − p50) = 5.08 × (10 123.6 − 10 063.6) = 305.1
reported:  ε(843 keV) = 10 062.1  −306.6 / +305.1 a.u.</div>

<h3>What the output numbers mean</h3>
<p>The plotted band, the query result, the MC histogram and the SpectraTools
export all use one rule, with p16, p50 and p84 the percentiles defined above
and B the Birge ratio (taken as 1 when it is below 1):</p>
<div class='formula'>value = ε(E*; θ̂)           (the best fit)
lower 1σ = B·(p50 − p16)      upper 1σ = B·(p84 − p50)
σ = B·(p84 − p16)/2           (symmetric summary; the export's deff)</div>
<table>
  <tr><th>Output</th><th>Definition</th><th>When to use it</th></tr>
  <tr><td><strong>Best fit</strong> ε(E*; θ̂)</td>
      <td>Direct evaluation of the fitted curve at E*</td>
      <td><strong>The value to report</strong> (least-squares
          result)</td></tr>
  <tr><td><strong>Δε (1σ, ×B)</strong></td>
      <td>+upper / −lower as above</td>
      <td><strong>The uncertainty to report.</strong> Captures parameter
          correlations, the fit's non-linearity and any asymmetry, and
          ignores the odd runaway refit that would inflate a standard
          deviation. Measured from the MC median, so the interval always
          contains the best fit.</td></tr>
  <tr><td><strong>MC median</strong> and <strong>z</strong></td>
      <td>p50, and z = (p50 − best fit) / ((p84 − p16)/2), unscaled</td>
      <td>A <em>check</em>, not a result. A healthy bootstrap gives |z| of a
          few hundredths. <strong>|z| &gt; 1</strong> means the refits do
          not scatter around the best fit — for example because they
          converged to a different local minimum — and the uncertainty
          cannot be trusted; CalEnEff then warns in the status bar, the
          legend, the results file and the query log. Do <em>not</em>
          "correct" the best fit with the MC mean or median: when the
          offset comes from a different minimum, 2·best-fit − mean moves the
          value further from the truth, not closer.</td></tr>
</table>
<div class='note'>
<strong>Practical guidance:</strong>
Report the best-fit value with its +upper/−lower 1σ (68% coverage) — inside
the calibrated energy range only. Outside it both models extrapolate, can
disagree by orders of magnitude, and CalEnEff flags such queries. The
difference between the KRF and Radware curves is a model uncertainty that
neither band contains; where it exceeds the 1σ, quote it separately. The
same holds for a second Radware solution: when the fit finds another
minimum within Δχ²/B² &lt; 1 of the best one, the results file lists it and
how far its curve departs — that ambiguity is not in the band either.
For publication, also quote the Birge-scaled parameter uncertainties
from the fit result table so reviewers can judge the goodness of fit.
</div>
<h3>Why the best fit is the result and the MC median only a check</h3>
<p>Every query — energy and efficiency — shows three numbers in the same
order: the <strong>best fit</strong>, its <strong>1σ</strong>, and the
<strong>Monte Carlo median</strong>. The order is deliberate: the best fit
is the measurement, the Monte Carlo tells you how uncertain it is, and the
median confirms that this uncertainty is about the value reported.</p>

<p><strong>1. The best fit is the estimate the data support.</strong>
It is the curve that minimises χ² on your measured points — the
least-squares estimate, which for Gaussian errors is also the
maximum-likelihood estimate. The χ², the Birge ratio, the residual plot and
the drawn curve all belong to it, and it is deterministic: the same file
always gives the same number.</p>

<p><strong>2. The Monte Carlo measures uncertainty; it does not improve the
estimate.</strong> It is a parametric bootstrap: it takes your
already-noisy data, adds noise again 10 000 times, and refits each time.
That answers one question — <em>if the measurement were repeated, how much
would the result scatter?</em> — and its <strong>spread</strong> becomes
the 1σ. Its <strong>centre</strong> is not closer to the truth. Each
replicate is (truth + your measurement's noise) + fresh simulated noise, so
the ensemble is centred on your best fit, not on the true curve. Taking its
median as the result would not remove your measurement's error; at best it
reproduces the best fit, at worst it adds a bias of the fitting procedure
on top.</p>

<p><strong>3. A median curve is not a curve of the model.</strong> The
median at 300 keV and the median at 2000 keV generally come from different
replicates. Joined point by point they form a curve that no single set of
KRF or Radware parameters produces. The best fit is always a genuine curve
of the model, with one set of parameters you can quote.</p>

<p><strong>4. What the median is for: checking the uncertainty.</strong>
The difference between median and best fit estimates the bias of the
fitting procedure itself. CalEnEff turns it into a bias check,
z = (median − best fit) / σ<sub>MC</sub>:</p>
<ul>
  <li><strong>|z| of a few hundredths</strong> — the usual case. The refits
      scatter around the best fit, so the spread describes uncertainty
      <em>about the reported value</em>, and the 1σ can be quoted with
      it.</li>
  <li><strong>|z| &gt; 1</strong> — something is wrong and the 1σ is not
      reliable; CalEnEff warns in the status bar, the plot legend, the
      results file and the query log. Version 4.8 is the example: the
      Radware refits had converged to a different solution from the plotted
      curve, and z was 8.65. Had the median been promoted to "the result",
      the app would have reported that wrong solution — 10 187 instead of
      9 750 at 843 keV.</li>
</ul>

<p><strong>5. Why the median and not the mean.</strong> Both describe the
centre of the Monte Carlo distribution and agree when it is symmetric. They
part when it is skewed — typically when a curve is extrapolated beyond the
calibration lines — or when a few refits run away: those drag the mean (and
the standard deviation) far more than the median. The median is also the
50 % point of the same 15.87/50/84.13 % quantiles the 1σ is built from, so
value, interval and check use one set of statistics.</p>

<p><strong>6. Why not "correct" the best fit with the median?</strong>
Textbook bias correction, 2·best fit − median, works only when the offset is
a small, smooth statistical bias. A large offset almost always means a
convergence or model problem, and the "correction" then moves the value
further from the truth — in version 4.8 by 438 units at 843 keV, the wrong
way. When the offset is small, as it is when |z| is small, the correction is
negligible anyway. Either way there is nothing to gain.</p>

<p><strong>7. The evidence.</strong> The construction was tested for
frequentist coverage: 120 synthetic datasets drawn from a known true curve
with the stated uncertainties, each calibrated by CalEnEff. The interval
<em>best fit ± 1σ</em> contained the truth 67.5–71.7 % of the time for KRF
and 69–77 % for Radware, against the 68.3 % a correct 1σ interval should
give.</p>

<div class='note'><strong>In short:</strong> report the best fit with its
1σ; glance at the MC median (or z) to confirm the two agree; never report
the median instead.</div>

<h3>Why σ comes from the 15.87 %, 50 % and 84.13 % percentiles</h3>
<p>Every efficiency uncertainty in CalEnEff — the plotted band, the query, the
histogram and the SpectraTools export — is built from three percentiles of
the Monte Carlo values, p16, p50 and p84 (defined above: the values below
which 15.87 %, 50 % and 84.13 % of the refits lie). The levels are not
arbitrary.</p>

<h3>Where the numbers come from</h3>
<p>For a normal distribution the fraction of outcomes below μ + kσ is the
cumulative distribution Φ(k). At k = −1, 0, +1:</p>
<div class='formula'>Φ(−1) = 0.1587  →  p16 = μ − σ
Φ( 0) = 0.5000  →  p50 = μ
Φ(+1) = 0.8413  →  p84 = μ + σ</div>
<figure class="fig"><svg viewBox="0 0 680 250" role="img" aria-label="Gaussian distribution with the 15.87, 50 and 84.13 percent points" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI, Helvetica, Arial, sans-serif"><polygon points="263.9,200.0 263.9,109.3 266.0,107.0 268.2,104.7 270.3,102.5 272.5,100.2 274.7,98.0 276.8,95.8 279.0,93.6 281.1,91.4 283.3,89.2 285.4,87.1 287.6,85.0 289.7,82.9 291.9,80.9 294.0,78.9 296.2,76.9 298.3,75.0 300.5,73.2 302.6,71.4 304.8,69.7 306.9,68.0 309.1,66.4 311.3,64.8 313.4,63.3 315.6,61.9 317.7,60.6 319.9,59.3 322.0,58.1 324.2,57.0 326.3,55.9 328.5,55.0 330.6,54.1 332.8,53.4 334.9,52.7 337.1,52.1 339.2,51.6 341.4,51.1 343.5,50.8 345.7,50.6 347.8,50.4 350.0,50.4 352.2,50.4 354.3,50.6 356.5,50.8 358.6,51.1 360.8,51.6 362.9,52.1 365.1,52.7 367.2,53.4 369.4,54.1 371.5,55.0 373.7,55.9 375.8,57.0 378.0,58.1 380.1,59.3 382.3,60.6 384.4,61.9 386.6,63.3 388.8,64.8 390.9,66.4 393.1,68.0 395.2,69.7 397.4,71.4 399.5,73.2 401.7,75.0 403.8,76.9 406.0,78.9 408.1,80.9 410.3,82.9 412.4,85.0 414.6,87.1 416.7,89.2 418.9,91.4 421.0,93.6 423.2,95.8 425.3,98.0 427.5,100.2 429.7,102.5 431.8,104.7 434.0,107.0 436.1,109.3 436.1,200.0" fill="#0066cc" fill-opacity="0.18"/><polyline points="40.0,199.8 42.6,199.7 45.2,199.7 47.7,199.7 50.3,199.6 52.9,199.6 55.5,199.6 58.1,199.5 60.7,199.5 63.2,199.4 65.8,199.4 68.4,199.3 71.0,199.2 73.6,199.1 76.2,199.0 78.8,199.0 81.3,198.8 83.9,198.7 86.5,198.6 89.1,198.5 91.7,198.3 94.2,198.2 96.8,198.0 99.4,197.8 102.0,197.6 104.6,197.4 107.2,197.2 109.8,196.9 112.3,196.7 114.9,196.4 117.5,196.1 120.1,195.8 122.7,195.4 125.3,195.0 127.8,194.6 130.4,194.2 133.0,193.7 135.6,193.3 138.2,192.7 140.8,192.2 143.3,191.6 145.9,191.0 148.5,190.3 151.1,189.6 153.7,188.9 156.2,188.1 158.8,187.3 161.4,186.4 164.0,185.5 166.6,184.5 169.2,183.5 171.7,182.4 174.3,181.3 176.9,180.2 179.5,178.9 182.1,177.7 184.7,176.3 187.2,174.9 189.8,173.5 192.4,172.0 195.0,170.4 197.6,168.8 200.2,167.1 202.8,165.3 205.3,163.5 207.9,161.7 210.5,159.7 213.1,157.7 215.7,155.7 218.3,153.6 220.8,151.4 223.4,149.2 226.0,147.0 228.6,144.6 231.2,142.3 233.8,139.9 236.3,137.4 238.9,134.9 241.5,132.4 244.1,129.8 246.7,127.2 249.2,124.5 251.8,121.9 254.4,119.2 257.0,116.5 259.6,113.8 262.2,111.1 264.8,108.4 267.3,105.6 269.9,102.9 272.5,100.2 275.1,97.5 277.7,94.9 280.2,92.2 282.8,89.6 285.4,87.1 288.0,84.6 290.6,82.1 293.2,79.7 295.8,77.3 298.3,75.0 300.9,72.8 303.5,70.7 306.1,68.6 308.7,66.7 311.3,64.8 313.8,63.0 316.4,61.4 319.0,59.8 321.6,58.3 324.2,57.0 326.8,55.8 329.3,54.6 331.9,53.7 334.5,52.8 337.1,52.1 339.7,51.5 342.2,51.0 344.8,50.7 347.4,50.5 350.0,50.4 352.6,50.5 355.2,50.7 357.8,51.0 360.3,51.5 362.9,52.1 365.5,52.8 368.1,53.7 370.7,54.6 373.2,55.8 375.8,57.0 378.4,58.3 381.0,59.8 383.6,61.4 386.2,63.0 388.8,64.8 391.3,66.7 393.9,68.6 396.5,70.7 399.1,72.8 401.7,75.0 404.2,77.3 406.8,79.7 409.4,82.1 412.0,84.6 414.6,87.1 417.2,89.6 419.8,92.2 422.3,94.9 424.9,97.5 427.5,100.2 430.1,102.9 432.7,105.6 435.3,108.4 437.8,111.1 440.4,113.8 443.0,116.5 445.6,119.2 448.2,121.9 450.8,124.5 453.3,127.2 455.9,129.8 458.5,132.4 461.1,134.9 463.7,137.4 466.2,139.9 468.8,142.3 471.4,144.6 474.0,147.0 476.6,149.2 479.2,151.4 481.8,153.6 484.3,155.7 486.9,157.7 489.5,159.7 492.1,161.7 494.7,163.5 497.2,165.3 499.8,167.1 502.4,168.8 505.0,170.4 507.6,172.0 510.2,173.5 512.8,174.9 515.3,176.3 517.9,177.7 520.5,178.9 523.1,180.2 525.7,181.3 528.2,182.4 530.8,183.5 533.4,184.5 536.0,185.5 538.6,186.4 541.2,187.3 543.8,188.1 546.3,188.9 548.9,189.6 551.5,190.3 554.1,191.0 556.7,191.6 559.2,192.2 561.8,192.7 564.4,193.3 567.0,193.7 569.6,194.2 572.2,194.6 574.8,195.0 577.3,195.4 579.9,195.8 582.5,196.1 585.1,196.4 587.7,196.7 590.2,196.9 592.8,197.2 595.4,197.4 598.0,197.6 600.6,197.8 603.2,198.0 605.8,198.2 608.3,198.3 610.9,198.5 613.5,198.6 616.1,198.7 618.7,198.8 621.3,199.0 623.8,199.0 626.4,199.1 629.0,199.2 631.6,199.3 634.2,199.4 636.8,199.4 639.3,199.5 641.9,199.5 644.5,199.6 647.1,199.6 649.7,199.6 652.2,199.7 654.8,199.7 657.4,199.7 660.0,199.8" fill="none" stroke="#1a1a1a" stroke-width="1.8"/><line x1="263.9" y1="200.0" x2="263.9" y2="65.0" stroke="#0066cc" stroke-width="1.6" stroke-dasharray="5,3"/><text paint-order="stroke" stroke="#fbfcfe" stroke-width="4" stroke-linejoin="round" x="263.9" y="60.0" fill="#0066cc" font-size="12" text-anchor="middle">p16 = μ − σ</text><line x1="350.0" y1="200.0" x2="350.0" y2="38.8" stroke="#d9730d" stroke-width="1.6"/><text paint-order="stroke" stroke="#fbfcfe" stroke-width="4" stroke-linejoin="round" x="350.0" y="33.8" fill="#d9730d" font-size="12" text-anchor="middle">p50 = median = μ</text><line x1="436.1" y1="200.0" x2="436.1" y2="65.0" stroke="#0066cc" stroke-width="1.6" stroke-dasharray="5,3"/><text paint-order="stroke" stroke="#fbfcfe" stroke-width="4" stroke-linejoin="round" x="436.1" y="60.0" fill="#0066cc" font-size="12" text-anchor="middle">p84 = μ + σ</text><text paint-order="stroke" stroke="#fbfcfe" stroke-width="4" stroke-linejoin="round" x="350.0" y="155.0" font-size="13" text-anchor="middle" fill="#0066cc" font-weight="600">68.27 %</text><text paint-order="stroke" stroke="#fbfcfe" stroke-width="4" stroke-linejoin="round" x="113.2" y="171.9" font-size="12" text-anchor="middle" fill="#888888">15.87 %</text><text paint-order="stroke" stroke="#fbfcfe" stroke-width="4" stroke-linejoin="round" x="586.8" y="171.9" font-size="12" text-anchor="middle" fill="#888888">15.87 %</text><line x1="40" y1="200.0" x2="660" y2="200.0" stroke="#1a1a1a" stroke-width="1"/><line x1="91.7" y1="200.0" x2="91.7" y2="205.0" stroke="#1a1a1a"/><text paint-order="stroke" stroke="#fbfcfe" stroke-width="4" stroke-linejoin="round" x="91.7" y="218.0" font-size="12" text-anchor="middle" fill="#1a1a1a">μ−3σ</text><line x1="177.8" y1="200.0" x2="177.8" y2="205.0" stroke="#1a1a1a"/><text paint-order="stroke" stroke="#fbfcfe" stroke-width="4" stroke-linejoin="round" x="177.8" y="218.0" font-size="12" text-anchor="middle" fill="#1a1a1a">μ−2σ</text><line x1="263.9" y1="200.0" x2="263.9" y2="205.0" stroke="#1a1a1a"/><text paint-order="stroke" stroke="#fbfcfe" stroke-width="4" stroke-linejoin="round" x="263.9" y="218.0" font-size="12" text-anchor="middle" fill="#1a1a1a">μ−σ</text><line x1="350.0" y1="200.0" x2="350.0" y2="205.0" stroke="#1a1a1a"/><text paint-order="stroke" stroke="#fbfcfe" stroke-width="4" stroke-linejoin="round" x="350.0" y="218.0" font-size="12" text-anchor="middle" fill="#1a1a1a">μ</text><line x1="436.1" y1="200.0" x2="436.1" y2="205.0" stroke="#1a1a1a"/><text paint-order="stroke" stroke="#fbfcfe" stroke-width="4" stroke-linejoin="round" x="436.1" y="218.0" font-size="12" text-anchor="middle" fill="#1a1a1a">μ+σ</text><line x1="522.2" y1="200.0" x2="522.2" y2="205.0" stroke="#1a1a1a"/><text paint-order="stroke" stroke="#fbfcfe" stroke-width="4" stroke-linejoin="round" x="522.2" y="218.0" font-size="12" text-anchor="middle" fill="#1a1a1a">μ+2σ</text><line x1="608.3" y1="200.0" x2="608.3" y2="205.0" stroke="#1a1a1a"/><text paint-order="stroke" stroke="#fbfcfe" stroke-width="4" stroke-linejoin="round" x="608.3" y="218.0" font-size="12" text-anchor="middle" fill="#1a1a1a">μ+3σ</text><text paint-order="stroke" stroke="#fbfcfe" stroke-width="4" stroke-linejoin="round" x="350.0" y="242" font-size="12" text-anchor="middle" fill="#888888">Gaussian: the 15.87 / 50 / 84.13 % points fall exactly at μ − σ, μ, μ + σ</text></svg>
<figcaption>Figure 2. For a Gaussian, p16, p50 and p84 — the 15.87 %, 50 % and
84.13 % points — are exactly μ − σ, μ and μ + σ, and the range between the outer two holds
68.27 % of the outcomes — the probability content of ±1σ.</figcaption></figure>
<p>So for Gaussian Monte Carlo values, half the 15.87–84.13 % range <em>is</em>
the standard deviation:</p>
<div class='formula'>σ₆₈ = (p84 − p16) / 2       = σ for a Gaussian</div>
<p>It is a second way of measuring the same σ, not a different definition. On
the bundled dataset, inside the calibrated range, std/σ₆₈ was 0.97–1.04.</p>

<h3>Why not simply the standard deviation?</h3>
<p>On a Gaussian the two agree. They differ only where the distribution is
not Gaussian — and there the percentiles give the more meaningful
number.</p>
<p><strong>1. The same coverage for any shape.</strong> Whatever the
distribution looks like, the 15.87–84.13 % interval still contains 68.27 % of
the outcomes, which is the property a "1σ" is supposed to have. For a
skewed or heavy-tailed distribution, mean ± std contains some other,
unknown fraction.</p>
<figure class="fig"><svg viewBox="0 0 680 250" role="img" aria-label="Skewed distribution: percentile interval versus mean plus or minus standard deviation" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI, Helvetica, Arial, sans-serif"><polygon points="125.2,200.0 125.2,99.6 126.6,98.2 128.0,97.0 129.5,95.9 130.9,94.8 132.3,93.9 133.8,93.0 135.2,92.2 136.7,91.5 138.1,90.9 139.5,90.4 141.0,90.0 142.4,89.6 143.8,89.3 145.3,89.1 146.7,89.0 148.1,88.9 149.6,88.9 151.0,88.9 152.4,89.0 153.9,89.2 155.3,89.4 156.7,89.7 158.2,90.0 159.6,90.4 161.0,90.8 162.5,91.3 163.9,91.8 165.3,92.4 166.8,93.0 168.2,93.6 169.6,94.2 171.1,94.9 172.5,95.6 173.9,96.4 175.4,97.1 176.8,97.9 178.2,98.7 179.7,99.6 181.1,100.4 182.5,101.3 184.0,102.2 185.4,103.1 186.8,104.0 188.3,104.9 189.7,105.8 191.1,106.8 192.6,107.8 194.0,108.7 195.4,109.7 196.9,110.7 198.3,111.7 199.8,112.6 201.2,113.6 202.6,114.6 204.1,115.6 205.5,116.6 206.9,117.6 208.4,118.6 209.8,119.6 211.2,120.6 212.7,121.6 214.1,122.6 215.5,123.6 217.0,124.5 218.4,125.5 219.8,126.5 221.3,127.4 222.7,128.4 224.1,129.4 225.6,130.3 227.0,131.3 228.4,132.2 229.9,133.1 231.3,134.0 232.7,135.0 234.2,135.9 235.6,136.8 237.0,137.7 238.5,138.5 239.9,139.4 241.3,140.3 242.8,141.1 244.2,142.0 245.6,142.8 247.1,143.7 248.5,144.5 249.9,145.3 251.4,146.1 252.8,146.9 254.2,147.7 255.7,148.5 257.1,149.2 258.5,150.0 260.0,150.7 261.4,151.5 262.9,152.2 264.3,152.9 265.7,153.6 267.2,154.3 268.6,155.0 270.0,155.7 271.5,156.4 272.9,157.1 274.3,157.7 275.8,158.4 277.2,159.0 278.6,159.6 280.1,160.3 281.5,160.9 282.9,161.5 284.4,162.1 285.8,162.7 287.2,163.3 288.7,163.8 290.1,164.4 291.5,164.9 293.0,165.5 294.4,166.0 295.8,166.6 295.8,200.0" fill="#0066cc" fill-opacity="0.18"/><polyline points="40.7,200.0 42.8,200.0 44.9,200.0 47.0,200.0 49.0,200.0 51.1,200.0 53.2,199.9 55.2,199.8 57.3,199.6 59.4,199.2 61.4,198.6 63.5,197.7 65.6,196.6 67.7,195.1 69.7,193.2 71.8,191.0 73.9,188.4 75.9,185.5 78.0,182.3 80.1,178.8 82.2,175.1 84.2,171.1 86.3,167.0 88.4,162.8 90.4,158.4 92.5,154.1 94.6,149.7 96.7,145.3 98.7,141.0 100.8,136.8 102.9,132.7 104.9,128.8 107.0,124.9 109.1,121.3 111.2,117.8 113.2,114.5 115.3,111.5 117.4,108.6 119.4,105.9 121.5,103.4 123.6,101.2 125.7,99.1 127.7,97.3 129.8,95.6 131.9,94.2 133.9,92.9 136.0,91.8 138.1,90.9 140.2,90.2 142.2,89.7 144.3,89.3 146.4,89.0 148.4,88.9 150.5,88.9 152.6,89.1 154.6,89.3 156.7,89.7 158.8,90.2 160.9,90.8 162.9,91.5 165.0,92.2 167.1,93.1 169.1,94.0 171.2,95.0 173.3,96.0 175.4,97.1 177.4,98.3 179.5,99.5 181.6,100.7 183.6,102.0 185.7,103.3 187.8,104.6 189.9,105.9 191.9,107.3 194.0,108.7 196.1,110.1 198.1,111.5 200.2,113.0 202.3,114.4 204.4,115.8 206.4,117.3 208.5,118.7 210.6,120.1 212.6,121.6 214.7,123.0 216.8,124.4 218.9,125.8 220.9,127.2 223.0,128.6 225.1,130.0 227.1,131.3 229.2,132.7 231.3,134.0 233.4,135.3 235.4,136.6 237.5,137.9 239.6,139.2 241.6,140.5 243.7,141.7 245.8,142.9 247.8,144.1 249.9,145.3 252.0,146.4 254.1,147.6 256.1,148.7 258.2,149.8 260.3,150.9 262.3,151.9 264.4,153.0 266.5,154.0 268.6,155.0 270.6,156.0 272.7,157.0 274.8,157.9 276.8,158.9 278.9,159.8 281.0,160.7 283.1,161.5 285.1,162.4 287.2,163.2 289.3,164.1 291.3,164.9 293.4,165.7 295.5,166.4 297.6,167.2 299.6,167.9 301.7,168.7 303.8,169.4 305.8,170.1 307.9,170.7 310.0,171.4 312.1,172.1 314.1,172.7 316.2,173.3 318.3,173.9 320.3,174.5 322.4,175.1 324.5,175.7 326.6,176.2 328.6,176.8 330.7,177.3 332.8,177.8 334.8,178.3 336.9,178.8 339.0,179.3 341.0,179.8 343.1,180.2 345.2,180.7 347.3,181.1 349.3,181.6 351.4,182.0 353.5,182.4 355.5,182.8 357.6,183.2 359.7,183.6 361.8,183.9 363.8,184.3 365.9,184.7 368.0,185.0 370.0,185.3 372.1,185.7 374.2,186.0 376.3,186.3 378.3,186.6 380.4,186.9 382.5,187.2 384.5,187.5 386.6,187.8 388.7,188.1 390.8,188.3 392.8,188.6 394.9,188.9 397.0,189.1 399.0,189.4 401.1,189.6 403.2,189.8 405.3,190.1 407.3,190.3 409.4,190.5 411.5,190.7 413.5,190.9 415.6,191.1 417.7,191.3 419.8,191.5 421.8,191.7 423.9,191.9 426.0,192.1 428.0,192.2 430.1,192.4 432.2,192.6 434.2,192.7 436.3,192.9 438.4,193.1 440.5,193.2 442.5,193.4 444.6,193.5 446.7,193.6 448.7,193.8 450.8,193.9 452.9,194.1 455.0,194.2 457.0,194.3 459.1,194.4 461.2,194.6 463.2,194.7 465.3,194.8 467.4,194.9 469.5,195.0 471.5,195.1 473.6,195.2 475.7,195.3 477.7,195.4 479.8,195.5 481.9,195.6 484.0,195.7 486.0,195.8 488.1,195.9 490.2,196.0 492.2,196.1 494.3,196.2 496.4,196.2 498.5,196.3 500.5,196.4 502.6,196.5 504.7,196.5 506.7,196.6 508.8,196.7 510.9,196.8 513.0,196.8 515.0,196.9 517.1,197.0 519.2,197.0 521.2,197.1 523.3,197.1 525.4,197.2 527.4,197.3 529.5,197.3 531.6,197.4 533.7,197.4 535.7,197.5 537.8,197.5 539.9,197.6 541.9,197.6 544.0,197.7 546.1,197.7 548.2,197.8 550.2,197.8 552.3,197.9 554.4,197.9 556.4,198.0 558.5,198.0 560.6,198.0 562.7,198.1 564.7,198.1 566.8,198.2 568.9,198.2 570.9,198.2 573.0,198.3 575.1,198.3 577.2,198.3 579.2,198.4 581.3,198.4 583.4,198.4 585.4,198.5 587.5,198.5 589.6,198.5 591.7,198.6 593.7,198.6 595.8,198.6 597.9,198.6 599.9,198.7 602.0,198.7 604.1,198.7 606.2,198.7 608.2,198.8 610.3,198.8 612.4,198.8 614.4,198.8 616.5,198.9 618.6,198.9 620.6,198.9 622.7,198.9 624.8,198.9 626.9,199.0 628.9,199.0 631.0,199.0 633.1,199.0 635.1,199.0 637.2,199.1 639.3,199.1 641.4,199.1 643.4,199.1 645.5,199.1 647.6,199.2 649.6,199.2 651.7,199.2 653.8,199.2 655.9,199.2 657.9,199.2 660.0,199.2" fill="none" stroke="#1a1a1a" stroke-width="1.8"/><line x1="125.2" y1="200.0" x2="125.2" y2="42.2" stroke="#0066cc" stroke-width="1.6" stroke-dasharray="5,3"/><line x1="295.8" y1="200.0" x2="295.8" y2="42.2" stroke="#0066cc" stroke-width="1.6" stroke-dasharray="5,3"/><line x1="187.6" y1="200.0" x2="187.6" y2="88.9" stroke="#d9730d" stroke-width="1.6"/><text paint-order="stroke" stroke="#fbfcfe" stroke-width="4" stroke-linejoin="round" x="193.6" y="161.1" font-size="12" fill="#d9730d">median</text><line x1="125.2" y1="42.2" x2="295.8" y2="42.2" stroke="#0066cc" stroke-width="3"/><text paint-order="stroke" stroke="#fbfcfe" stroke-width="4" stroke-linejoin="round" x="303.8" y="46.2" font-size="12" fill="#0066cc">p16 … p84: 68.27 %, −0.42 / +0.73</text><line x1="109.7" y1="67.5" x2="313.8" y2="67.5" stroke="#888888" stroke-width="3"/><circle cx="211.7" cy="67.5" r="3.5" fill="#888888"/><text paint-order="stroke" stroke="#fbfcfe" stroke-width="4" stroke-linejoin="round" x="321.8" y="71.5" font-size="12" fill="#888888">mean ± std: 78.3 %, symmetric ±0.69</text><line x1="40" y1="200.0" x2="660" y2="200.0" stroke="#1a1a1a" stroke-width="1"/><line x1="40.0" y1="200.0" x2="40.0" y2="205.0" stroke="#1a1a1a"/><text paint-order="stroke" stroke="#fbfcfe" stroke-width="4" stroke-linejoin="round" x="40.0" y="218.0" font-size="12" text-anchor="middle" fill="#1a1a1a">0</text><line x1="187.6" y1="200.0" x2="187.6" y2="205.0" stroke="#1a1a1a"/><text paint-order="stroke" stroke="#fbfcfe" stroke-width="4" stroke-linejoin="round" x="187.6" y="218.0" font-size="12" text-anchor="middle" fill="#1a1a1a">1</text><line x1="335.2" y1="200.0" x2="335.2" y2="205.0" stroke="#1a1a1a"/><text paint-order="stroke" stroke="#fbfcfe" stroke-width="4" stroke-linejoin="round" x="335.2" y="218.0" font-size="12" text-anchor="middle" fill="#1a1a1a">2</text><line x1="482.9" y1="200.0" x2="482.9" y2="205.0" stroke="#1a1a1a"/><text paint-order="stroke" stroke="#fbfcfe" stroke-width="4" stroke-linejoin="round" x="482.9" y="218.0" font-size="12" text-anchor="middle" fill="#1a1a1a">3</text><line x1="630.5" y1="200.0" x2="630.5" y2="205.0" stroke="#1a1a1a"/><text paint-order="stroke" stroke="#fbfcfe" stroke-width="4" stroke-linejoin="round" x="630.5" y="218.0" font-size="12" text-anchor="middle" fill="#1a1a1a">4</text><text paint-order="stroke" stroke="#fbfcfe" stroke-width="4" stroke-linejoin="round" x="350.0" y="242" font-size="12" text-anchor="middle" fill="#888888">Skewed distribution: the percentile interval keeps 68.27 % and the asymmetry; mean ± std does not</text></svg>
<figcaption>Figure 3. A skewed distribution (log-normal). The percentile
interval (blue) still holds 68.27 % and is asymmetric: −0.42 / +0.73
about the median. Mean ± standard deviation (grey) is symmetric (±0.69)
about a different centre and holds 78.3 % instead.</figcaption></figure>
<p><strong>2. Asymmetry is kept.</strong> The lower half-width p50 − p16 and
the upper half-width p84 − p50 are separate numbers, which is why CalEnEff
reports +upper / −lower. Efficiency is a non-linear function of the fit
parameters, so its distribution can be lopsided — mostly towards the ends of
the calibrated range and beyond them, where upper/lower ratios from 0.16 to
13.7 were measured.</p>
<p><strong>3. Robust to a few bad refits.</strong> A handful of Monte Carlo
refits that run away can inflate the standard deviation enormously while
barely moving the percentiles.</p>
<figure class="fig"><svg viewBox="0 0 680 250" role="img" aria-label="Histogram with a few runaway samples: standard deviation versus percentile width" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI, Helvetica, Arial, sans-serif"><rect x="148.5" y="199.9" width="7.1" height="0.1" fill="#888888" fill-opacity="0.45"/><rect x="179.5" y="199.9" width="7.2" height="0.1" fill="#888888" fill-opacity="0.45"/><rect x="202.8" y="199.9" width="7.2" height="0.1" fill="#888888" fill-opacity="0.45"/><rect x="210.5" y="199.5" width="7.2" height="0.5" fill="#888888" fill-opacity="0.45"/><rect x="218.3" y="199.6" width="7.2" height="0.4" fill="#888888" fill-opacity="0.45"/><rect x="226.0" y="199.0" width="7.1" height="1.0" fill="#888888" fill-opacity="0.45"/><rect x="233.8" y="198.7" width="7.2" height="1.3" fill="#888888" fill-opacity="0.45"/><rect x="241.5" y="198.1" width="7.2" height="1.9" fill="#888888" fill-opacity="0.45"/><rect x="249.2" y="195.2" width="7.2" height="4.8" fill="#888888" fill-opacity="0.45"/><rect x="257.0" y="193.0" width="7.2" height="7.0" fill="#888888" fill-opacity="0.45"/><rect x="264.8" y="187.3" width="7.2" height="12.7" fill="#888888" fill-opacity="0.45"/><rect x="272.5" y="184.9" width="7.2" height="15.1" fill="#888888" fill-opacity="0.45"/><rect x="280.2" y="176.5" width="7.2" height="23.5" fill="#888888" fill-opacity="0.45"/><rect x="288.0" y="166.8" width="7.2" height="33.2" fill="#888888" fill-opacity="0.45"/><rect x="295.8" y="157.1" width="7.2" height="42.9" fill="#888888" fill-opacity="0.45"/><rect x="303.5" y="142.3" width="7.2" height="57.7" fill="#888888" fill-opacity="0.45"/><rect x="311.2" y="135.1" width="7.2" height="64.9" fill="#888888" fill-opacity="0.45"/><rect x="319.0" y="122.9" width="7.2" height="77.1" fill="#888888" fill-opacity="0.45"/><rect x="326.8" y="115.7" width="7.2" height="84.3" fill="#888888" fill-opacity="0.45"/><rect x="334.5" y="98.5" width="7.2" height="101.5" fill="#888888" fill-opacity="0.45"/><rect x="342.2" y="101.9" width="7.2" height="98.1" fill="#888888" fill-opacity="0.45"/><rect x="350.0" y="97.1" width="7.2" height="102.9" fill="#888888" fill-opacity="0.45"/><rect x="357.8" y="106.0" width="7.1" height="94.0" fill="#888888" fill-opacity="0.45"/><rect x="365.5" y="117.3" width="7.2" height="82.7" fill="#888888" fill-opacity="0.45"/><rect x="373.2" y="122.7" width="7.2" height="77.3" fill="#888888" fill-opacity="0.45"/><rect x="381.0" y="134.1" width="7.2" height="65.9" fill="#888888" fill-opacity="0.45"/><rect x="388.8" y="143.3" width="7.2" height="56.7" fill="#888888" fill-opacity="0.45"/><rect x="396.5" y="160.9" width="7.1" height="39.1" fill="#888888" fill-opacity="0.45"/><rect x="404.2" y="168.1" width="7.2" height="31.9" fill="#888888" fill-opacity="0.45"/><rect x="412.0" y="179.1" width="7.1" height="20.9" fill="#888888" fill-opacity="0.45"/><rect x="419.8" y="184.2" width="7.2" height="15.8" fill="#888888" fill-opacity="0.45"/><rect x="427.5" y="189.1" width="7.2" height="10.9" fill="#888888" fill-opacity="0.45"/><rect x="435.3" y="192.3" width="7.1" height="7.7" fill="#888888" fill-opacity="0.45"/><rect x="443.0" y="196.0" width="7.2" height="4.0" fill="#888888" fill-opacity="0.45"/><rect x="450.8" y="197.6" width="7.1" height="2.4" fill="#888888" fill-opacity="0.45"/><rect x="458.5" y="198.6" width="7.2" height="1.4" fill="#888888" fill-opacity="0.45"/><rect x="466.2" y="199.4" width="7.2" height="0.6" fill="#888888" fill-opacity="0.45"/><rect x="474.0" y="199.6" width="7.1" height="0.4" fill="#888888" fill-opacity="0.45"/><rect x="481.8" y="199.9" width="7.2" height="0.1" fill="#888888" fill-opacity="0.45"/><rect x="489.5" y="199.7" width="7.1" height="0.3" fill="#888888" fill-opacity="0.45"/><rect x="505.0" y="199.9" width="7.2" height="0.1" fill="#888888" fill-opacity="0.45"/><rect x="520.5" y="199.9" width="7.2" height="0.1" fill="#888888" fill-opacity="0.45"/><rect x="559.2" y="199.9" width="7.2" height="0.1" fill="#888888" fill-opacity="0.45"/><rect x="567.0" y="199.9" width="7.2" height="0.1" fill="#888888" fill-opacity="0.45"/><rect x="582.5" y="199.9" width="7.2" height="0.1" fill="#888888" fill-opacity="0.45"/><rect x="613.5" y="199.9" width="7.2" height="0.1" fill="#888888" fill-opacity="0.45"/><rect x="621.2" y="199.7" width="7.2" height="0.3" fill="#888888" fill-opacity="0.45"/><line x1="310.4" y1="40.6" x2="388.8" y2="40.6" stroke="#0066cc" stroke-width="3"/><text paint-order="stroke" stroke="#fbfcfe" stroke-width="4" stroke-linejoin="round" x="396.8" y="44.6" font-size="12" fill="#0066cc">σ₆₈ from percentiles = 1.01</text><line x1="229.0" y1="71.4" x2="471.0" y2="71.4" stroke="#d9730d" stroke-width="3"/><text paint-order="stroke" stroke="#fbfcfe" stroke-width="4" stroke-linejoin="round" x="479.0" y="75.4" font-size="12" fill="#d9730d">standard deviation = 3.12</text><text paint-order="stroke" stroke="#fbfcfe" stroke-width="4" stroke-linejoin="round" x="656" y="135.2" font-size="11" text-anchor="end" fill="#888888">+ 84 runaway samples</text><text paint-order="stroke" stroke="#fbfcfe" stroke-width="4" stroke-linejoin="round" x="656" y="149.2" font-size="11" text-anchor="end" fill="#888888">beyond the frame</text><line x1="40" y1="200.0" x2="660" y2="200.0" stroke="#1a1a1a" stroke-width="1"/><line x1="117.5" y1="200.0" x2="117.5" y2="205.0" stroke="#1a1a1a"/><text paint-order="stroke" stroke="#fbfcfe" stroke-width="4" stroke-linejoin="round" x="117.5" y="218.0" font-size="12" text-anchor="middle" fill="#1a1a1a">−6</text><line x1="195.0" y1="200.0" x2="195.0" y2="205.0" stroke="#1a1a1a"/><text paint-order="stroke" stroke="#fbfcfe" stroke-width="4" stroke-linejoin="round" x="195.0" y="218.0" font-size="12" text-anchor="middle" fill="#1a1a1a">−4</text><line x1="272.5" y1="200.0" x2="272.5" y2="205.0" stroke="#1a1a1a"/><text paint-order="stroke" stroke="#fbfcfe" stroke-width="4" stroke-linejoin="round" x="272.5" y="218.0" font-size="12" text-anchor="middle" fill="#1a1a1a">−2</text><line x1="350.0" y1="200.0" x2="350.0" y2="205.0" stroke="#1a1a1a"/><text paint-order="stroke" stroke="#fbfcfe" stroke-width="4" stroke-linejoin="round" x="350.0" y="218.0" font-size="12" text-anchor="middle" fill="#1a1a1a">0</text><line x1="427.5" y1="200.0" x2="427.5" y2="205.0" stroke="#1a1a1a"/><text paint-order="stroke" stroke="#fbfcfe" stroke-width="4" stroke-linejoin="round" x="427.5" y="218.0" font-size="12" text-anchor="middle" fill="#1a1a1a">2</text><line x1="505.0" y1="200.0" x2="505.0" y2="205.0" stroke="#1a1a1a"/><text paint-order="stroke" stroke="#fbfcfe" stroke-width="4" stroke-linejoin="round" x="505.0" y="218.0" font-size="12" text-anchor="middle" fill="#1a1a1a">4</text><line x1="582.5" y1="200.0" x2="582.5" y2="205.0" stroke="#1a1a1a"/><text paint-order="stroke" stroke="#fbfcfe" stroke-width="4" stroke-linejoin="round" x="582.5" y="218.0" font-size="12" text-anchor="middle" fill="#1a1a1a">6</text><text paint-order="stroke" stroke="#fbfcfe" stroke-width="4" stroke-linejoin="round" x="350.0" y="242" font-size="12" text-anchor="middle" fill="#888888">10 000 samples, 1 % of them runaway: the standard deviation follows the outliers, σ₆₈ does not</text></svg>
<figcaption>Figure 4. 10 000 samples, 1 % of them runaway. The standard
deviation (orange, 3.12) is dragged out by the few outliers — 3.1× the
percentile width σ₆₈ (blue, 1.01), which still describes the bulk of the
distribution. Just beyond the calibration lines, CalEnEff's own Monte Carlo
showed the standard deviation at up to 4.8× σ₆₈ for this reason.</figcaption></figure>
<p><strong>4. Unchanged by monotonic transformations.</strong> Percentiles
pass through any monotonic function: the 84th percentile of ε is the
exponential of the 84th percentile of ln ε, and the same holds for energy
versus channel. A standard deviation does not, so a std-based interval
depends on which variable it happens to be computed in; a percentile
interval does not.</p>
<p><strong>5. One set of statistics for everything.</strong> The 50 % point
is the median used by the bias check, and the same three percentiles build
the band, the query and the export. Value, interval and check therefore all
come from one consistent set of numbers.</p>

<h3>How CalEnEff turns them into the reported 1σ</h3>
<div class='formula'>lower 1σ = B · (p50 − p16)
upper 1σ = B · (p84 − p50)
σ        = B · (p84 − p16) / 2        (symmetric summary; the export's Δε)</div>
<p>with B the model's Birge ratio, taken as 1 when it is below 1. The
interval is placed around the best fit, not around the median, so a small
offset between the two cannot move it (see the section above).</p>

<h3>The price</h3>
<p>From the same number of samples N, a width taken from percentiles is
noisier than a standard deviation. For a Gaussian the relative uncertainty
of σ₆₈ is about <span class="nb">0.96/<span class="sqrt"><span class="rs">√</span><span class="rad">N</span></span></span>, against <span class="nb">0.71/<span class="sqrt"><span class="rs">√</span><span class="rad">N</span></span></span> for the standard deviation.
With N = 10 000 that is about 1.0 % against 0.7 % — negligible next to the
rest of the uncertainty budget (the Birge factor alone is about 5 on the
bundled data).</p>
<div class='note'><strong>Energy queries</strong> still take their 1σ from
the standard deviation (the calibration share Birge-inflated, your Δch₀
added). That is harmless there: the channel-to-energy inversion is close to
linear and its distribution Gaussian, so the two widths agree, and the MC
median and mean differ by 0.0003 keV at channel 2000.</div>

<p>Reference: Tellinghuisen, J., "Statistical Error Propagation,"
<em>J. Phys. Chem. A</em> 105 (2001) 3917–3921.</p>

<!-- ── Chi-squared and ndf ────────────────────────────────────── -->
<h2>Chi-squared and degrees of freedom</h2>
<table>
  <tr><th>Calibration</th><th>Free parameters p</th><th>ndf = n − p</th></tr>
  <tr><td>Energy — Linear</td><td>2 (a, b)</td><td>n − 2</td></tr>
  <tr><td>Energy — Quadratic</td><td>3 (a, b, d)</td><td>n − 3</td></tr>
  <tr><td>Efficiency (CalEnEff)</td><td>4 (a, b, c, d)</td><td>n − 4</td></tr>
  <tr><td>Efficiency (Radware)</td><td>5 (A, B, D, E, F; C = 0, G = 15 fixed)</td><td>n − 5</td></tr>
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
your measurement, and take every line of one calibration from the
<em>same</em> evaluation: mixing them introduces few-percent inconsistencies
between lines. The tables below were checked line by line on 2026-09-24
against the IAEA recommended standards and, for nuclides or lines those
do not include, ENSDF via the
<a href="https://www-nds.iaea.org/relnsd/vcharthtml/VChartHTML.html">IAEA LiveChart</a>;
each table's source note says which rows were corrected.</p>

<h3>²²⁶Ra — T½ = 1 600 y — secular equilibrium with daughters</h3>
<p>Covers 53 keV – 2 448 keV with lines in equilibrium — a convenient
single-source calibration, <strong>provided three conditions hold</strong>.
In secular equilibrium the chain includes
<strong>²²²Rn → ²¹⁴Pb → ²¹⁴Bi</strong> as the dominant gamma emitters.</p>
<ul>
  <li><strong>Equilibrium.</strong> The 186 keV line is ²²⁶Ra itself; every
      other line is emitted after ²²²Rn (T½ 3.8 d). A source that is not
      gas-tight, or was sealed less than ~3 weeks before counting, holds
      fewer daughters than ²²⁶Ra, and the 186 keV point then sits above
      the curve fitted through the rest — check it, or leave it out.
      ²¹⁰Pb (46.5 keV, T½ 22.2 y) is not in equilibrium in any source
      younger than about a century.</li>
  <li><strong>True coincidence summing.</strong> ²¹⁴Bi decays through
      cascades: most lines are emitted together with the 609.3 keV
      transition and lose counts, while several (1377.7, 1729.6, 1764.5,
      1847.4, 2118.5 keV) also gain sum-peak counts from two-step cascades.
      Close to the detector both effects reach tens of percent, in opposite
      directions, and <strong>CalEnEff does not correct them</strong>. Count
      far enough away for them to be negligible (typically ≥ 10–25 cm,
      depending on detector size), or correct the peak areas with a
      dedicated code before fitting.</li>
  <li><strong>Interferences.</strong> The 186 keV line overlaps ²³⁵U at
      185.7 keV and should be excluded when measuring uranium-containing
      samples. Lines below ~100 keV are sensitive to source self-absorption
      and geometry, and the 74–90 keV region is crowded with Bi, Po and
      shielding Pb X-rays.</li>
</ul>
<table>
  <tr><th>Energy (keV)</th><th>Daughter</th><th>I (%)</th><th>Notes</th></tr>
  <tr><td>46.539</td>   <td>²¹⁰Pb</td><td>4.25</td>   <td>²¹⁰Pb (T½ 22.2 y) is NOT in equilibrium with ²²⁶Ra unless the source is ≳100 y old — do not use for efficiency without its own activity; self-absorption sensitive</td></tr>
  <tr><td>53.227</td>   <td>²¹⁴Pb</td><td>1.066</td>   <td>Weak; low-energy calibration only</td></tr>
  <tr><td>74.815</td>   <td>²¹⁴Pb (Bi Kα₂ X-ray)</td><td>5.22</td>   <td>X-ray, not a γ-ray; coincides with Pb Kα₁ (74.97 keV) fluorescence from lead shielding — avoid</td></tr>
  <tr><td>186.211</td>  <td>²²⁶Ra</td><td>3.533(28)</td><td>Overlaps ²³⁵U 185.7 keV — exclude for U samples</td></tr>
  <tr><td>241.997</td>  <td>²¹⁴Pb</td><td>7.19</td>   <td></td></tr>
  <tr><td>295.224</td>  <td>²¹⁴Pb</td><td>18.28</td>  <td></td></tr>
  <tr><td>351.932</td>  <td>²¹⁴Pb</td><td>35.34</td>  <td>Strongest ²¹⁴Pb line</td></tr>
  <tr><td>405.72</td>  <td>²¹⁴Bi</td><td>0.168</td>  <td>Very weak</td></tr>
  <tr><td>609.316</td>  <td>²¹⁴Bi</td><td>45.16</td>  <td>Strong, well-isolated; primary calibration line</td></tr>
  <tr><td>665.453</td>  <td>²¹⁴Bi</td><td>1.521</td>  <td></td></tr>
  <tr><td>768.367</td>  <td>²¹⁴Bi</td><td>4.85</td>  <td></td></tr>
  <tr><td>806.185</td>  <td>²¹⁴Bi</td><td>1.255</td>  <td></td></tr>
  <tr><td>934.061</td>  <td>²¹⁴Bi</td><td>3.074</td>  <td></td></tr>
  <tr><td>1120.287</td> <td>²¹⁴Bi</td><td>14.78</td>  <td></td></tr>
  <tr><td>1155.19</td> <td>²¹⁴Bi</td><td>1.624</td>  <td></td></tr>
  <tr><td>1238.11</td> <td>²¹⁴Bi</td><td>5.79</td>  <td></td></tr>
  <tr><td>1280.96</td> <td>²¹⁴Bi</td><td>1.425</td>  <td></td></tr>
  <tr><td>1377.669</td> <td>²¹⁴Bi</td><td>3.954</td>  <td></td></tr>
  <tr><td>1401.516</td> <td>²¹⁴Bi</td><td>1.324</td>  <td></td></tr>
  <tr><td>1407.993</td> <td>²¹⁴Bi</td><td>2.369</td>  <td></td></tr>
  <tr><td>1509.217</td> <td>²¹⁴Bi</td><td>2.108</td>  <td></td></tr>
  <tr><td>1661.316</td> <td>²¹⁴Bi</td><td>1.037</td>  <td></td></tr>
  <tr><td>1729.64</td> <td>²¹⁴Bi</td><td>2.817</td>  <td></td></tr>
  <tr><td>1764.539</td> <td>²¹⁴Bi</td><td>15.17</td>  <td>Second strongest ²¹⁴Bi line</td></tr>
  <tr><td>1847.42</td> <td>²¹⁴Bi</td><td>2.000</td>  <td></td></tr>
  <tr><td>2118.536</td> <td>²¹⁴Bi</td><td>1.148</td>  <td></td></tr>
  <tr><td>2204.071</td> <td>²¹⁴Bi</td><td>4.89</td>  <td></td></tr>
  <tr><td>2447.673</td> <td>²¹⁴Bi</td><td>1.536</td>  <td>Highest-energy usable line</td></tr>
</table>
<p>Source: <a href="https://www-nds.iaea.org/xgamma_standards/">IAEA recommended
decay data standards for detector calibration</a> — the same values as the
example dataset <code>226Ra_En_Area.txt</code>; the 46.5, 74.8 and 405.7 keV
rows, which that set does not include, from ENSDF. All rows harmonised
2026-09-24: the previous table mixed evaluations, listed a Bi X-ray as a
0.25% ²¹⁴Pb γ-ray (it is 5.22%), and gave 405.7 keV the nuclide and
intensity of a different line.</p>

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
  <tr><td>563.986</td><td>0.494(5)</td><td>Very weak</td></tr>
  <tr><td>586.265</td><td>0.458(4)</td><td>Weak</td></tr>
  <tr><td>678.623</td><td>0.473(4)</td><td>Weak</td></tr>
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
<p>Source: <a href="http://www.lnhb.fr/nuclides/Eu-152_tables.pdf">LNHB Eu-152 tables</a>;
563.986 keV (listed at 0.102%, really 0.494%) and 678.623 keV corrected from
ENSDF, 2026-09-24.</p>

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
  <tr><td>223.237</td><td>0.4530(34)</td><td>Weak</td></tr>
  <tr><td>276.404</td><td>7.16(5)</td> <td></td></tr>
  <tr><td>302.851</td><td>18.34(13)</td><td></td></tr>
  <tr><td>356.013</td><td>62.05(19)</td><td>Strongest line; primary calibration point</td></tr>
  <tr><td>383.849</td><td>8.94(6)</td> <td></td></tr>
</table>
<p>Source: <a href="http://www.lnhb.fr/nuclides/Ba-133_tables.pdf">LNHB Ba-133 tables</a>;
302.9, 356.0 and 383.8 keV from the IAEA recommended standards and the
223.2 keV energy from ENSDF, 2026-09-24 — the previous values were an older,
2–4% higher evaluation.</p>

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
  <tr><td>31.738</td>  <td>0.874</td><td>Very weak; X-ray region</td></tr>
  <tr><td>65.722</td>  <td>3.013</td> <td></td></tr>
  <tr><td>67.75</td>  <td>42.4</td> <td>Strongest low-energy line</td></tr>
  <tr><td>84.68</td>  <td>2.654</td> <td></td></tr>
  <tr><td>100.11</td> <td>14.2</td> <td></td></tr>
  <tr><td>113.672</td> <td>1.871</td> <td></td></tr>
  <tr><td>116.418</td> <td>0.444</td> <td>Weak</td></tr>
  <tr><td>152.43</td> <td>7.0</td>  <td></td></tr>
  <tr><td>156.386</td> <td>2.671</td> <td></td></tr>
  <tr><td>179.39</td> <td>~3.1</td> <td></td></tr>
  <tr><td>198.352</td> <td>1.465</td> <td></td></tr>
  <tr><td>222.11</td> <td>~7.5</td> <td></td></tr>
  <tr><td>229.32</td> <td>~3.6</td> <td></td></tr>
  <tr><td>264.074</td> <td>3.612</td> <td></td></tr>
  <tr><td>1121.29</td><td>35.24</td><td>Strong; high-energy anchor</td></tr>
  <tr><td>1189.05</td><td>16.5</td> <td></td></tr>
  <tr><td>1221.39</td><td>27.14</td><td></td></tr>
  <tr><td>1231.02</td><td>11.46</td><td></td></tr>
</table>
<div class='note'>Values marked "~" are approximate; verify against
<a href="https://www.nndc.bnl.gov/nudat3/">NNDC NuDat 3</a> for
publication-quality data. T½ makes Ta-182 suitable for measurements
spanning several weeks.</div>
<p>Source: ENSDF, via <a href="https://www.nndc.bnl.gov/nudat3/">NNDC NuDat 3</a>
and the IAEA LiveChart. Eight intensities corrected 2026-09-24 (113.67 keV was
listed at 3.5%, really 1.87%), and a 1100.44 keV line that does not exist
removed.</p>

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
  <tr><td>26.345</td><td>2.400</td> <td>Np L X-ray region; geometry sensitive</td></tr>
  <tr><td>33.196</td><td>0.126</td><td>Very weak</td></tr>
  <tr><td>43.420</td><td>0.073</td><td>Very weak</td></tr>
  <tr><td>59.537</td><td>35.92</td><td>Primary calibration line</td></tr>
</table>
<p>Source: <a href="https://www.lnhb.fr/nuclides/Am-241_tables.pdf">LNHB Am-241 tables</a>;
<a href="https://www.nndc.bnl.gov/nudat3/">NNDC NuDat 3</a>; 26.345 keV from the
IAEA recommended standards, 2026-09-24.</p>

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
  <tr><td>61.46</td> <td>²³⁹Np</td><td>1.300</td><td>Weak</td></tr>
  <tr><td>74.660</td><td>²⁴³Am</td><td>67.2</td><td>Strongest Am-243 line</td></tr>
  <tr><td>86.710</td><td>²³⁹Np</td><td>0.346</td><td></td></tr>
  <tr><td>106.12</td><td>²⁴³Am+²³⁹Np</td><td>~25</td><td>Blend; use with care</td></tr>
  <tr><td>209.753</td><td>²³⁹Np</td><td>3.363</td><td></td></tr>
  <tr><td>228.183</td><td>²³⁹Np</td><td>10.73</td><td></td></tr>
  <tr><td>277.60</td><td>²³⁹Np</td><td>14.3</td><td></td></tr>
  <tr><td>334.31</td><td>²³⁹Np</td><td>2.056</td><td>Very weak</td></tr>
</table>
<p>Source: <a href="https://www.nndc.bnl.gov/nudat3/">NNDC NuDat 3</a>;
<a href="https://nds.iaea.org/xgamma_standards/">IAEA NDS xgamma standards</a>.
Corrected 2026-09-24 against those and ENSDF: 74.66 keV (was 57%, really
67.2%), 334.31 keV (was 0.023%, really 2.06%) and four other rows; the
86.50, 144.62 and 174.01 keV rows named lines that do not exist — the first
is now the real 86.71 keV line, the other two are removed.</p>

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
  <tr><td>3009.559</td><td>1.038</td> <td>Weak</td></tr>
  <tr><td>3201.930</td><td>3.203</td> <td></td></tr>
  <tr><td>3253.402</td><td>7.870</td> <td></td></tr>
  <tr><td>3272.984</td><td>1.86</td> <td></td></tr>
  <tr><td>3451.119</td><td>0.94</td> <td>Highest usable line</td></tr>
</table>
<p>Source: <a href="https://www.lnhb.fr/nuclides/Co-56_tables.pdf">LNHB Co-56 tables</a>;
<a href="https://www.nndc.bnl.gov/nudat3/">NNDC NuDat 3</a>. 3009.6, 3201.9 and
3253.4 keV intensities from the IAEA recommended standards, 2026-09-24, and a
3369.99 keV row listed at 0.62% removed — that line is 0.010%.</p>

<h3>⁷⁵Se — T½ = 119.78 d</h3>
<p>Selenium-75 provides 9 lines from 66 to 401 keV, covering the
critical 100–300 keV region with high-intensity lines at 136 keV (58.8%)
and 264.7 keV (59.4%) — both nearly equal in intensity, which makes
Se-75 self-consistent for efficiency shape validation.
The 279.5 keV line (25.2%) is a useful cross-check point.</p>
<table>
  <tr><th>Energy (keV)</th><th>I (%)</th><th>Notes</th></tr>
  <tr><td>66.052</td><td>1.112</td> <td>Weak; low-energy region</td></tr>
  <tr><td>96.734</td><td>3.40</td> <td></td></tr>
  <tr><td>121.115</td><td>17.32</td><td></td></tr>
  <tr><td>136.000</td><td>58.76</td><td>Primary anchor</td></tr>
  <tr><td>198.606</td><td>1.48</td> <td>Weak</td></tr>
  <tr><td>264.658</td><td>59.35</td><td>Co-equal with 136 keV; useful self-check</td></tr>
  <tr><td>279.542</td><td>25.16</td><td></td></tr>
  <tr><td>303.924</td><td>1.31</td> <td>Weak</td></tr>
  <tr><td>400.657</td><td>11.53</td><td></td></tr>
</table>
<p>Source: <a href="https://www.nndc.bnl.gov/nudat3/">NNDC NuDat 3</a>;
<a href="https://nds.iaea.org/xgamma_standards/">IAEA NDS xgamma standards</a>;
66.05 and 198.61 keV corrected from the latter, 2026-09-24 (both were ~10%
low).</p>

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
