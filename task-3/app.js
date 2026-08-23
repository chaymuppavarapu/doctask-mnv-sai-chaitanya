const DEFAULT_DATA = [
[{"use_case": "Multilingual help-center article maintenance", "real_companies": "Zendesk", "document_workflow": "Create and maintain translated Help Center articles, including translated sections/categories and ongoing article updates.", "recurring_problem": "When the source article changes, the knowledge team must keep its localized versions, parent structure, and language-specific content aligned.", "evidence_basis": "Zendesk's official documentation describes adding translated articles, translating parent sections/categories, and establishing an ongoing localization process for new and updated Help Center content.", "buyer_role": "Knowledge Management / Support Content Lead", "why_it_bites": "Stale support content creates inconsistent answers across locales and makes every product/content release a localization follow-up task.", "where_they_listen": "Knowledge-management communities, customer-support operations communities, Zendesk ecosystem, documentation/content events", "conversation_opener": "When a source Help Center article changes, how do you identify every locale that now needs review and republish?", "source_url": "https://support.zendesk.com/hc/en-us/articles/4408834328090-Localizing-help-center-content"}, {"use_case": "Localized developer documentation with continuous sync", "real_companies": "GitBook", "document_workflow": "Maintain translated documentation spaces/variants and synchronize translated pages when source documentation changes.", "recurring_problem": "Documentation teams need translated versions to preserve structure and remain current without manually reprocessing every page after each source change.", "evidence_basis": "GitBook officially documents translation spaces, automatic translation, and continuous updates where the translation workflow runs only for changed source pages.", "buyer_role": "Documentation / Developer Education Lead", "why_it_bites": "Release-driven documentation changes can leave localized docs behind, especially when teams must protect code, commands, formatting, and terminology.", "where_they_listen": "Documentation communities, developer-education teams, GitBook ecosystem, developer communities", "conversation_opener": "When a docs release changes 20 source pages, how do you know exactly which localized pages need retranslation?", "source_url": "https://gitbook.com/docs/creating-content/translations"}, {"use_case": "Programmatic HTML localization", "real_companies": "Cloudflare", "document_workflow": "Localize a rendered website by parsing and rewriting HTML while dynamically transforming page content for the visitor's locale.", "recurring_problem": "Localization logic must modify textual content without breaking HTML structure, selectors, attributes, or page behavior.", "evidence_basis": "Cloudflare's official tutorial demonstrates an internationalization/localization engine using HTMLRewriter to parse and rewrite HTML on the edge.", "buyer_role": "Web Platform / Developer Experience Lead", "why_it_bites": "A translation layer that treats HTML as plain text can break structure or require fragile per-page code.", "where_they_listen": "Web-platform engineering communities, Cloudflare developer community, edge/serverless events", "conversation_opener": "How are you protecting HTML structure and page behavior when localization happens programmatically?", "source_url": "https://developers.cloudflare.com/pages/tutorials/localize-a-website/"}, {"use_case": "API-localized structured content", "real_companies": "Stripe", "document_workflow": "Provide localized strings for API-supported content by exporting translatable fields, translating them, and serving the appropriate localized copy.", "recurring_problem": "Structured API content needs translation assets to stay synchronized with the application's source content and locale-selection logic.", "evidence_basis": "Stripe's official localization documentation describes XLIFF export, translation of target languages, and a localization API shape containing localization keys and translated content.", "buyer_role": "Platform / Developer Documentation Lead", "why_it_bites": "Manual translation operations around structured API fields create another content system that must remain consistent with product releases.", "where_they_listen": "API documentation communities, developer relations teams, platform engineering communities", "conversation_opener": "Where does the translation lifecycle live today for structured strings that are exposed through your APIs?", "source_url": "https://docs.stripe.com/localization"}, {"use_case": "Commerce translation maintenance and stale-content detection", "real_companies": "Shopify", "document_workflow": "Export, review, update, and import translations for products, articles, pages, themes, checkout, and other translatable resources.", "recurring_problem": "Source changes can make existing translations outdated, requiring teams to identify stale content and retranslate it.", "evidence_basis": "Shopify's official documentation defines translated/outdated/untranslated statuses and provides an export workflow specifically for outdated translations; Translate & Adapt can also retranslate out-of-sync content.", "buyer_role": "Localization / Content Operations Lead", "why_it_bites": "Catalog and storefront changes happen continuously, so translation debt can accumulate across many content types and markets.", "where_they_listen": "Commerce operations communities, Shopify ecosystem, localization communities, international-growth events", "conversation_opener": "How do you find every translated product or content field that became stale after a source update?", "source_url": "https://help.shopify.com/en/manual/markets/languages/manage-languages"}, {"use_case": "Technical localization QA and release pipelines", "real_companies": "GitLab", "document_workflow": "Generate translations, process Markdown, run QA on localized documentation, manage translation requests, and test localized documentation in pipelines.", "recurring_problem": "Translated technical documentation can introduce broken formatting, links, redirects, shortcodes, or terminology issues that must be caught before release.", "evidence_basis": "GitLab's official handbook documents AI translation generation, Markdown processing, QA, translation request management, localized release pipelines, and automated quality checks.", "buyer_role": "Technical Documentation / Localization Engineering Lead", "why_it_bites": "Localization QA is coupled to documentation engineering and release management; failures can reach production if checks are inconsistent.", "where_they_listen": "Documentation engineering communities, GitLab community, localization-engineering teams, technical-writing events", "conversation_opener": "Which localization defects are your current QA pipeline best at catching, and which still require human review?", "source_url": "https://handbook.gitlab.com/handbook/marketing/localization/tech_docs_localization/"}, {"use_case": "Locale-specific verification template operations", "real_companies": "Twilio", "document_workflow": "Resolve verification-message locale from the recipient's country/locale, maintain translated template variants, and fall back when a translation is unavailable.", "recurring_problem": "Each supported locale adds another template variant whose content, approval state, and fallback behavior must remain correct.", "evidence_basis": "Twilio's official Verify documentation describes locale resolution, translated template properties, custom-template translations, supported languages, and fallback behavior.", "buyer_role": "Messaging / Developer Content Operations Lead", "why_it_bites": "A wrong or stale localized verification message is customer-facing and can affect clarity, delivery behavior, and operational consistency.", "where_they_listen": "Messaging developer communities, Twilio ecosystem, developer-relations teams, communications engineering events", "conversation_opener": "How do you audit translated verification templates when a product team changes the source message?", "source_url": "https://www.twilio.com/docs/verify/supported-languages"}, {"use_case": "Locale fallback and multilingual product-surface consistency", "real_companies": "Atlassian", "document_workflow": "Support multiple product/account languages and provide locale fallback when the preferred language is unavailable.", "recurring_problem": "Internationalized products need consistent language availability and predictable fallback behavior across supported surfaces.", "evidence_basis": "Atlassian's official language-preferences documentation lists supported languages and documents locale fallback when the preferred language is not available.", "buyer_role": "Internationalization / Product Documentation Lead", "why_it_bites": "Locale gaps are user-visible and can create inconsistent experiences when different surfaces support different language sets.", "where_they_listen": "Atlassian community, product internationalization communities, developer/product events", "conversation_opener": "When a locale is missing or partially supported, how do you track where fallback content is still being shown?", "source_url": "https://support.atlassian.com/atlassian-account/docs/manage-your-language-preferences/"}, {"use_case": "Reusable translated content-block maintenance", "real_companies": "Zendesk", "document_workflow": "Reuse content blocks inside translated Help Center articles while maintaining the translated block content separately.", "recurring_problem": "A reusable block can appear in multiple translated articles, but its translated version still needs deliberate maintenance when the source wording changes.", "evidence_basis": "Zendesk's official documentation states that content blocks can be used in translated articles and explains that translated blocks are maintained in the translated language.", "buyer_role": "Knowledge Operations Lead", "why_it_bites": "A single reusable block can create many hidden localization dependencies, making updates easy to miss.", "where_they_listen": "Support operations communities, knowledge-management teams, Zendesk ecosystem", "conversation_opener": "If a reusable support block changes today, how do you identify every locale that needs its translated block reviewed?", "source_url": "https://support.zendesk.com/hc/en-us/articles/4486473049370-Using-content-blocks-in-translated-articles"}, {"use_case": "Public-article translation coverage and status", "real_companies": "Intercom", "document_workflow": "Create translated public articles, publish them by language, and monitor whether each translation is published or missing/unpublished.", "recurring_problem": "Knowledge teams need to detect missing or unpublished translations so customers do not encounter gaps in multilingual self-service coverage.", "evidence_basis": "Intercom's official documentation describes multilingual public articles and explicit translation-status states, including published versus missing/unpublished translations.", "buyer_role": "Knowledge Operations / Support Content Lead", "why_it_bites": "Translation gaps can silently reduce self-service coverage for specific customer-language segments.", "where_they_listen": "Support-content communities, Intercom ecosystem, knowledge-management and customer-experience events", "conversation_opener": "How do you prioritize missing or unpublished translations before customers encounter a language coverage gap?", "source_url": "https://www.intercom.com/help/en/articles/3107405-add-translations-to-public-articles"}]
];

const state = { data: DEFAULT_DATA, filtered: [], selected: null };

const $ = (id) => document.getElementById(id);

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, ch => ({
    "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"
  }[ch]));
}
function splitCompanies(value) {
  return String(value || "").split(";").map(x => x.trim()).filter(Boolean);
}
function companyChips(value) {
  return splitCompanies(value).map(c => `<span class="company-chip">${escapeHtml(c)}</span>`).join("");
}
function normalize(row) {
  const keys = [
    "use_case","real_companies","document_workflow","recurring_problem",
    "evidence_basis","buyer_role","why_it_bites","where_they_listen",
    "conversation_opener","source_url"
  ];
  const out = {};
  keys.forEach(k => out[k] = row[k] ?? "");
  return out;
}
function populateBuyerFilter(data) {
  const select = $("buyerFilter");
  const current = select.value;
  const roles = [...new Set(data.map(x => x.buyer_role).filter(Boolean))].sort();
  select.innerHTML = `<option value="">All buyer roles</option>` +
    roles.map(r => `<option value="${escapeHtml(r)}">${escapeHtml(r)}</option>`).join("");
  if (roles.includes(current)) select.value = current;
}
function renderStats(data) {
  const companies = new Set();
  const buyers = new Set();
  data.forEach(row => {
    splitCompanies(row.real_companies).forEach(c => companies.add(c));
    if (row.buyer_role) buyers.add(row.buyer_role);
  });
  $("stats").innerHTML = [
    ["Use cases", data.length, "research rows"],
    ["Companies", companies.size, "individually evidenced"],
    ["Buyer roles", buyers.size, "distinct personas"],
    ["Evidence", data.filter(x => x.source_url).length, "official source links"]
  ].map(([label,value,sub]) => `<div class="stat"><div class="stat-value">${value}</div><div class="stat-label">${label}</div><div class="stat-sub">${sub}</div></div>`).join("");
  $("heroCount").textContent = data.length;
}
function getFiltered() {
  const q = $("searchInput").value.trim().toLowerCase();
  const buyer = $("buyerFilter").value;
  const sort = $("sortSelect").value;
  let rows = state.data.filter(row => {
    const haystack = Object.values(row).join(" ").toLowerCase();
    return (!q || haystack.includes(q)) && (!buyer || row.buyer_role === buyer);
  });
  if (sort === "use_case") rows.sort((a,b) => a.use_case.localeCompare(b.use_case));
  if (sort === "companies") rows.sort((a,b) => a.real_companies.localeCompare(b.real_companies));
  if (sort === "buyer") rows.sort((a,b) => a.buyer_role.localeCompare(b.buyer_role));
  return rows;
}
function renderCards() {
  state.filtered = getFiltered();
  $("resultCount").textContent = `${state.filtered.length} of ${state.data.length}`;
  $("cards").innerHTML = state.filtered.map((row,index) => `
    <article class="card" data-index="${index}" tabindex="0">
      <div class="card-top">
        <span class="number">${String(state.data.indexOf(row)+1).padStart(2,"0")}</span>
        <span class="buyer-pill">${escapeHtml(row.buyer_role || "Buyer not specified")}</span>
      </div>
      <h3>${escapeHtml(row.use_case)}</h3>
      <div class="companies">${companyChips(row.real_companies)}</div>
      <div class="workflow-preview">${escapeHtml(row.document_workflow)}</div>
      <p class="pain">${escapeHtml(row.why_it_bites)}</p>
      <div class="card-bottom"><span>View evidence & buying angle</span><span class="arrow">→</span></div>
    </article>
  `).join("");
  document.querySelectorAll(".card").forEach(card => {
    const open = () => openDetail(state.filtered[Number(card.dataset.index)]);
    card.addEventListener("click",open);
    card.addEventListener("keydown",e => { if(e.key==="Enter"||e.key===" "){e.preventDefault();open();} });
  });
  $("empty").hidden = state.filtered.length !== 0;
}
function openDetail(row) {
  state.selected = row;
  $("dialogKicker").textContent = row.buyer_role || "BUYER";
  $("dialogTitle").textContent = row.use_case;
  const source = row.source_url
    ? `<a class="source-link" href="${escapeHtml(row.source_url)}" target="_blank" rel="noopener noreferrer">Open official source ↗</a>`
    : `<span class="muted">No source URL supplied</span>`;
  $("dialogBody").innerHTML = `
    <div class="dialog-companies">${companyChips(row.real_companies)}</div>
    <div class="detail-grid">
      <section class="detail-block emphasis"><div class="detail-label">Specific document workflow</div><p>${escapeHtml(row.document_workflow)}</p></section>
      <section class="detail-block"><div class="detail-label">Recurring problem</div><p>${escapeHtml(row.recurring_problem)}</p></section>
      <section class="detail-block"><div class="detail-label">Evidence basis</div><p>${escapeHtml(row.evidence_basis)}</p></section>
      <section class="detail-block emphasis"><div class="detail-label">Why it bites</div><p>${escapeHtml(row.why_it_bites)}</p></section>
      <section class="detail-block"><div class="detail-label">Likely buyer</div><p>${escapeHtml(row.buyer_role)}</p></section>
      <section class="detail-block"><div class="detail-label">Where they listen</div><p>${escapeHtml(row.where_they_listen)}</p></section>
    </div>
    <section class="conversation"><div class="detail-label">First-conversation angle</div><p>${escapeHtml(row.conversation_opener)}</p></section>
    <div class="source-row"><span class="detail-label">Official evidence</span>${source}</div>
  `;
  $("detailDialog").showModal();
}
function parseCSV(text) {
  const rows=[]; let row=[],field="",quoted=false;
  for(let i=0;i<text.length;i++){
    const ch=text[i],next=text[i+1];
    if(ch==='"'){ if(quoted&&next==='"'){field+='"';i++;} else quoted=!quoted; }
    else if(ch===","&&!quoted){row.push(field);field="";}
    else if((ch==="\n"||ch==="\r")&&!quoted){
      if(ch==="\r"&&next==="\n")i++;
      row.push(field);field="";
      if(row.some(x=>x.trim()!==""))rows.push(row);
      row=[];
    } else field+=ch;
  }
  row.push(field); if(row.some(x=>x.trim()!==""))rows.push(row);
  if(!rows.length)return[];
  const headers=rows[0].map(h=>h.trim().replace(/^"|"$/g,""));
  return rows.slice(1).map(values=>{
    const obj={};headers.forEach((h,i)=>obj[h]=(values[i]??"").trim());
    return normalize(obj);
  }).filter(r=>r.use_case);
}
function loadData(data){ state.data=data.map(normalize);populateBuyerFilter(state.data);renderStats(state.data);renderCards(); }
$("searchInput").addEventListener("input",renderCards);
$("buyerFilter").addEventListener("change",renderCards);
$("sortSelect").addEventListener("change",renderCards);
$("csvInput").addEventListener("change",async event=>{
  const file=event.target.files?.[0];if(!file)return;
  try{
    const parsed=parseCSV(await file.text());
    if(!parsed.length)throw new Error("No valid rows found.");
    loadData(parsed);
  }catch(err){alert(`Could not load CSV: ${err.message}`);}
});
$("resetBtn").addEventListener("click",()=>{
  $("searchInput").value="";$("sortSelect").value="default";loadData(DEFAULT_DATA);$("csvInput").value="";
});
$("closeDialog").addEventListener("click",()=>$("detailDialog").close());
$("detailDialog").addEventListener("click",e=>{if(e.target===$("detailDialog"))$("detailDialog").close();});
loadData(DEFAULT_DATA);
