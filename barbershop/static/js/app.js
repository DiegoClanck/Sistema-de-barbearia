const state = {
  token: localStorage.getItem("navalha_token"),
  user: JSON.parse(localStorage.getItem("navalha_user") || "null"),
  services: [], professionals: [], appointments: [], currentView: "inicio"
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  const response = await fetch(`/api${path}`, { ...options, headers });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 && state.token) logout(false);
    throw new Error(data.erro || "Não foi possível concluir a operação.");
  }
  return data;
}

function toast(message, type = "success") {
  const item = document.createElement("div");
  item.className = `toast ${type}`;
  item.textContent = message;
  $("#toast-region").append(item);
  setTimeout(() => item.remove(), 3800);
}

function money(value) { return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(value); }
function escapeHtml(value = "") { const el = document.createElement("div"); el.textContent = value; return el.innerHTML; }
function dateParts(value) {
  const [date, time] = value.split(" ");
  const parsed = new Date(`${date}T${time}:00`);
  return { day: parsed.toLocaleDateString("pt-BR", { day: "2-digit", month: "short" }), time, full: parsed.toLocaleDateString("pt-BR", { weekday: "long", day: "2-digit", month: "long" }) };
}

async function loadPublicData() {
  try {
    const [services, professionals] = await Promise.all([api("/servicos"), api("/profissionais")]);
    state.services = services.servicos;
    state.professionals = professionals.profissionais;
    $("#public-services").innerHTML = state.services.slice(0, 3).map((service, index) => `
      <article class="service-card reveal" data-letter="${escapeHtml(service.nome[0])}">
        <span class="service-number">0${index + 1}</span>
        <h3>${escapeHtml(service.nome)}</h3>
        <p>Atendimento personalizado com técnica, cuidado e acabamento impecável.</p>
        <div class="service-meta"><span>◷ ${service.duracao_minutos} minutos</span><strong>${money(service.preco)}</strong></div>
      </article>`).join("");
  } catch (error) { $("#public-services").innerHTML = `<p>${error.message}</p>`; }
}

function openModal(register = false) {
  $("#auth-modal").classList.remove("hidden");
  document.body.style.overflow = "hidden";
  setAuthMode(register);
  setTimeout(() => $(register ? "#register-form input" : "#login-form input")?.focus(), 50);
}
function closeModal() { $("#auth-modal").classList.add("hidden"); document.body.style.overflow = ""; }
function setAuthMode(register) {
  $("#login-form").classList.toggle("hidden", register);
  $("#register-form").classList.toggle("hidden", !register);
  $("#auth-title").textContent = register ? "Crie sua conta" : "Entre na sua conta";
  $("#auth-subtitle").textContent = register ? "Seu próximo horário está a poucos passos." : "Acesse seus horários e cuide do seu estilo.";
  $(".switch-auth").innerHTML = register ? "Já possui conta? <strong>Entrar</strong>" : "Ainda não tem conta? <strong>Cadastre-se</strong>";
}

async function login(username, password) {
  const data = await api("/auth/login", { method: "POST", body: JSON.stringify({ usuario: username, senha: password }) });
  state.token = data.token; state.user = data.usuario;
  localStorage.setItem("navalha_token", state.token); localStorage.setItem("navalha_user", JSON.stringify(state.user));
  closeModal(); showApp(); toast(`Bem-vindo, ${state.user.nome.split(" ")[0]}!`);
}
function logout(showMessage = true) {
  state.token = null; state.user = null; state.appointments = [];
  localStorage.removeItem("navalha_token"); localStorage.removeItem("navalha_user");
  $("#app-shell").classList.add("hidden"); $("#public-site").classList.remove("hidden"); $(".topbar").classList.remove("hidden");
  if (showMessage) toast("Você saiu da sua conta.");
}

const navigation = {
  cliente: [{ id: "inicio", icon: "⌂", label: "Visão geral" }, { id: "agendar", icon: "＋", label: "Novo agendamento" }, { id: "agenda", icon: "◷", label: "Meus horários" }],
  profissional: [{ id: "inicio", icon: "⌂", label: "Minha agenda" }, { id: "historico", icon: "✓", label: "Atendimentos" }],
  admin: [{ id: "inicio", icon: "▦", label: "Dashboard" }, { id: "agenda", icon: "◷", label: "Agendamentos" }, { id: "servicos", icon: "✂", label: "Serviços" }, { id: "equipe", icon: "♙", label: "Equipe" }]
};

function showApp() {
  $("#public-site").classList.add("hidden"); $(".topbar").classList.add("hidden"); $("#app-shell").classList.remove("hidden");
  $("#user-name").textContent = state.user.nome; $("#user-role").textContent = state.user.tipo; $("#user-avatar").textContent = state.user.nome.slice(0, 2).toUpperCase();
  $("#app-navigation").innerHTML = navigation[state.user.tipo].map(item => `<button class="nav-item" data-view="${item.id}"><span>${item.icon}</span>${item.label}</button>`).join("");
  $$("[data-view]").forEach(button => button.addEventListener("click", () => renderView(button.dataset.view)));
  renderView("inicio");
}

async function renderView(view) {
  state.currentView = view; $$("[data-view]").forEach(button => button.classList.toggle("active", button.dataset.view === view));
  $(".sidebar").classList.remove("open"); $("#app-view").innerHTML = `<div class="panel"><div class="skeleton"></div></div>`;
  try {
    if (state.user.tipo === "cliente") await renderClient(view);
    else if (state.user.tipo === "profissional") await renderProfessional(view);
    else await renderAdmin(view);
  } catch (error) { $("#app-view").innerHTML = emptyState("!", "Algo não saiu como esperado", error.message); }
}

function setHeading(kicker, title) { $("#page-kicker").textContent = kicker; $("#page-title").textContent = title; }
function emptyState(icon, title, text) { return `<div class="panel empty-state"><span>${icon}</span><strong>${title}</strong><p>${text}</p></div>`; }
function appointmentRows(items, actions = false) {
  if (!items.length) return emptyState("◷", "Nenhum horário por aqui", "Os agendamentos aparecerão nesta lista.");
  return `<div class="appointment-list">${items.map(item => { const date = dateParts(item.inicio); return `
    <div class="appointment-row">
      <div class="date-badge"><strong>${date.day}</strong><span>${date.time}</span></div>
      <div><h3>${escapeHtml(state.user.tipo === "cliente" ? item.profissional.nome : item.cliente.nome)}</h3><p>${escapeHtml(item.servico.nome)} · ${item.servico.duracao_minutos} min</p></div>
      <div><span class="status status-${item.status}">${item.status}</span></div>
      ${actions ? actionButtons(item) : ""}
    </div>`; }).join("")}</div>`;
}
function actionButtons(item) {
  const buttons = [];
  if (state.user.tipo === "cliente" && ["agendado", "confirmado"].includes(item.status)) buttons.push(`<button class="mini-button" data-status="cancelado" data-id="${item.id}">Cancelar</button>`);
  if (["profissional", "admin"].includes(state.user.tipo) && item.status === "agendado") buttons.push(`<button class="mini-button" data-status="confirmado" data-id="${item.id}">Confirmar</button>`);
  if (["profissional", "admin"].includes(state.user.tipo) && ["agendado", "confirmado"].includes(item.status)) buttons.push(`<button class="mini-button" data-status="concluido" data-id="${item.id}">Concluir</button>`);
  return `<div class="row-actions">${buttons.join("") || `<span class="status status-${item.status}">${item.status}</span>`}</div>`;
}
function bindStatusActions() {
  $$("[data-status]").forEach(button => button.addEventListener("click", async () => {
    try { await api(`/agendamentos/${button.dataset.id}/status`, { method: "PATCH", body: JSON.stringify({ status: button.dataset.status }) }); toast("Agendamento atualizado."); renderView(state.currentView); }
    catch (error) { toast(error.message, "error"); }
  }));
}

async function renderClient(view) {
  if (!state.services.length || !state.professionals.length) await loadPublicData();
  if (view === "agendar") {
    setHeading("RESERVA ONLINE", "Escolha seu próximo horário");
    $("#app-view").innerHTML = `<div class="content-grid"><div class="panel"><div class="panel-header"><div><h2>Novo agendamento</h2><p>Selecione o serviço, profissional e melhor momento.</p></div></div>
      <form id="booking-form" class="form-grid">
        <div class="form-field full"><label>Serviço</label><select name="servico_id" required><option value="">Selecione...</option>${state.services.map(s => `<option value="${s.id}">${escapeHtml(s.nome)} — ${s.duracao_minutos} min · ${money(s.preco)}</option>`).join("")}</select></div>
        <div class="form-field full"><label>Profissional</label><select name="profissional_id" required><option value="">Selecione...</option>${state.professionals.map(p => `<option value="${p.id}">${escapeHtml(p.nome)}</option>`).join("")}</select></div>
        <div class="form-field"><label>Data</label><input name="data" type="date" min="${new Date().toISOString().slice(0,10)}" required></div>
        <div class="form-field"><label>Horário</label><input name="hora" type="time" step="900" required></div>
        <div class="form-field full"><button class="button button-gold" type="submit">Confirmar agendamento →</button></div>
      </form></div><div class="panel"><div class="panel-header"><div><h2>Como funciona</h2></div></div><p style="color:#777;font-size:12px;line-height:1.8">Seu horário respeita automaticamente a jornada do profissional e a duração de cada serviço. Caso já exista um atendimento no período, você poderá escolher outro momento.</p></div></div>`;
    $("#booking-form").addEventListener("submit", submitBooking); return;
  }
  const data = await api("/agendamentos"); state.appointments = data.agendamentos;
  if (view === "agenda") {
    setHeading("SEUS HORÁRIOS", "Minha agenda"); $("#app-view").innerHTML = `<div class="panel"><div class="panel-header"><div><h2>Todos os agendamentos</h2><p>Acompanhe e gerencie suas reservas.</p></div><button class="button button-gold" data-go-booking>+ Novo</button></div>${appointmentRows(state.appointments, true)}</div>`;
    $("[data-go-booking]")?.addEventListener("click", () => renderView("agendar")); bindStatusActions(); return;
  }
  const active = state.appointments.filter(a => ["agendado", "confirmado"].includes(a.status)); const next = [...active].reverse()[0];
  setHeading("ÁREA DO CLIENTE", `Olá, ${state.user.nome.split(" ")[0]}!`);
  $("#app-view").innerHTML = `<div class="dashboard-grid"><div class="stat-card"><small>Próximos horários</small><strong>${active.length}</strong></div><div class="stat-card"><small>Atendimentos feitos</small><strong>${state.appointments.filter(a=>a.status==="concluido").length}</strong></div><div class="stat-card"><small>Status da conta</small><strong class="gold">${state.user.assinante ? "Assinante" : "Cliente"}</strong></div><div class="stat-card"><small>Serviços disponíveis</small><strong>${state.services.length}</strong></div></div>
    <div class="content-grid"><div class="panel"><div class="panel-header"><div><h2>Seus agendamentos</h2><p>Próximos compromissos e histórico.</p></div><button class="button button-gold" data-go-booking>+ Agendar</button></div>${appointmentRows(state.appointments.slice(0,5), true)}</div>
    <div class="panel"><div class="panel-header"><div><h2>Próxima visita</h2></div></div>${next ? `<div class="empty-state"><span>✂</span><strong>${dateParts(next.inicio).full}</strong><p>${next.servico.nome} com ${next.profissional.nome}, às ${dateParts(next.inicio).time}</p></div>` : `<div class="empty-state"><span>＋</span><strong>Renove seu estilo</strong><p>Você ainda não possui uma próxima visita.</p></div>`}</div></div>`;
  $("[data-go-booking]")?.addEventListener("click", () => renderView("agendar")); bindStatusActions();
}

async function submitBooking(event) {
  event.preventDefault(); const form = new FormData(event.currentTarget); const button = $("button[type=submit]", event.currentTarget); button.disabled = true; button.textContent = "Reservando...";
  try { await api("/agendamentos", { method: "POST", body: JSON.stringify({ servico_id: Number(form.get("servico_id")), profissional_id: Number(form.get("profissional_id")), data_hora: `${form.get("data")} ${form.get("hora")}` }) }); toast("Horário reservado com sucesso!"); renderView("agenda"); }
  catch (error) { toast(error.message, "error"); button.disabled = false; button.textContent = "Confirmar agendamento →"; }
}

async function renderProfessional(view) {
  const data = await api(`/agendamentos${view === "historico" ? "?status=concluido" : ""}`); state.appointments = data.agendamentos;
  setHeading(view === "historico" ? "HISTÓRICO" : "ÁREA DO PROFISSIONAL", view === "historico" ? "Atendimentos concluídos" : `Bom trabalho, ${state.user.nome.split(" ")[0]}!`);
  const today = new Date().toISOString().slice(0,10); const todayItems = state.appointments.filter(a => a.inicio.startsWith(today));
  $("#app-view").innerHTML = view === "historico" ? `<div class="panel"><div class="panel-header"><div><h2>Histórico de atendimentos</h2><p>Serviços finalizados por você.</p></div></div>${appointmentRows(state.appointments, false)}</div>` : `<div class="dashboard-grid"><div class="stat-card"><small>Atendimentos hoje</small><strong>${todayItems.length}</strong></div><div class="stat-card"><small>Aguardando confirmação</small><strong>${state.appointments.filter(a=>a.status==="agendado").length}</strong></div><div class="stat-card"><small>Confirmados</small><strong>${state.appointments.filter(a=>a.status==="confirmado").length}</strong></div><div class="stat-card"><small>Jornada</small><strong class="gold">${state.user.jornada ? state.user.jornada.inicio : "—"}</strong></div></div><div class="panel"><div class="panel-header"><div><h2>Sua agenda</h2><p>Confirme ou conclua os próximos atendimentos.</p></div></div>${appointmentRows(state.appointments, true)}</div>`;
  bindStatusActions();
}

async function renderAdmin(view) {
  if (view === "servicos") { await renderAdminServices(); return; }
  if (view === "equipe") { await renderAdminTeam(); return; }
  if (view === "agenda") { const data = await api("/agendamentos"); state.appointments = data.agendamentos; setHeading("GESTÃO DE AGENDA", "Todos os agendamentos"); $("#app-view").innerHTML = `<div class="panel"><div class="panel-header"><div><h2>Agenda geral</h2><p>Visão completa de clientes e profissionais.</p></div></div>${appointmentRows(state.appointments, true)}</div>`; bindStatusActions(); return; }
  const [dashboard, appointments] = await Promise.all([api("/admin/dashboard"), api("/agendamentos")]); state.appointments = appointments.agendamentos;
  setHeading("VISÃO GERAL", "Painel da barbearia");
  $("#app-view").innerHTML = `<div class="dashboard-grid"><div class="stat-card"><small>Faturamento realizado</small><strong class="gold">${money(dashboard.faturamento)}</strong></div><div class="stat-card"><small>Clientes ativos</small><strong>${dashboard.total_clientes}</strong></div><div class="stat-card"><small>Equipe</small><strong>${dashboard.total_profissionais}</strong></div><div class="stat-card"><small>Agenda pendente</small><strong>${dashboard.agendamentos_pendentes}</strong></div></div><div class="content-grid"><div class="panel"><div class="panel-header"><div><h2>Agenda recente</h2><p>Últimos agendamentos registrados.</p></div></div>${appointmentRows(state.appointments.slice(0,6), true)}</div><div class="panel"><div class="panel-header"><div><h2>Resumo operacional</h2></div></div><div class="empty-state"><span>✦</span><strong>${dashboard.atendimentos_concluidos} atendimentos concluídos</strong><p>${dashboard.total_assinantes} clientes fazem parte do clube de assinantes.</p></div></div></div>`; bindStatusActions();
}

async function renderAdminServices() {
  const data = await api("/servicos"); state.services = data.servicos; setHeading("CATÁLOGO", "Serviços da barbearia");
  $("#app-view").innerHTML = `<div class="content-grid"><div class="panel"><div class="panel-header"><div><h2>Serviços ativos</h2><p>Catálogo oferecido aos clientes.</p></div></div><div class="table-wrap"><table class="data-table"><thead><tr><th>Serviço</th><th>Duração</th><th>Valor</th><th>Status</th></tr></thead><tbody>${state.services.map(s=>`<tr><td><strong>${escapeHtml(s.nome)}</strong></td><td>${s.duracao_minutos} min</td><td>${money(s.preco)}</td><td><span class="status status-confirmado">Ativo</span></td></tr>`).join("")}</tbody></table></div></div><div class="panel"><div class="panel-header"><div><h2>Novo serviço</h2><p>Adicione uma opção ao catálogo.</p></div></div><form id="service-form" class="form-grid"><div class="form-field full"><label>Nome</label><input name="nome" required></div><div class="form-field"><label>Duração (min)</label><input name="duracao" type="number" min="5" required></div><div class="form-field"><label>Preço (R$)</label><input name="preco" type="number" min="0" step="0.01" required></div><div class="form-field full"><button class="button button-gold" type="submit">Adicionar serviço</button></div></form></div></div>`;
  $("#service-form").addEventListener("submit", async event => { event.preventDefault(); const f=new FormData(event.currentTarget); try{await api("/servicos",{method:"POST",body:JSON.stringify({nome:f.get("nome"),duracao_minutos:Number(f.get("duracao")),preco:Number(f.get("preco"))})});toast("Serviço adicionado.");renderView("servicos");}catch(e){toast(e.message,"error");} });
}

async function renderAdminTeam() {
  const data = await api("/profissionais"); state.professionals = data.profissionais; setHeading("NOSSO TIME", "Equipe de profissionais");
  $("#app-view").innerHTML = `<div class="content-grid"><div class="panel"><div class="panel-header"><div><h2>Profissionais ativos</h2><p>Equipe disponível para agendamentos.</p></div></div><div class="table-wrap"><table class="data-table"><thead><tr><th>Nome</th><th>Usuário</th><th>Jornada</th><th>Dias</th></tr></thead><tbody>${state.professionals.map(p=>`<tr><td><strong>${escapeHtml(p.nome)}</strong></td><td>${escapeHtml(p.usuario)}</td><td>${p.jornada?.inicio || "—"} — ${p.jornada?.fim || "—"}</td><td>${p.jornada?.dias_semana.length || 0} dias</td></tr>`).join("")}</tbody></table></div></div><div class="panel"><div class="panel-header"><div><h2>Novo profissional</h2><p>Cadastre um novo membro.</p></div></div><form id="team-form" class="form-grid"><div class="form-field full"><label>Nome</label><input name="nome" required></div><div class="form-field full"><label>Usuário</label><input name="usuario" required></div><div class="form-field full"><label>Senha inicial</label><input name="senha" type="password" minlength="6" required></div><div class="form-field full"><button class="button button-gold" type="submit">Adicionar à equipe</button></div></form></div></div>`;
  $("#team-form").addEventListener("submit", async event => { event.preventDefault(); const f=new FormData(event.currentTarget); try{await api("/profissionais",{method:"POST",body:JSON.stringify({nome:f.get("nome"),usuario:f.get("usuario"),senha:f.get("senha")})});toast("Profissional cadastrado.");renderView("equipe");}catch(e){toast(e.message,"error");} });
}

document.addEventListener("click", event => {
  const action = event.target.closest("[data-action]")?.dataset.action;
  if (action === "open-login") openModal();
  if (action === "start-booking") state.user ? showApp() : openModal();
  if (action === "close-modal") closeModal();
  if (action === "switch-auth") setAuthMode(!$("#login-form").classList.contains("hidden"));
  if (action === "logout") logout();
  if (action === "toggle-sidebar") $(".sidebar").classList.toggle("open");
});
$("#auth-modal").addEventListener("click", event => { if (event.target === $("#auth-modal")) closeModal(); });
$("#login-form").addEventListener("submit", async event => { event.preventDefault(); const f=new FormData(event.currentTarget); try{await login(f.get("usuario"),f.get("senha"));}catch(e){toast(e.message,"error");} });
$("#register-form").addEventListener("submit", async event => { event.preventDefault(); const f=new FormData(event.currentTarget); try{await api("/clientes",{method:"POST",body:JSON.stringify({nome:f.get("nome"),usuario:f.get("usuario"),senha:f.get("senha")})});toast("Conta criada! Entrando...");await login(f.get("usuario"),f.get("senha"));}catch(e){toast(e.message,"error");} });
$$('[data-demo]').forEach(button => button.addEventListener("click", () => login(button.dataset.demo, button.dataset.demo === "admin" ? "admin123" : "123456").catch(e=>toast(e.message,"error"))));
document.addEventListener("keydown", event => { if (event.key === "Escape") closeModal(); });

loadPublicData();
if (state.token && state.user) showApp();
