/* RailGuard AI - passenger interface */
const $ = id => document.getElementById(id);

const I18N = {
  en: {
    logoSub: 'Platform Risk & Guidance',
    heroTitle: 'Smart Platform Verification & Risk Assistance',
    heroSubtitle: 'Verify your platform, estimate transit risk, and receive walking guidance to catch your train on time.',
    quickTitle: '⚡ Quick Test Scenarios:',
    formTitle: 'Check Train & Platform Status',
    lblTrain: 'Train Number or Name:', helpTrain: 'Start typing - matching trains appear. Pick one from the list.',
    lblStation: 'Your Station:', lblPlatform: 'Your Current Platform:',
    btnText: 'Verify Platform & Analyze Risk', checking: '⏳ Checking...',
    lblAssignedPlat: 'Assigned Platform', lblYourPlat: 'Your Current Platform',
    lblTimeRem: 'Time Until Departure', lblRiskLevel: 'Miss Risk Level',
    analysisTitle: 'Risk & Transit Analysis', guidanceTitle: 'Step-by-Step Walking Guidance',
    min: 'min', walk: 'Walk', crowd: 'Platform crowd', crowded: 'Crowded', clear: 'Clear', gap: 'Platform gap', analysis: 'Analysis',
    risk: {Low: 'LOW', Medium: 'MEDIUM', High: 'HIGH'},
    disclaimer: 'ℹ️ <strong>Academic Prototype Note:</strong> Platform information is based on scheduled database records. Always cross-check with official station audio announcements and display boards.',
    errTitle: 'Something went wrong.', errHint: 'Try one of the quick test buttons above to see a verified sample train.',
    network: 'Could not reach the server.',
    footer: '&copy; 2026 RailGuard AI | B.Tech AI/ML Project'
  },
  hi: {
    logoSub: 'प्लेटफॉर्म जोखिम और मार्गदर्शन',
    heroTitle: 'स्मार्ट प्लेटफॉर्म सत्यापन और जोखिम सहायता',
    heroSubtitle: 'अपना प्लेटफॉर्म जांचें, जोखिम का अनुमान लगाएं और समय पर ट्रेन पकड़ने के लिए मार्गदर्शन पाएं।',
    quickTitle: '⚡ त्वरित परीक्षण:',
    formTitle: 'ट्रेन और प्लेटफॉर्म की स्थिति जांचें',
    lblTrain: 'ट्रेन नंबर या नाम:', helpTrain: 'टाइप करना शुरू करें - मिलती-जुलती ट्रेनें दिखेंगी। सूची से चुनें।',
    lblStation: 'आपका स्टेशन:', lblPlatform: 'आपका वर्तमान प्लेटफॉर्म:',
    btnText: 'प्लेटफॉर्म जांचें और जोखिम देखें', checking: '⏳ जांच हो रही है...',
    lblAssignedPlat: 'निर्धारित प्लेटफॉर्म', lblYourPlat: 'आपका वर्तमान प्लेटफॉर्म',
    lblTimeRem: 'प्रस्थान में शेष समय', lblRiskLevel: 'ट्रेन छूटने का जोखिम',
    analysisTitle: 'जोखिम और यात्रा विश्लेषण', guidanceTitle: 'चरण-दर-चरण पैदल मार्गदर्शन',
    min: 'मिनट', walk: 'पैदल', crowd: 'प्लेटफॉर्म भीड़', crowded: 'भीड़भाड़', clear: 'खाली', gap: 'प्लेटफॉर्म अंतर', analysis: 'विश्लेषण',
    risk: {Low: 'कम', Medium: 'मध्यम', High: 'उच्च'},
    disclaimer: 'ℹ️ <strong>नोट:</strong> प्लेटफॉर्म की जानकारी निर्धारित डेटाबेस रिकॉर्ड पर आधारित है। हमेशा स्टेशन की आधिकारिक घोषणाओं और डिस्प्ले बोर्ड से मिलान करें।',
    errTitle: 'कुछ गड़बड़ हो गई।', errHint: 'ऊपर दिए गए त्वरित परीक्षण बटन आज़माएं।',
    network: 'सर्वर से संपर्क नहीं हो सका।',
    footer: '&copy; 2026 RailGuard AI | B.Tech AI/ML प्रोजेक्ट'
  },
  mr: {
    logoSub: 'प्लॅटफॉर्म धोका आणि मार्गदर्शन',
    heroTitle: 'स्मार्ट प्लॅटफॉर्म पडताळणी आणि धोका सहाय्य',
    heroSubtitle: 'तुमचा प्लॅटफॉर्म तपासा, धोका जाणून घ्या आणि वेळेत गाडी पकडण्यासाठी मार्गदर्शन मिळवा.',
    quickTitle: '⚡ जलद चाचणी:',
    formTitle: 'गाडी आणि प्लॅटफॉर्म स्थिती तपासा',
    lblTrain: 'गाडी क्रमांक किंवा नाव:', helpTrain: 'टाइप करायला सुरुवात करा - जुळणाऱ्या गाड्या दिसतील. यादीतून निवडा.',
    lblStation: 'तुमचे स्टेशन:', lblPlatform: 'तुमचा सध्याचा प्लॅटफॉर्म:',
    btnText: 'प्लॅटफॉर्म तपासा आणि धोका पहा', checking: '⏳ तपासत आहे...',
    lblAssignedPlat: 'नियुक्त प्लॅटफॉर्म', lblYourPlat: 'तुमचा सध्याचा प्लॅटफॉर्म',
    lblTimeRem: 'सुटण्यास उरलेला वेळ', lblRiskLevel: 'गाडी चुकण्याचा धोका',
    analysisTitle: 'धोका आणि प्रवास विश्लेषण', guidanceTitle: 'टप्प्याटप्प्याने चालण्याचे मार्गदर्शन',
    min: 'मिनिटे', walk: 'चालणे', crowd: 'प्लॅटफॉर्म गर्दी', crowded: 'गर्दी', clear: 'मोकळा', gap: 'प्लॅटफॉर्म अंतर', analysis: 'विश्लेषण',
    risk: {Low: 'कमी', Medium: 'मध्यम', High: 'जास्त'},
    disclaimer: 'ℹ️ <strong>टीप:</strong> प्लॅटफॉर्मची माहिती नियोजित डेटाबेस नोंदींवर आधारित आहे. नेहमी स्टेशनवरील अधिकृत घोषणा आणि डिस्प्ले बोर्डशी पडताळणी करा.',
    errTitle: 'काहीतरी चुकले.', errHint: 'वरील जलद चाचणी बटणे वापरून पहा.',
    network: 'सर्व्हरशी संपर्क होऊ शकला नाही.',
    footer: '&copy; 2026 RailGuard AI | B.Tech AI/ML प्रकल्प'
  }
};

let lang = 'en';
let lastResult = null;
let stopsLoadedFor = '';

function applyLanguage() {
  const t = I18N[lang];
  const text = {logoSub:'logoSub', heroTitle:'heroTitle', heroSubtitle:'heroSubtitle', quickTitle:'quickTitle',
    formTitle:'formTitle', lblTrain:'lblTrain', helpTrain:'helpTrain', lblStation:'lblStation',
    lblPlatform:'lblPlatform', btnText:'btnText', lblAssignedPlat:'lblAssignedPlat', lblYourPlat:'lblYourPlat',
    lblTimeRem:'lblTimeRem', lblRiskLevel:'lblRiskLevel', analysisTitle:'analysisTitle', guidanceTitle:'guidanceTitle'};
  for (const [id, key] of Object.entries(text)) if ($(id)) $(id).textContent = t[key];
  $('disclaimerText').innerHTML = t.disclaimer;
  $('footerText').innerHTML = t.footer;
  document.documentElement.lang = lang;
}

/* ---------- Searchable train dropdown (works with thousands of trains) ---------- */
let acItems = [], acActive = -1, acTimer = null, acSeq = 0;

function esc(t) { const d = document.createElement('div'); d.textContent = t; return d.innerHTML; }

function closeDropdown() {
  $('trainDropdown').style.display = 'none';
  $('trainInput').setAttribute('aria-expanded', 'false');
  acActive = -1;
}

function highlight(i) {
  [...$('trainDropdown').children].forEach((li, n) => li.classList.toggle('active', n === i));
  acActive = i;
  const el = $('trainDropdown').children[i];
  if (el) el.scrollIntoView({block: 'nearest'});
}

function pickTrain(t) {
  $('trainInput').value = `${t.train_number} - ${t.train_name}`;
  $('trainNumber').value = t.train_number;
  closeDropdown();
  stopsLoadedFor = '';
  $('stationInput').value = '';
  loadStops();
  $('stationInput').focus();
}

async function searchTrains(q) {
  const seq = ++acSeq;
  try {
    const list = await (await fetch('/api/search-trains?q=' + encodeURIComponent(q))).json();
    if (seq !== acSeq) return;                 // a newer search already replaced this one
    acItems = list;
    const dd = $('trainDropdown');
    dd.innerHTML = '';
    if (!list.length) {
      const li = document.createElement('li'); li.className = 'ac-empty';
      li.textContent = 'No matching train'; dd.appendChild(li);
    }
    list.forEach((t, i) => {
      const li = document.createElement('li');
      li.setAttribute('role', 'option');
      li.innerHTML = `<strong>${esc(t.train_number)}</strong> ${esc(t.train_name)}<small>${esc(t.source)} → ${esc(t.dest)}</small>`;
      li.addEventListener('mousedown', e => { e.preventDefault(); pickTrain(t); });
      dd.appendChild(li);
    });
    dd.style.display = 'block';
    $('trainInput').setAttribute('aria-expanded', 'true');
    acActive = -1;
  } catch (e) { /* suggestions are optional */ }
}

function onTrainTyping() {
  $('trainNumber').value = '';                 // typed by hand -> not a confirmed pick yet
  stopsLoadedFor = '';
  clearTimeout(acTimer);
  const q = $('trainInput').value.trim();
  acTimer = setTimeout(() => searchTrains(q), 200);   // debounce: one request per pause
  if (/^\d{4,5}$/.test(q)) loadStops();
}

function trainKeys(e) {
  const dd = $('trainDropdown');
  if (dd.style.display === 'none') return;
  if (e.key === 'ArrowDown') { e.preventDefault(); highlight(Math.min(acActive + 1, acItems.length - 1)); }
  else if (e.key === 'ArrowUp') { e.preventDefault(); highlight(Math.max(acActive - 1, 0)); }
  else if (e.key === 'Enter' && acActive >= 0) { e.preventDefault(); pickTrain(acItems[acActive]); }
  else if (e.key === 'Escape') closeDropdown();
}

async function loadStops() {
  const num = ($('trainNumber').value || $('trainInput').value).trim();
  if (!/^\d{3,6}$/.test(num) || num === stopsLoadedFor) return;
  stopsLoadedFor = num;
  try {
    const stops = await (await fetch('/api/train-stops/' + encodeURIComponent(num))).json();
    $('stationList').innerHTML = stops.map(s =>
      `<option value="${s.station}">${s.station} - departs ${s.departure_time}</option>`).join('');
    if (stops.length === 1) $('stationInput').value = stops[0].station;
  } catch (e) { /* ignore */ }
}

/* ---------- Quick test chips ---------- */
function fillQuickTest(train, station, platform, minutes) {
  $('trainInput').value = train;
  $('trainNumber').value = train;
  closeDropdown();
  stopsLoadedFor = '';
  loadStops();
  $('stationInput').value = station;
  $('platformInput').value = platform;
  $('minutesOverride').value = minutes || '';
  $('checkForm').requestSubmit();
}
window.fillQuickTest = fillQuickTest;

/* ---------- Rendering ---------- */
function showError(msg) {
  $('resultCard').style.display = 'none';
  $('errorMessage').textContent = msg || I18N[lang].errTitle;
  $('errorHint').textContent = I18N[lang].errHint;
  $('errorCard').style.display = 'flex';
}

function render(d) {
  const t = I18N[lang];
  $('errorCard').style.display = 'none';

  const banner = $('mismatchBanner');
  banner.className = 'alert-banner ' + (d.is_match ? 'success' : 'danger');
  banner.innerHTML = '';
  const head = document.createElement('div');
  head.textContent = (d.is_match ? '✅ ' : '⚠️ ') + d.alert;
  const sub = document.createElement('small');
  sub.textContent = `${d.train_number} · ${d.train_name} | ${d.source_station} → ${d.destination_station} | ${d.station}`;
  banner.append(head, sub);

  $('valAssignedPlat').textContent = d.assigned_platform;
  $('valYourPlat').textContent = d.current_platform;
  $('valTimeRem').textContent = `${d.minutes_remaining} ${t.min} (${d.departure_time})`;

  const badge = $('valRiskBadge');
  badge.textContent = t.risk[d.risk_level] || d.risk_level;
  badge.className = 'badge ' + d.risk_level.toLowerCase();
  $('analysisBox').className = 'analysis-box risk-' + d.risk_level.toLowerCase();
  $('analysisSummary').textContent = d.risk_summary;

  const factors = [
    `${t.gap}: ${d.platform_gap}`,
    `${t.walk}: ~${d.estimated_walk_minutes} ${t.min}`,
    `${t.crowd}: ${d.crowd_level === 'High' ? t.crowded : t.clear}`,
    `${t.analysis}: ${d.model_used}`
  ];
  $('factorsList').innerHTML = factors.map(f => `<span class="factor"></span>`).join('');
  [...$('factorsList').children].forEach((el, i) => { el.textContent = factors[i]; });

  const ol = document.createElement('ol');
  d.guidance.forEach(step => { const li = document.createElement('li'); li.textContent = step; ol.appendChild(li); });
  $('guidanceContent').innerHTML = '';
  $('guidanceContent').appendChild(ol);

  $('resultCard').style.display = 'block';
  $('resultCard').scrollIntoView({behavior: 'smooth', block: 'start'});
}

async function submitCheck() {
  const btnText = $('btnText'), spin = $('btnSpinner');
  $('btnSubmit').disabled = true; btnText.style.display = 'none';
  spin.textContent = I18N[lang].checking; spin.style.display = 'inline';
  try {
    const res = await fetch('/api/check-platform', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        train: ($('trainNumber').value || $('trainInput').value).trim(),
        station: $('stationInput').value.trim(),
        current_platform: $('platformInput').value,
        language: lang,
        minutes_override: $('minutesOverride').value
      })
    });
    const d = await res.json();
    if (!d.success) { lastResult = null; showError(d.error); return; }
    lastResult = d; render(d);
  } catch (e) {
    showError(I18N[lang].network);
  } finally {
    $('btnSubmit').disabled = false; spin.style.display = 'none'; btnText.style.display = 'inline';
  }
}

document.addEventListener('DOMContentLoaded', () => {
  applyLanguage();
  $('checkForm').addEventListener('submit', e => { e.preventDefault(); submitCheck(); });
  $('trainInput').addEventListener('input', onTrainTyping);
  $('trainInput').addEventListener('focus', () => searchTrains($('trainInput').value.trim()));
  $('trainInput').addEventListener('keydown', trainKeys);
  $('trainInput').addEventListener('blur', () => setTimeout(closeDropdown, 150));
  document.addEventListener('click', e => { if (!e.target.closest('.ac-wrap')) closeDropdown(); });
  // typing manually cancels the demo-minutes override from the quick-test chip
  ['stationInput', 'platformInput', 'trainInput'].forEach(id =>
    $(id).addEventListener('input', () => { $('minutesOverride').value = ''; }));
  $('langSelect').addEventListener('change', e => {
    lang = e.target.value; applyLanguage();
    if (lastResult) submitCheck();   // re-fetch so the server text matches the language
  });
});
