const DEFAULT_DATA = [{"use_case":"Multilingual Help Center article maintenance","real_companies":"Zendesk","document_workflow":"Create and maintain translated Help Center articles, including translated sections/categories and ongoing article updates.","recurring_problem":"When source content changes, localized versions need coordinated updates; stale translations and missed structural changes can reduce consistency across locales.","evidence_basis":"Zendesk officially documents adding translated Help Center articles and translating parent sections/categories, establishing a recurring localization workflow.","buyer_role":"Knowledge Operations / Support Content Lead","why_it_bites":"Every source-content release can create follow-up translation and review work across multiple locales.","where_they_listen":"Knowledge-management communities, support-operations communities, Zendesk ecosystem, documentation/content events","conversation_opener":"When a Help Center article changes, how do you identify every locale that now needs review and republish?","source_url":"https://support.zendesk.com/hc/en-us/articles/4408834328090-Localizing-help-center-content"},{"use_case":"Localized developer documentation synchronization","real_companies":"GitBook","document_workflow":"Maintain localized documentation variants and keep translated developer documentation aligned with source content.","recurring_problem":"Multiple documentation variants create synchronization and review work whenever source documentation changes.","evidence_basis":"GitBook documents localized documentation variants and AI translation workflows for multiple languages.","buyer_role":"Documentation / Developer Education Lead","why_it_bites":"Developer documentation changes frequently, so localization can become a repeated release dependency.","where_they_listen":"Developer-documentation communities, GitBook ecosystem, technical-writing events","conversation_opener":"When a source documentation page changes, how do you identify which localized variants need translation and review?","source_url":"https://gitbook.com/docs/guides/content-organization-and-localization/localize-your-docs-with-variants-in-gitbook"},{"use_case":"Multilingual storefront content and translation maintenance","real_companies":"Shopify","document_workflow":"Maintain multilingual store content, translations, translated URLs, and translation status across localized content.","recurring_problem":"Source changes can create a queue of translation and review work across language variants, with outdated translations needing attention.","evidence_basis":"Shopify officially documents multilingual content, translation workflows, translated URLs, CSV translation management, and outdated translation status.","buyer_role":"Localization / Content Operations Lead","why_it_bites":"Large catalogs and frequent content changes multiply localization maintenance work.","where_they_listen":"Localization communities, Shopify ecosystem, ecommerce operations communities","conversation_opener":"When source storefront content changes, how do you prioritize the language variants that are now outdated?","source_url":"https://help.shopify.com/en/manual/international/localization-and-translation"},{"use_case":"Technical documentation localization QA and release workflow","real_companies":"GitLab","document_workflow":"Localize product documentation, manage translation requests, run QA, and maintain multilingual documentation.","recurring_problem":"Frequent documentation releases create recurring translation, QA, and synchronization work across languages.","evidence_basis":"GitLab describes product-documentation localization infrastructure, automated workflows, QA, translation request management, and multilingual documentation.","buyer_role":"Documentation Localization Lead","why_it_bites":"Documentation release velocity can turn localization QA into a recurring bottleneck.","where_they_listen":"Technical-writing communities, GitLab ecosystem, localization and developer-documentation events","conversation_opener":"How do you keep localization QA from becoming a release bottleneck when source documentation changes frequently?","source_url":"https://handbook.gitlab.com/handbook/marketing/localization/tech_docs_localization/"},{"use_case":"Public knowledge article translation coverage and status","real_companies":"Intercom","document_workflow":"Create translated public articles, publish them by language, and track whether translations are published or missing/unpublished.","recurring_problem":"Missing or unpublished translations can create language-specific gaps in self-service support.","evidence_basis":"Intercom officially documents multilingual public articles and translation-status states including published versus missing/unpublished translations.","buyer_role":"Knowledge Operations / Support Content Lead","why_it_bites":"Translation gaps can silently reduce self-service coverage for specific customer-language segments.","where_they_listen":"Support-content communities, Intercom ecosystem, knowledge-management and customer-experience events","conversation_opener":"How do you prioritize missing or unpublished translations before customers encounter a language coverage gap?","source_url":"https://www.intercom.com/help/en/articles/3107405-add-translations-to-public-articles"},{"use_case":"Knowledge article translation and review workflow","real_companies":"Salesforce","document_workflow":"Translate Knowledge articles into multiple languages, assign translations, import translated article files, and have subject-matter experts review the results.","recurring_problem":"Multilingual knowledge content creates recurring translation, assignment, import, and review work that must stay synchronized with source articles.","evidence_basis":"Salesforce officially documents Knowledge Translation, translation submission by language, separate translated article records, subject-matter review, and importing article translations with HTML and images.","buyer_role":"Knowledge Management / Localization Operations Lead","why_it_bites":"A large multilingual knowledge base creates repeated translation and review work, while article updates can leave localized support content out of sync.","where_they_listen":"Knowledge-management communities, Salesforce ecosystem, customer-support operations communities, localization and technical-writing events","conversation_opener":"When a Knowledge article changes, how do you identify which language versions need translation and subject-matter review before publishing?","source_url":"https://help.salesforce.com/s/articleView?id=service.service_translating_a_knowledge_article.htm\u0026language=en_US\u0026type=5"},{"use_case":"Personalized offer-letter and employment-agreement generation","real_companies":"Workday","document_workflow":"Generate offer letters and employment agreements from reusable templates using candidate data, condition rules, review steps, regeneration, and attachments.","recurring_problem":"High-volume recruiting requires repeated document generation, correction, regeneration, review, and attachment handling when candidate or offer details change.","evidence_basis":"Workday documents customizable offer templates with variable data, dynamic document generation, review steps, regeneration after corrections, and attachments.","buyer_role":"Recruiting Operations / HR Operations Lead","why_it_bites":"Offer corrections and high-volume hiring create repeated document-generation and review work.","where_they_listen":"HR operations communities, recruiting-operations communities, Workday ecosystem, HR technology events","conversation_opener":"When candidate details change after an offer is generated, how do you regenerate the document while keeping the approved template and review process intact?","source_url":"https://doc.workday.com/admin-guide/en-us/human-capital-management/recruiting/offers/gxl1589210137955.html"},{"use_case":"Standard employee document generation and review","real_companies":"ServiceNow","document_workflow":"Use HTML/PDF document templates to generate standard letters or documents and route participants through fill, sign, review, and PDF generation steps.","recurring_problem":"Standard employee documents require repeated population, review, signing, and final document generation.","evidence_basis":"ServiceNow officially documents Document Templates for HTML/PDF generation, participant tasks, review, signing, preview, and PDF generation.","buyer_role":"Employee Operations / HR Service Delivery Lead","why_it_bites":"Repeated standard-document workflows create operational overhead when teams manage many similar employee requests.","where_they_listen":"HR service-delivery communities, ServiceNow ecosystem, employee-experience events","conversation_opener":"How much of your standard-document workflow still depends on maintaining templates and moving generated documents through review?","source_url":"https://www.servicenow.com/docs/r/employee-service-management/hr-service-delivery/document-templates-overview.html"},{"use_case":"Personalized agreement generation from structured business data","real_companies":"DocuSign","document_workflow":"Generate personalized agreements from templates by dynamically inserting data from internal systems before sending them for eSignature.","recurring_problem":"Teams repeatedly assemble personalized agreements from source-system data and templates, with location- or scenario-specific clauses that must be correct before signing.","evidence_basis":"DocuSign officially documents document generation through its eSignature REST API, dynamic data insertion, templates, and personalized agreement examples including offer letters and service requests.","buyer_role":"Agreement Operations / Business Systems Lead","why_it_bites":"Manual template selection and data insertion create repetitive preparation work and formatting risk before agreements reach signature.","where_they_listen":"Agreement-operations communities, DocuSign ecosystem, legal-operations and business-systems events","conversation_opener":"Where does document generation happen before an agreement enters your signing workflow, and how do you keep the generated document consistent with source data?","source_url":"https://www.docusign.com/blog/developers/generate-and-send-personalized-agreements-document-generation-esignature"},{"use_case":"Reusable quote and proposal document generation","real_companies":"HubSpot","document_workflow":"Create standardized branded quotes from reusable templates, populate line items and deal information, add terms and attachments, route approvals, and present the quote for buyer acceptance.","recurring_problem":"Revenue teams need consistent quote structure and content while deal-specific pricing, terms, attachments, and approvals change from opportunity to opportunity.","evidence_basis":"HubSpot officially documents quote templates, reusable modules, line items, cover letters, terms, attachments, approvals, and buyer acceptance in its CPQ workflow.","buyer_role":"Revenue Operations / Sales Operations Lead","why_it_bites":"Template drift and repeated quote editing can slow sales operations while creating consistency and approval risks.","where_they_listen":"Revenue-operations communities, HubSpot ecosystem, sales-operations and CPQ events","conversation_opener":"When quote structure or terms change, how do you keep every seller-generated document aligned without manually maintaining multiple versions?","source_url":"https://knowledge.hubspot.com/cpq/understand-hubspot-cpq"}];

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
      <div class="card-bottom"><span>View evidence & buying angle</span><span class="arrow">â†’</span></div>
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
    ? `<a class="source-link" href="${escapeHtml(row.source_url)}" target="_blank" rel="noopener noreferrer">Open official source â†—</a>`
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
function loadData(data){ state.data=data.map(normalize);populateBuyerFilter(state.data);renderStats(state.data);renderCards(); }
$("searchInput").addEventListener("input",renderCards);
$("buyerFilter").addEventListener("change",renderCards);
$("sortSelect").addEventListener("change",renderCards);
$("resetBtn").addEventListener("click",()=>{
  $("searchInput").value="";
  $("buyerFilter").value="";
  $("sortSelect").value="default";
  renderCards();
});
$("closeDialog").addEventListener("click",()=>$("detailDialog").close());
$("detailDialog").addEventListener("click",e=>{if(e.target===$("detailDialog"))$("detailDialog").close();});
loadData(DEFAULT_DATA);

