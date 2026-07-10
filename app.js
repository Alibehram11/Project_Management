const STORAGE_KEY = "projeYonetimi.v5";
const SESSION_KEY = "projeYonetimi.session.v5";
const MAX_FILE_SIZE = 2 * 1024 * 1024;
const SELF_TEST_MODE = new URLSearchParams(window.location.search).has("selftest");

const documentTemplates = [
  {
    id: "fr01",
    fileName: "01_FR-01_Proje_Tanim_Karti.docx",
    title: "FR-01 Proje Tanım Kartı",
    questions: [
      "Proje adı",
      "Proje amacı",
      "Hedef kullanıcı veya yarışma kategorisi",
      "Takım üyeleri ve sorumlulukları",
      "Beklenen çıktı",
    ],
  },
  {
    id: "fr02",
    fileName: "02_FR-02_Kural_Gereksinim_Matrisi.docx",
    title: "FR-02 Kural Gereksinim Matrisi",
    questions: [
      "İlgili kural maddesi",
      "Teknik gereksinim",
      "Bu gereksinimi karşılayan çözüm",
      "Kontrol yöntemi",
    ],
  },
  {
    id: "fr03",
    fileName: "03_FR-03_On_Tasarim_Formu.docx",
    title: "FR-03 Ön Tasarım Formu",
    questions: [
      "Tasarım özeti",
      "Kullanılacak ana parçalar",
      "Yazılım mimarisi",
      "Mekanik/elektronik tasarım notları",
      "Açık riskler",
    ],
  },
  {
    id: "fr04",
    fileName: "04_FR-04_Malzeme_Ihtiyac_Listesi.docx",
    title: "FR-04 Malzeme İhtiyaç Listesi",
    questions: [
      "Malzeme adı",
      "Adet",
      "Tahmini maliyet",
      "Tedarik durumu",
      "Sorumlu kişi",
    ],
  },
  {
    id: "fr05",
    fileName: "05_FR-05_Kritik_Parca_Yedek_Listesi.docx",
    title: "FR-05 Kritik Parça Yedek Listesi",
    questions: [
      "Kritik parça",
      "Arıza etkisi",
      "Yedek parça durumu",
      "Sorumlu kişi",
    ],
  },
  {
    id: "fr06",
    fileName: "06_FR-06_Gorev_Dagilim_Matrisi.docx",
    title: "FR-06 Görev Dağılım Matrisi",
    questions: [
      "Görev adı",
      "Sorumlu ekip/kişi",
      "Başlangıç tarihi",
      "Bitiş tarihi",
      "Durum",
    ],
  },
  {
    id: "fr07",
    fileName: "07_FR-07_Zaman_Cizelgesi.docx",
    title: "FR-07 Zaman Çizelgesi",
    questions: [
      "Kilometre taşı",
      "Planlanan tarih",
      "Gerçekleşen tarih",
      "Gecikme/engel notu",
    ],
  },
  {
    id: "fr08",
    fileName: "08_FR-08_Risk_Kayit_Formu.docx",
    title: "FR-08 Risk Kayıt Formu",
    questions: [
      "Risk tanımı",
      "Olasılık",
      "Etki",
      "Önlem",
      "Sorumlu kişi",
    ],
  },
  {
    id: "fr09",
    fileName: "09_FR-09_Test_Plani_Hata_Defteri.docx",
    title: "FR-09 Test Planı Hata Defteri",
    questions: [
      "Test adı",
      "Test adımları",
      "Beklenen sonuç",
      "Bulunan hata",
      "Düzeltme durumu",
    ],
  },
  {
    id: "fr10",
    fileName: "10_FR-10_Yarisma_Gunu_Kapanis_Raporu.docx",
    title: "FR-10 Yarışma Günü Kapanış Raporu",
    questions: [
      "Yarışma günü özeti",
      "Başarılı olan noktalar",
      "Sorunlar",
      "Bir sonraki proje için notlar",
    ],
  },
];

const ALLOWED_PRIORITIES = new Set(["low", "normal", "high", "urgent"]);
const ALLOWED_ROLES = new Set(["member", "lead", "admin"]);
const ALLOWED_TEAMS = new Set(["Yazılım", "Tasarım", "Mekanik", "Elektronik", "Yönetim"]);
const ALLOWED_EVENT_TYPES = new Set(["Toplantı", "Teslim", "Test", "Yarışma", "Not"]);

const authView = document.querySelector("#authView");
const appView = document.querySelector("#appView");
const loginTab = document.querySelector("#loginTab");
const registerTab = document.querySelector("#registerTab");
const loginForm = document.querySelector("#loginForm");
const registerForm = document.querySelector("#registerForm");
const authMessage = document.querySelector("#authMessage");
const projectSelect = document.querySelector("#projectSelect");
const activeProjectLabel = document.querySelector("#activeProjectLabel");
const changeProjectButton = document.querySelector("#changeProjectButton");
const projectGate = document.querySelector("#projectGate");
const projectGateList = document.querySelector("#projectGateList");
const gateNewProjectButton = document.querySelector("#gateNewProjectButton");
const currentUserLabel = document.querySelector("#currentUserLabel");
const projectRoleLabel = document.querySelector("#projectRoleLabel");
const projectTitle = document.querySelector("#projectTitle");
const logoutButton = document.querySelector("#logoutButton");
const openTaskButton = document.querySelector("#openTaskButton");
const openMemberButton = document.querySelector("#openMemberButton");
const openEventButton = document.querySelector("#openEventButton");
const newProjectButton = document.querySelector("#newProjectButton");
const openTemplateEditorButton = document.querySelector("#openTemplateEditorButton");
const memberSubmitButton = document.querySelector("#memberSubmitButton");
const navLinks = document.querySelectorAll(".nav-link");
const workspaceView = document.querySelector("#workspaceView");
const adminView = document.querySelector("#adminView");
const dashboardView = document.querySelector("#dashboardView");
const myWorkView = document.querySelector("#myWorkView");
const tasksView = document.querySelector("#tasksView");
const inboxView = document.querySelector("#inboxView");
const teamView = document.querySelector("#teamView");
const docsView = document.querySelector("#docsView");
const calendarView = document.querySelector("#calendarView");
const crmView = document.querySelector("#crmView");
const feedView = document.querySelector("#feedView");
const reportsView = document.querySelector("#reportsView");
const taskDialog = document.querySelector("#taskDialog");
const memberDialog = document.querySelector("#memberDialog");
const projectDialog = document.querySelector("#projectDialog");
const eventDialog = document.querySelector("#eventDialog");
const templateDialog = document.querySelector("#templateDialog");
const taskForm = document.querySelector("#taskForm");
const memberForm = document.querySelector("#memberForm");
const projectForm = document.querySelector("#projectForm");
const eventForm = document.querySelector("#eventForm");
const documentForm = document.querySelector("#documentForm");
const templateForm = document.querySelector("#templateForm");
const checkTemplateButton = document.querySelector("#checkTemplateButton");
const exportDocumentButton = document.querySelector("#exportDocumentButton");
const templateUploadInput = document.querySelector("#templateUploadInput");
const documentBackendMessage = document.querySelector("#documentBackendMessage");
const adminUserForm = document.querySelector("#adminUserForm");
const refreshLogsButton = document.querySelector("#refreshLogsButton");
const downloadStateButton = document.querySelector("#downloadStateButton");
const saveSnapshotButton = document.querySelector("#saveSnapshotButton");
const reloadBackendStateButton = document.querySelector("#reloadBackendStateButton");
const repairStateButton = document.querySelector("#repairStateButton");
const maintenanceMessage = document.querySelector("#maintenanceMessage");
const backendStatus = document.querySelector("#backendStatus");

let state = loadState();
let session = loadSession();
let backendOnline = false;
let stateSyncTimer = 0;
let latestLogs = [];

function uid() {
  if (window.crypto?.randomUUID) {
    return window.crypto.randomUUID();
  }
  return `id-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function todayOffset(days) {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return date.toISOString().slice(0, 10);
}

function createSeedData() {
  const ownerId = uid();
  const leadId = uid();
  const devId = uid();
  const designId = uid();
  const projectId = uid();

  return {
    version: 5,
    users: [
      {
        id: ownerId,
        name: "Ana Admin",
        email: "admin@proje.local",
        password: "123456",
      },
      {
        id: leadId,
        name: "Yazılım Kaptanı",
        email: "yazilim@proje.local",
        password: "123456",
      },
      {
        id: devId,
        name: "Yazılım Üyesi",
        email: "yazilim2@proje.local",
        password: "123456",
      },
      {
        id: designId,
        name: "Tasarım Üyesi",
        email: "tasarim@proje.local",
        password: "123456",
      },
    ],
    projects: [
      {
        id: projectId,
        name: "Robot Takımı Yönetimi",
        description: "Yazılım, tasarım, belge ve takvim akışını takip.",
        ownerId,
        memberIds: [ownerId, leadId, devId, designId],
        adminIds: [ownerId],
        memberProfiles: {
          [ownerId]: { role: "owner", team: "Yönetim", title: "Ana admin" },
          [leadId]: { role: "lead", team: "Yazılım", title: "Yazılım kaptanlığı" },
          [devId]: { role: "member", team: "Yazılım", title: "Yazılım ekibi" },
          [designId]: { role: "member", team: "Tasarım", title: "Tasarım ekibi" },
        },
      },
    ],
    invites: [],
    tasks: [
      {
        id: uid(),
        projectId,
        title: "Kontrol paneli giriş ekranı",
        description: "Mail ve şifre ile giriş yapılacak ekranı hazırla.",
        assigneeId: devId,
        createdBy: leadId,
        dueDate: todayOffset(3),
        status: "todo",
        team: "Yazılım",
        priority: "high",
        label: "Yazılım",
        estimateHours: 4,
        checklist: [
          { id: uid(), text: "Form alanlarını bağla", done: true },
          { id: uid(), text: "Giriş hatalarını göster", done: false },
        ],
        comments: [],
        submissions: [],
      },
      {
        id: uid(),
        projectId,
        title: "Ana sayfa tasarım taslağı",
        description: "Takım ve görevlerin görüleceği arayüz taslağını yükle.",
        assigneeId: designId,
        createdBy: ownerId,
        dueDate: todayOffset(5),
        status: "review",
        team: "Tasarım",
        priority: "normal",
        label: "Tasarım",
        estimateHours: 3,
        checklist: [{ id: uid(), text: "Dashboard taslağı", done: true }],
        comments: [
          {
            id: uid(),
            userId: ownerId,
            text: "Renkleri biraz daha sade tutalım.",
            createdAt: new Date().toISOString(),
          },
        ],
        submissions: [
          {
            id: uid(),
            userId: designId,
            note: "İlk taslak eklendi, onay bekliyor.",
            fileName: "dashboard-tasarim.png",
            fileData: "",
            submittedAt: new Date().toISOString(),
          },
        ],
      },
    ],
    documents: {},
    documentTemplates: documentTemplates.map((template) => ({
      ...template,
      questions: [...template.questions],
    })),
    calendarEvents: [
      {
        id: uid(),
        projectId,
        title: "Haftalık ekip toplantısı",
        date: todayOffset(2),
        type: "Toplantı",
        description: "Görev durumu ve belge eksikleri kontrol edilecek.",
        createdBy: ownerId,
      },
    ],
    crmItems: [
      {
        id: uid(),
        projectId,
        title: "Sponsor görüşmesi",
        company: "Yerel teknoloji firması",
        stage: "İlk temas",
        value: "Destek görüşülecek",
        ownerId,
      },
      {
        id: uid(),
        projectId,
        title: "Malzeme tedariki",
        company: "Parça tedarikçisi",
        stage: "Teklif bekleniyor",
        value: "Motor ve elektronik",
        ownerId: leadId,
      },
    ],
    feedItems: [
      {
        id: uid(),
        projectId,
        userId: ownerId,
        type: "Duyuru",
        text: "Bu hafta görev ve belge eksikleri kapatılacak.",
        createdAt: new Date().toISOString(),
      },
    ],
  };
}

function loadState() {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (!saved) {
    const seed = createSeedData();
    localStorage.setItem(STORAGE_KEY, JSON.stringify(seed));
    return seed;
  }

  try {
    const parsed = JSON.parse(saved);
    return normalizeState(parsed);
  } catch {
    const seed = createSeedData();
    localStorage.setItem(STORAGE_KEY, JSON.stringify(seed));
    return seed;
  }
}

function normalizeState(value) {
  const seed = createSeedData();
  const normalized = {
    ...seed,
    ...value,
    version: 5,
    users: Array.isArray(value.users) ? value.users : seed.users,
    projects: Array.isArray(value.projects) ? value.projects : seed.projects,
    invites: Array.isArray(value.invites) ? value.invites : [],
    tasks: Array.isArray(value.tasks) ? value.tasks : seed.tasks,
    documents: value.documents && typeof value.documents === "object" ? value.documents : {},
    calendarEvents: Array.isArray(value.calendarEvents) ? value.calendarEvents : [],
    crmItems: Array.isArray(value.crmItems) ? value.crmItems : seed.crmItems,
    feedItems: Array.isArray(value.feedItems) ? value.feedItems : seed.feedItems,
    documentTemplates: Array.isArray(value.documentTemplates)
      ? value.documentTemplates
      : seed.documentTemplates,
  };

  normalized.projects.forEach((project) => {
    project.memberIds ||= [];
    project.adminIds ||= [project.ownerId].filter(Boolean);
    project.memberProfiles ||= {};
    project.memberIds.forEach((userId) => {
      project.memberProfiles[userId] ||= {
        role: userId === project.ownerId ? "owner" : "member",
        team: "Yönetim",
        title: userId === project.ownerId ? "Ana admin" : "Üye",
      };
      const profile = project.memberProfiles[userId];
      if (profile.role !== "owner" && !ALLOWED_ROLES.has(profile.role)) {
        profile.role = "member";
      }
      if (!ALLOWED_TEAMS.has(profile.team)) {
        profile.team = "Yönetim";
      }
    });
  });

  normalized.tasks.forEach((task) => {
    task.priority = ALLOWED_PRIORITIES.has(task.priority) ? task.priority : "normal";
    if (!["todo", "review", "approved", "changes"].includes(task.status)) {
      task.status = "todo";
    }
    task.label ||= task.team || "Yönetim";
    task.estimateHours = Number(task.estimateHours || 0);
    task.checklist = Array.isArray(task.checklist) ? task.checklist : [];
    task.comments = Array.isArray(task.comments) ? task.comments : [];
  });

  normalized.documentTemplates = mergeTemplates(normalized.documentTemplates);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(normalized));
  return normalized;
}

function mergeTemplates(templates) {
  return documentTemplates.map((base) => {
    const existing = templates.find((template) => template.id === base.id);
    return {
      ...base,
      ...existing,
      questions: existing?.questions?.length ? existing.questions : base.questions,
    };
  });
}

function canUseBackend() {
  return window.location.protocol === "http:" || window.location.protocol === "https:";
}

function setBackendMessage(message, type = "info") {
  if (documentBackendMessage) {
    documentBackendMessage.textContent = message;
    documentBackendMessage.dataset.type = type;
  }
}

function setMaintenanceMessage(message, type = "info") {
  if (maintenanceMessage) {
    maintenanceMessage.textContent = message;
    maintenanceMessage.dataset.type = type;
  }
}

function updateBackendStatus(message) {
  if (!backendStatus) {
    return;
  }
  backendStatus.textContent = message || (backendOnline ? "Backend aktif: SQLite, log ve Word indirme açık." : "Backend kapalı: site statik modda çalışıyor.");
  backendStatus.dataset.online = backendOnline ? "true" : "false";
}

async function apiJson(path, options = {}) {
  if (!canUseBackend() || SELF_TEST_MODE) {
    return null;
  }

  try {
    const response = await fetch(path, {
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    backendOnline = true;
    updateBackendStatus();
    return response.status === 204 ? {} : response.json();
  } catch (error) {
    backendOnline = false;
    updateBackendStatus("Backend kapalı: python server.py ile açınca kayıt, log ve Word indirme aktif olur.");
    return null;
  }
}

function queueStateSync(reason) {
  if (!canUseBackend() || SELF_TEST_MODE) {
    return;
  }
  clearTimeout(stateSyncTimer);
  stateSyncTimer = window.setTimeout(() => syncStateToBackend(reason), 450);
}

async function syncStateToBackend(reason = "state-sync") {
  await apiJson("/api/state", {
    method: "POST",
    body: JSON.stringify({
      reason,
      actor: currentUser()?.email || "anonim",
      payload: state,
    }),
  });
}

async function logAction(action, detail = {}) {
  await apiJson("/api/log", {
    method: "POST",
    body: JSON.stringify({
      actor: currentUser()?.email || detail.actor || "anonim",
      action,
      detail,
    }),
  });
}

async function bootstrapBackend() {
  if (!canUseBackend() || SELF_TEST_MODE) {
    updateBackendStatus("Statik mod: Word indirme ve SQLite log için python server.py ile aç.");
    return;
  }

  const health = await apiJson("/api/health");
  if (!health?.ok) {
    return;
  }

  const saved = await apiJson("/api/state");
  if (saved?.payload) {
    state = normalizeState(saved.payload);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    render();
  } else {
    await syncStateToBackend("initial-browser-state");
  }
  await refreshLogs();
}

function saveState() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  queueStateSync("saveState");
}

function loadSession() {
  const saved = localStorage.getItem(SESSION_KEY);
  if (!saved) {
    return { userId: null, projectId: null, view: "admin", documentId: "fr01" };
  }

  try {
    return { view: "admin", documentId: "fr01", ...JSON.parse(saved) };
  } catch {
    return { userId: null, projectId: null, view: "admin", documentId: "fr01" };
  }
}

function saveSession() {
  localStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

function currentUser() {
  return state.users.find((user) => user.id === session.userId);
}

function currentProject() {
  return state.projects.find((project) => project.id === session.projectId);
}

function projectsForUser(userId) {
  return state.projects.filter((project) => project.memberIds.includes(userId));
}

function pendingNotificationsForUser(userId) {
  return state.invites.filter((invite) => invite.userId === userId && invite.status === "pending");
}

function profileFor(project, userId) {
  return project?.memberProfiles?.[userId] || null;
}

function roleFor(project, userId) {
  if (!project || !userId) {
    return "none";
  }
  if (project.ownerId === userId) {
    return "owner";
  }
  return profileFor(project, userId)?.role || "none";
}

function canManageProject() {
  const role = roleFor(currentProject(), session.userId);
  return role === "owner" || role === "admin";
}

function canAssignTasks() {
  const role = roleFor(currentProject(), session.userId);
  return role === "owner" || role === "admin" || role === "lead";
}

function isProjectManager() {
  const role = roleFor(currentProject(), session.userId);
  return role === "owner" || role === "admin";
}

function canEditTemplates() {
  return roleFor(currentProject(), session.userId) === "owner";
}

function isSystemAdmin() {
  return currentUser()?.email.toLowerCase() === "admin@proje.local";
}

function safeOpenDialog(dialog) {
  if (!dialog.open) {
    dialog.showModal();
  }
}

function closeAllDialogs() {
  [taskDialog, memberDialog, projectDialog, eventDialog, templateDialog].forEach((dialog) => {
    if (dialog.open) {
      dialog.close();
    }
  });
}

function taskBelongsToCurrentProject(task) {
  return Boolean(task && currentProject()?.id === task.projectId);
}

function userName(userId) {
  return state.users.find((user) => user.id === userId)?.name || "Bilinmeyen";
}

function userEmail(userId) {
  return state.users.find((user) => user.id === userId)?.email || "";
}

function setAuthTab(tabName) {
  const isLogin = tabName === "login";
  loginTab.classList.toggle("active", isLogin);
  registerTab.classList.toggle("active", !isLogin);
  loginForm.classList.toggle("hidden", !isLogin);
  registerForm.classList.toggle("hidden", isLogin);
  authMessage.textContent = "";
}

function setMessage(message, type = "error") {
  authMessage.textContent = message;
  authMessage.dataset.type = type;
}

function signIn(email, password) {
  const normalized = email.trim().toLowerCase();
  const user = state.users.find(
    (item) => item.email.toLowerCase() === normalized && item.password === password,
  );

  if (!user) {
    setMessage("Mail veya şifre hatalı.");
    return;
  }

  session = {
    userId: user.id,
    projectId: null,
    view: "project-select",
    documentId: "fr01",
  };
  saveSession();
  logAction("auth.login", { actor: user.email });
  render();
}

function registerUser(name, email, password) {
  const normalized = email.trim().toLowerCase();
  const exists = state.users.some((user) => user.email.toLowerCase() === normalized);

  if (exists) {
    setMessage("Bu mail ile kayıtlı bir kullanıcı var.");
    return;
  }

  const user = {
    id: uid(),
    name: name.trim(),
    email: normalized,
    password,
  };
  state.users.push(user);
  saveState();
  session = { userId: user.id, projectId: null, view: "project-select", documentId: "fr01" };
  saveSession();
  logAction("auth.register", { actor: user.email });
  render();
}

function logout() {
  logAction("auth.logout", { actor: currentUser()?.email || "anonim" });
  session = { userId: null, projectId: null, view: "admin", documentId: "fr01" };
  saveSession();
  render();
}

function render() {
  const user = currentUser();
  authView.classList.toggle("hidden", Boolean(user));
  appView.classList.toggle("hidden", !user);

  if (!user) {
    return;
  }

  const projects = projectsForUser(user.id);
  if (session.projectId && !projects.some((project) => project.id === session.projectId)) {
    session.projectId = null;
    session.view = "project-select";
    saveSession();
  }

  currentUserLabel.textContent = `${user.name} · ${user.email}`;
  renderProjectOptions(projects);
  renderProjectGate(projects);
  const selectingProject = shouldShowProjectGate(projects);
  appView.classList.toggle("project-select-mode", selectingProject);
  projectGate.classList.toggle("hidden", !selectingProject);
  workspaceView.classList.toggle("hidden", selectingProject);
  document.querySelector(".sidebar").classList.toggle("hidden", selectingProject);

  if (selectingProject) {
    return;
  }

  normalizeActiveView();
  renderActiveView();
  renderHeader();
  renderAdmin();
  renderDashboard();
  renderMyWork();
  renderTasks();
  renderInbox();
  renderTeam();
  renderDocuments();
  renderCalendar();
  renderBusinessModules();
  renderDialogs();
}

function renderProjectOptions(projects) {
  projectSelect.innerHTML = "";
  const project = currentProject();
  activeProjectLabel.textContent = project?.name || "Proje seç";

  if (projects.length === 0) {
    const option = document.createElement("option");
    option.textContent = "Henüz proje yok";
    option.value = "";
    projectSelect.append(option);
    return;
  }

  projects.forEach((project) => {
    const option = document.createElement("option");
    option.value = project.id;
    option.textContent = project.name;
    option.selected = project.id === session.projectId;
    projectSelect.append(option);
  });
}

function shouldShowProjectGate(projects) {
  return session.view === "project-select" || !session.projectId || projects.length === 0;
}

function renderProjectGate(projects) {
  projectGateList.innerHTML = "";
  gateNewProjectButton.classList.toggle("hidden", !isSystemAdmin());

  if (projects.length === 0) {
    const empty = document.createElement("article");
    empty.className = "project-choice-card empty-choice";
    empty.innerHTML = `
      <strong></strong>
      <p></p>
    `;
    empty.querySelector("strong").textContent = isSystemAdmin()
      ? "Henüz proje yok"
      : "Henüz bir projeye eklenmedin";
    empty.querySelector("p").textContent = isSystemAdmin()
      ? "Yeni proje oluşturarak başlayabilirsin."
      : "Bir admin seni projeye eklediğinde burada görünecek.";
    projectGateList.append(empty);
    return;
  }

  projects.forEach((project) => {
    const tasks = state.tasks.filter((task) => task.projectId === project.id);
    const card = document.createElement("button");
    card.className = "project-choice-card";
    card.type = "button";
    card.innerHTML = `
      <span></span>
      <strong></strong>
      <p></p>
      <small></small>
    `;
    card.querySelector("span").textContent = roleLabel(roleFor(project, session.userId));
    card.querySelector("strong").textContent = project.name;
    card.querySelector("p").textContent = project.description || "Açıklama eklenmedi.";
    card.querySelector("small").textContent = `${validProjectMemberIds(project).length} üye · ${tasks.length} görev`;
    card.addEventListener("click", () => selectProject(project.id));
    projectGateList.append(card);
  });
}

function selectProject(projectId) {
  const project = projectsForUser(session.userId).find((item) => item.id === projectId);
  if (!project) {
    return false;
  }

  session.projectId = project.id;
  session.view = isProjectManager() ? "admin" : "dashboard";
  saveSession();
  logAction("project.selected", { projectId: project.id, projectName: project.name });
  render();
  return true;
}

function showProjectChooser() {
  closeAllDialogs();
  session.projectId = null;
  session.view = "project-select";
  saveSession();
  render();
}

function renderHeader() {
  const project = currentProject();
  const role = roleFor(project, session.userId);

  if (!project) {
    projectTitle.textContent = "Proje yok";
    projectRoleLabel.textContent = isSystemAdmin()
      ? "Yeni proje oluşturabilir veya ekip kurabilirsin"
      : "Bir adminin seni projeye eklemesini bekleyebilirsin";
    openTaskButton.disabled = true;
    openMemberButton.disabled = true;
    openEventButton.disabled = true;
    openTaskButton.classList.add("hidden");
    openMemberButton.classList.add("hidden");
    openEventButton.classList.add("hidden");
    openTemplateEditorButton.disabled = true;
    openTemplateEditorButton.classList.add("hidden");
    newProjectButton.classList.toggle("hidden", !isSystemAdmin());
    return;
  }

  projectTitle.textContent = project.name;
  projectRoleLabel.textContent = `${roleLabel(role)} · ${profileFor(project, session.userId)?.team || "Yönetim"}`;
  openTaskButton.disabled = !canAssignTasks();
  openMemberButton.disabled = !canManageProject();
  openEventButton.disabled = !canAssignTasks();
  openTaskButton.classList.toggle("hidden", !canAssignTasks());
  openMemberButton.classList.toggle("hidden", !canManageProject());
  openEventButton.classList.toggle("hidden", !canAssignTasks());
  openTemplateEditorButton.disabled = !canEditTemplates();
  openTemplateEditorButton.classList.toggle("hidden", !canEditTemplates());
  newProjectButton.classList.toggle("hidden", !isSystemAdmin());
}

function normalizeActiveView() {
  const validViews = new Set([
    "project-select",
    "admin",
    "dashboard",
    "mywork",
    "tasks",
    "inbox",
    "team",
    "docs",
    "calendar",
    "crm",
    "feed",
    "reports",
  ]);

  if (!validViews.has(session.view)) {
    session.view = isProjectManager() ? "admin" : "dashboard";
    saveSession();
    return;
  }

  if ((session.view === "admin" || session.view === "reports") && !isProjectManager()) {
    session.view = "dashboard";
    saveSession();
  }
}

function renderActiveView() {
  const view = session.view || "admin";
  adminView.classList.toggle("hidden", view !== "admin");
  dashboardView.classList.toggle("hidden", view !== "dashboard");
  myWorkView.classList.toggle("hidden", view !== "mywork");
  tasksView.classList.toggle("hidden", view !== "tasks");
  inboxView.classList.toggle("hidden", view !== "inbox");
  teamView.classList.toggle("hidden", view !== "team");
  docsView.classList.toggle("hidden", view !== "docs");
  calendarView.classList.toggle("hidden", view !== "calendar");
  crmView.classList.toggle("hidden", view !== "crm");
  feedView.classList.toggle("hidden", view !== "feed");
  reportsView.classList.toggle("hidden", view !== "reports");

  navLinks.forEach((link) => {
    if (link.classList.contains("management-only")) {
      link.classList.toggle("hidden", !isProjectManager());
    }
    link.classList.toggle("active", link.dataset.view === view);
  });
}

function renderAdmin() {
  renderNotifications();
  renderProjectList();
  renderAdminUsers();
  renderAdminLogs();
}

function renderAdminUsers() {
  const list = document.querySelector("#adminUserList");
  const label = document.querySelector("#adminUserCountLabel");
  if (!list || !label) {
    return;
  }

  label.textContent = `${state.users.length} kullanıcı`;
  list.innerHTML = "";
  state.users.forEach((user) => {
    const activeProject = currentProject();
    const isMember = activeProject?.memberIds.includes(user.id);
    const item = document.createElement("article");
    item.className = "admin-list-item";
    item.innerHTML = `
      <div>
        <strong></strong>
        <span></span>
      </div>
      <div class="row-actions">
        <button class="secondary-action small" data-remove-project type="button">Projeden çıkar</button>
        <button class="secondary-action small danger-action" data-delete-user type="button">Sistemden sil</button>
      </div>
    `;
    item.querySelector("strong").textContent = user.name;
    item.querySelector("span").textContent = `${user.email} · ${isMember ? "bu projede" : "projede değil"}`;

    const removeProjectButton = item.querySelector("[data-remove-project]");
    removeProjectButton.disabled = !isMember || user.id === activeProject?.ownerId || user.id === session.userId;
    removeProjectButton.addEventListener("click", () => removeUserFromProject(user.id));

    const deleteButton = item.querySelector("[data-delete-user]");
    deleteButton.disabled = !isSystemAdmin() || user.id === session.userId || state.projects.some((project) => project.ownerId === user.id);
    deleteButton.addEventListener("click", () => deleteSystemUser(user.id));
    list.append(item);
  });
}

function renderAdminLogs() {
  const list = document.querySelector("#adminLogList");
  if (!list) {
    return;
  }
  list.innerHTML = "";

  if (!canUseBackend()) {
    list.append(emptyState("Logları görmek için siteyi python server.py ile aç."));
    return;
  }

  if (latestLogs.length === 0) {
    list.append(emptyState(backendOnline ? "Henüz log yok." : "Backend bağlantısı bekleniyor."));
    return;
  }

  latestLogs.slice(0, 30).forEach((log) => {
    const item = document.createElement("article");
    item.className = "log-item";
    item.innerHTML = `
      <strong></strong>
      <span></span>
      <p></p>
    `;
    item.querySelector("strong").textContent = log.action;
    item.querySelector("span").textContent = `${log.actor || "anonim"} · ${formatDateTime(log.ts)}`;
    item.querySelector("p").textContent = summarizeLogDetail(log.detail);
    list.append(item);
  });
}

function summarizeLogDetail(detail) {
  if (!detail) {
    return "Detay yok.";
  }
  if (typeof detail === "string") {
    return detail;
  }
  return Object.entries(detail)
    .map(([key, value]) => `${key}: ${typeof value === "object" ? JSON.stringify(value) : value}`)
    .join(" · ")
    .slice(0, 220);
}

async function refreshLogs() {
  const result = await apiJson("/api/logs");
  latestLogs = Array.isArray(result?.logs) ? result.logs : latestLogs;
  renderAdminLogs();
}

function renderNotifications() {
  const invitePanel = document.querySelector("#invitePanel");
  const inviteList = document.querySelector("#inviteList");
  const notifications = pendingNotificationsForUser(session.userId);
  invitePanel.classList.toggle("hidden", notifications.length === 0);
  inviteList.innerHTML = "";

  notifications.forEach((invite) => {
    const project = state.projects.find((item) => item.id === invite.projectId);
    const item = document.createElement("article");
    item.className = "invite-card";
    item.innerHTML = `
      <div>
        <strong></strong>
        <span></span>
        <p></p>
      </div>
      <button class="primary-action small" type="button">Kabul et</button>
    `;
    item.querySelector("strong").textContent = project?.name || "Silinmiş proje";
    item.querySelector("span").textContent = `${roleLabel(invite.role)} · ${invite.team}`;
    item.querySelector("p").textContent = invite.note || "Projeye erişim bildirimi.";
    item.querySelector("button").addEventListener("click", () => acceptInvite(invite.id));
    inviteList.append(item);
  });
}

function renderProjectList() {
  const list = document.querySelector("#adminProjectList");
  const label = document.querySelector("#projectCountLabel");
  const userProjects = projectsForUser(session.userId);
  label.textContent = `${userProjects.length} proje`;
  list.innerHTML = "";

  if (userProjects.length === 0) {
    list.append(emptyState("Henüz bir projede değilsin. Sistem admini proje oluşturabilir veya bir admin seni ekleyebilir."));
    return;
  }

  userProjects.forEach((project) => {
    const tasks = state.tasks.filter((task) => task.projectId === project.id);
    const pending = state.invites.filter(
      (invite) => invite.projectId === project.id && invite.status === "pending",
    );
    const item = document.createElement("article");
    item.className = "project-card";
    item.innerHTML = `
      <div>
        <strong></strong>
        <p></p>
        <div class="task-meta">
          <span></span>
          <span></span>
          <span></span>
        </div>
      </div>
      <button class="secondary-action small" type="button">Aç</button>
    `;
    item.querySelector("strong").textContent = project.name;
    item.querySelector("p").textContent = project.description || "Açıklama eklenmedi.";
    const chips = item.querySelectorAll(".task-meta span");
    chips[0].textContent = `${validProjectMemberIds(project).length} üye`;
    chips[1].textContent = `${tasks.length} görev`;
    chips[2].textContent = `${pending.length} bildirim`;
    item.querySelector("button").addEventListener("click", () => {
      session.projectId = project.id;
      session.view = "dashboard";
      saveSession();
      render();
    });
    list.append(item);
  });
}

function acceptInvite(inviteId) {
  const invite = state.invites.find((item) => item.id === inviteId);
  const project = state.projects.find((item) => item.id === invite?.projectId);
  if (!invite || !project || invite.userId !== session.userId || invite.status !== "pending") {
    return;
  }

  addUserToProject(project, invite.userId, invite.role, invite.team);
  invite.status = "accepted";
  session.projectId = project.id;
  saveState();
  saveSession();
  render();
}

function projectTasks() {
  const project = currentProject();
  if (!project) {
    return [];
  }
  return state.tasks.filter((task) => task.projectId === project.id);
}

function projectEvents() {
  const project = currentProject();
  if (!project) {
    return [];
  }
  return state.calendarEvents
    .filter((event) => event.projectId === project.id)
    .sort((a, b) => new Date(a.date) - new Date(b.date));
}

function renderDashboard() {
  const project = currentProject();
  const tasks = projectTasks();
  const approved = tasks.filter((task) => task.status === "approved");
  const review = tasks.filter((task) => task.status === "review");

  document.querySelector("#openTasks").textContent = tasks.filter((task) => task.status !== "approved").length;
  document.querySelector("#reviewTasks").textContent = review.length;
  document.querySelector("#approvedTasks").textContent = approved.length;
  document.querySelector("#calendarCount").textContent = projectEvents().length;

  const recent = tasks
    .flatMap((task) =>
      task.submissions.map((submission) => ({
        task,
        submission,
      })),
    )
    .sort((a, b) => new Date(b.submission.submittedAt) - new Date(a.submission.submittedAt))
    .slice(0, 5);

  const recentSubmissions = document.querySelector("#recentSubmissions");
  recentSubmissions.innerHTML = "";
  if (recent.length === 0) {
    recentSubmissions.append(emptyState("Henüz teslim yüklenmedi."));
  } else {
    recent.forEach(({ task, submission }) => {
      const item = document.createElement("article");
      item.className = "submission-item";
      item.innerHTML = `
        <strong></strong>
        <span></span>
        <p></p>
      `;
      item.querySelector("strong").textContent = task.title;
      item.querySelector("span").textContent = `${userName(submission.userId)} · ${formatDateTime(
        submission.submittedAt,
      )}`;
      item.querySelector("p").textContent = submission.fileName
        ? `${submission.fileName} yüklendi`
        : submission.note;
      recentSubmissions.append(item);
    });
  }

  renderTeamList(document.querySelector("#teamPreview"), { compact: true });
}

function renderTasks() {
  const tasks = projectTasks();
  const buckets = {
    todo: document.querySelector("#todoTasks"),
    review: document.querySelector("#reviewTaskList"),
    approved: document.querySelector("#approvedTaskList"),
  };

  Object.values(buckets).forEach((bucket) => {
    bucket.innerHTML = "";
  });

  const grouped = {
    todo: tasks.filter((task) => task.status === "todo" || task.status === "changes"),
    review: tasks.filter((task) => task.status === "review"),
    approved: tasks.filter((task) => task.status === "approved"),
  };

  Object.entries(grouped).forEach(([status, items]) => {
    if (items.length === 0) {
      buckets[status].append(emptyState("Bu alanda görev yok."));
      return;
    }
    items.forEach((task) => buckets[status].append(createTaskCard(task)));
  });
}

function renderMyWork() {
  const list = document.querySelector("#myWorkList");
  const count = document.querySelector("#myWorkCount");
  const tasks = projectTasks()
    .filter((task) => task.assigneeId === session.userId && task.status !== "approved")
    .sort((a, b) => priorityRank(b.priority) - priorityRank(a.priority));

  count.textContent = `${tasks.length} görev`;
  list.innerHTML = "";

  if (tasks.length === 0) {
    list.append(emptyState("Sana atanmış açık görev yok."));
    return;
  }

  tasks.forEach((task) => list.append(createTaskCard(task)));
}

function renderInbox() {
  const list = document.querySelector("#inboxList");
  const project = currentProject();
  list.innerHTML = "";

  if (!project) {
    list.append(emptyState("Gelen kutusu için proje seç."));
    return;
  }

  const taskEvents = projectTasks().flatMap((task) => [
    ...task.comments.map((comment) => ({
      id: comment.id,
      userId: comment.userId,
      type: "Yorum",
      text: `${task.title}: ${comment.text}`,
      createdAt: comment.createdAt,
    })),
    ...task.submissions.map((submission) => ({
      id: submission.id,
      userId: submission.userId,
      type: "Teslim",
      text: `${task.title}: ${submission.note}`,
      createdAt: submission.submittedAt,
    })),
  ]);

  const inbox = taskEvents
    .filter((event) => event.userId !== session.userId)
    .sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));

  if (inbox.length === 0) {
    list.append(emptyState("Yeni yorum veya teslim bildirimi yok."));
    return;
  }

  inbox.slice(0, 20).forEach((event) => {
    const row = document.createElement("article");
    row.className = "feed-item";
    row.innerHTML = `
      <span class="avatar"></span>
      <div>
        <strong></strong>
        <p></p>
        <small></small>
      </div>
    `;
    row.querySelector(".avatar").textContent = initials(userName(event.userId));
    row.querySelector("strong").textContent = event.type;
    row.querySelector("p").textContent = event.text;
    row.querySelector("small").textContent = `${userName(event.userId)} · ${formatDateTime(
      event.createdAt,
    )}`;
    list.append(row);
  });
}

function createTaskCard(task) {
  const template = document.querySelector("#taskCardTemplate");
  const card = template.content.firstElementChild.cloneNode(true);
  const latestSubmission = task.submissions[task.submissions.length - 1];
  const isAssignee = task.assigneeId === session.userId;
  const canReview = canManageProject() && task.status === "review";

  card.querySelector("[data-task-title]").textContent = task.title;
  card.querySelector("[data-task-status]").textContent = statusLabel(task.status);
  card.querySelector("[data-task-status]").dataset.status = task.status;
  card.querySelector("[data-task-description]").textContent = task.description;
  card.querySelector("[data-task-assignee]").textContent = userName(task.assigneeId);
  card.querySelector("[data-task-due]").textContent = task.dueDate
    ? `Teslim: ${formatDate(task.dueDate)}`
    : "Tarih yok";
  card.querySelector("[data-task-team]").textContent = task.team || "Yönetim";
  card.querySelector("[data-task-priority]").textContent = priorityLabel(task.priority);
  card.querySelector("[data-task-priority]").dataset.priority = task.priority;
  card.querySelector("[data-task-label]").textContent = task.label || "Etiket yok";
  card.querySelector("[data-task-estimate]").textContent = task.estimateHours
    ? `${task.estimateHours} saat`
    : "Süre yok";

  const checklistArea = card.querySelector("[data-checklist-area]");
  renderTaskChecklist(task, checklistArea);

  const submissionArea = card.querySelector("[data-submission-area]");
  if (latestSubmission) {
    submissionArea.append(createSubmissionPreview(task, latestSubmission));
  }

  if (isAssignee && task.status !== "approved") {
    submissionArea.append(createSubmitForm(task));
  }

  if (canReview) {
    const reviewActions = document.createElement("div");
    reviewActions.className = "review-actions";

    const approveButton = document.createElement("button");
    approveButton.className = "primary-action small";
    approveButton.type = "button";
    approveButton.textContent = "Onayla";
    approveButton.addEventListener("click", () => updateTaskStatus(task.id, "approved"));

    const changesButton = document.createElement("button");
    changesButton.className = "secondary-action small";
    changesButton.type = "button";
    changesButton.textContent = "Düzeltme iste";
    changesButton.addEventListener("click", () => updateTaskStatus(task.id, "changes"));

    reviewActions.append(approveButton, changesButton);
    submissionArea.append(reviewActions);
  }

  renderTaskComments(task, card.querySelector("[data-comment-area]"));

  return card;
}

function renderTaskChecklist(task, container) {
  container.innerHTML = "";
  if (!task.checklist.length) {
    return;
  }

  const doneCount = task.checklist.filter((item) => item.done).length;
  const header = document.createElement("div");
  header.className = "checklist-header";
  header.innerHTML = `
    <strong></strong>
    <span></span>
  `;
  header.querySelector("strong").textContent = "Checklist";
  header.querySelector("span").textContent = `${doneCount}/${task.checklist.length}`;
  container.append(header);

  task.checklist.forEach((item) => {
    const label = document.createElement("label");
    label.className = "checklist-item";
    label.innerHTML = `
      <input type="checkbox" />
      <span></span>
    `;
    const checkbox = label.querySelector("input");
    checkbox.checked = item.done;
    checkbox.disabled = task.assigneeId !== session.userId && !canAssignTasks();
    checkbox.addEventListener("change", () => toggleChecklistItem(task.id, item.id));
    label.querySelector("span").textContent = item.text;
    container.append(label);
  });
}

function toggleChecklistItem(taskId, itemId) {
  const task = state.tasks.find((item) => item.id === taskId);
  const checklistItem = task?.checklist.find((item) => item.id === itemId);
  if (!task || !checklistItem) {
    return false;
  }

  if (!taskBelongsToCurrentProject(task) || (task.assigneeId !== session.userId && !canAssignTasks())) {
    return false;
  }

  checklistItem.done = !checklistItem.done;
  saveState();
  render();
  return true;
}

function renderTaskComments(task, container) {
  container.innerHTML = "";
  const latest = task.comments.slice(-2);
  if (latest.length) {
    const list = document.createElement("div");
    list.className = "comment-list";
    latest.forEach((comment) => {
      const item = document.createElement("article");
      item.className = "comment-item";
      item.innerHTML = `
        <strong></strong>
        <p></p>
      `;
      item.querySelector("strong").textContent = `${userName(comment.userId)} · ${formatDateTime(
        comment.createdAt,
      )}`;
      item.querySelector("p").textContent = comment.text;
      list.append(item);
    });
    container.append(list);
  }

  const canComment = currentProject()?.memberIds.includes(session.userId);
  if (!canComment) {
    return;
  }

  const form = document.createElement("form");
  form.className = "comment-form";
  form.innerHTML = `
    <input type="text" placeholder="Yorum ekle" />
    <button class="secondary-action small" type="submit">Yorum</button>
  `;
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    addTaskComment(task.id, form.querySelector("input").value);
  });
  container.append(form);
}

function addTaskComment(taskId, text) {
  const task = state.tasks.find((item) => item.id === taskId);
  const cleanText = text.trim();
  if (
    !taskBelongsToCurrentProject(task) ||
    !cleanText ||
    !validProjectMemberIds(currentProject()).includes(session.userId)
  ) {
    return false;
  }

  task.comments.push({
    id: uid(),
    userId: session.userId,
    text: cleanText,
    createdAt: new Date().toISOString(),
  });
  saveState();
  render();
  return true;
}

function createSubmissionPreview(task, submission) {
  const wrapper = document.createElement("div");
  wrapper.className = "submission-preview";

  const title = document.createElement("strong");
  title.textContent = "Son teslim";

  const note = document.createElement("p");
  note.textContent = submission.note || "Not eklenmedi.";

  const meta = document.createElement("span");
  meta.textContent = `${userName(submission.userId)} · ${formatDateTime(submission.submittedAt)}`;

  wrapper.append(title, note, meta);

  if (submission.fileName) {
    const link = document.createElement("a");
    link.textContent = submission.fileName;
    link.href = submission.fileData || "#";
    link.download = submission.fileName;
    if (!submission.fileData) {
      link.removeAttribute("download");
    }
    wrapper.append(link);
  }

  if (task.status === "changes") {
    const warning = document.createElement("span");
    warning.className = "revision-note";
    warning.textContent = "Düzeltme istenmiş.";
    wrapper.append(warning);
  }

  return wrapper;
}

function createSubmitForm(task) {
  const form = document.createElement("form");
  form.className = "submit-form";
  form.innerHTML = `
    <label>
      Teslim notu
      <textarea rows="3" required></textarea>
    </label>
    <label>
      Dosya
      <input type="file" />
    </label>
    <button class="primary-action small" type="submit">Teslim yükle</button>
    <span class="inline-message" role="status"></span>
  `;

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const note = form.querySelector("textarea").value.trim();
    const file = form.querySelector("input[type='file']").files[0];
    const message = form.querySelector(".inline-message");

    if (!note) {
      message.textContent = "Teslim notu gerekli.";
      return;
    }

    if (file && file.size > MAX_FILE_SIZE) {
      message.textContent = "Dosya 2 MB altında olmalı.";
      return;
    }

    const fileData = file ? await fileToDataUrl(file) : "";
    submitTask(task.id, {
      note,
      fileName: file?.name || "",
      fileData,
    });
  });

  return form;
}

function submitTask(taskId, submission) {
  const task = state.tasks.find((item) => item.id === taskId);
  if (!taskBelongsToCurrentProject(task) || task.assigneeId !== session.userId || task.status === "approved") {
    return false;
  }

  task.submissions.push({
    id: uid(),
    userId: session.userId,
    note: submission.note,
    fileName: submission.fileName,
    fileData: submission.fileData,
    submittedAt: new Date().toISOString(),
  });
  task.status = "review";
  saveState();
  logAction("task.submitted", {
    taskId,
    title: task.title,
    fileName: submission.fileName || "",
  });
  render();
  return true;
}

function updateTaskStatus(taskId, status) {
  const task = state.tasks.find((item) => item.id === taskId);
  if (!taskBelongsToCurrentProject(task) || !canManageProject() || !["approved", "changes"].includes(status)) {
    return false;
  }
  task.status = status;
  saveState();
  logAction("task.status.updated", { taskId, title: task.title, status });
  render();
  return true;
}

function renderTeam() {
  renderTeamList(document.querySelector("#teamFullList"), { compact: false });
}

function renderTeamList(container, options) {
  const project = currentProject();
  container.innerHTML = "";

  const memberIds = validProjectMemberIds(project);

  if (!project || memberIds.length === 0) {
    container.append(emptyState("Bu projede ekip üyesi yok."));
    return;
  }

  memberIds.forEach((userId) => {
    const user = state.users.find((item) => item.id === userId);
    if (!user) {
      return;
    }

    const profile = profileFor(project, user.id);
    const row = document.createElement("article");
    row.className = "member-row";
    row.innerHTML = `
      <span class="avatar"></span>
      <div>
        <strong></strong>
        <span></span>
      </div>
      <span class="role-pill"></span>
      <button class="secondary-action small member-task-button" type="button">Görev ata</button>
    `;
    row.querySelector(".avatar").textContent = initials(user.name);
    row.querySelector("strong").textContent = user.name;
    row.querySelector("div span").textContent = options.compact
      ? `${profile?.team || "Yönetim"}`
      : `${user.email} · ${profile?.team || "Yönetim"} · ${profile?.title || "Üye"}`;
    row.querySelector(".role-pill").textContent = roleLabel(roleFor(project, user.id));
    const taskButton = row.querySelector(".member-task-button");
    const canAssignToThisUser =
      canAssignTasks() &&
      (roleFor(project, session.userId) !== "lead" ||
        profileFor(project, session.userId)?.team === profile?.team);
    taskButton.classList.toggle("hidden", options.compact || !canAssignToThisUser);
    taskButton.addEventListener("click", () => openTaskDialogForUser(user.id));
    container.append(row);
  });
}

function openTaskDialogForUser(userId = "") {
  if (!canAssignTasks()) {
    return;
  }

  taskForm.reset();
  document.querySelector("#taskPriorityInput").value = "normal";
  document.querySelector("#taskDueInput").min = new Date().toISOString().slice(0, 10);
  renderAssigneeOptions();
  const assigneeSelect = document.querySelector("#taskAssigneeInput");
  if (userId && [...assigneeSelect.options].some((option) => option.value === userId)) {
    assigneeSelect.value = userId;
  }
  safeOpenDialog(taskDialog);
}

function renderDocuments() {
  renderDocumentCards();
  renderDocumentForm();
  setBackendMessage(
    canUseBackend()
      ? "Word işlemleri için backend bağlantısı kontrol ediliyor."
      : "Word indirme için siteyi python server.py ile aç.",
    canUseBackend() ? "info" : "warning",
  );
}

function renderDocumentCards() {
  const list = document.querySelector("#documentList");
  const project = currentProject();
  list.innerHTML = "";

  if (!project) {
    list.append(emptyState("Belge doldurmak için proje seç."));
    return;
  }

  state.documentTemplates.forEach((template) => {
    const key = documentKey(project.id, template.id);
    const saved = state.documents[key];
    const button = document.createElement("button");
    button.className = "document-card";
    button.type = "button";
    button.innerHTML = `
      <span></span>
      <strong></strong>
      <small></small>
    `;
    button.classList.toggle("active", session.documentId === template.id);
    button.querySelector("span").textContent = template.fileName;
    button.querySelector("strong").textContent = template.title;
    button.querySelector("small").textContent = saved
      ? `Son kayıt: ${formatDateTime(saved.updatedAt)}`
      : "Henüz doldurulmadı";
    button.addEventListener("click", () => {
      session.documentId = template.id;
      saveSession();
      renderDocuments();
    });
    list.append(button);
  });
}

function renderDocumentForm() {
  const project = currentProject();
  const template = state.documentTemplates.find((item) => item.id === session.documentId);
  documentForm.innerHTML = "";

  if (!project || !template) {
    documentForm.append(emptyState("Belge seç."));
    return;
  }

  const key = documentKey(project.id, template.id);
  const saved = state.documents[key] || { answers: {} };
  const header = document.createElement("div");
  header.className = "document-form-header";
  header.innerHTML = `
    <div>
      <h3></h3>
      <p></p>
    </div>
  `;
  header.querySelector("h3").textContent = template.title;
  header.querySelector("p").textContent = template.fileName;
  documentForm.append(header);

  template.questions.forEach((question, index) => {
    const label = document.createElement("label");
    label.textContent = question;
    const textarea = document.createElement("textarea");
    textarea.rows = 3;
    textarea.name = `q${index}`;
    textarea.value = saved.answers?.[`q${index}`] || "";
    label.append(textarea);
    documentForm.append(label);
  });

  const actions = document.createElement("div");
  actions.className = "form-actions";
  const saveButton = document.createElement("button");
  saveButton.className = "primary-action";
  saveButton.type = "submit";
  saveButton.textContent = "Belgeyi kaydet";
  const meta = document.createElement("span");
  meta.className = "inline-message";
  meta.textContent = saved.updatedAt
    ? `${userName(saved.updatedBy)} tarafından ${formatDateTime(saved.updatedAt)} kaydedildi`
    : "Herkes doldurabilir.";
  actions.append(saveButton, meta);
  documentForm.append(actions);
}

function saveDocumentAnswers() {
  const project = currentProject();
  const template = state.documentTemplates.find((item) => item.id === session.documentId);
  if (!project || !template) {
    return false;
  }

  const answers = {};
  template.questions.forEach((_, index) => {
    answers[`q${index}`] = documentForm.elements[`q${index}`]?.value || "";
  });

  state.documents[documentKey(project.id, template.id)] = {
    answers,
    updatedBy: session.userId,
    updatedAt: new Date().toISOString(),
  };
  saveState();
  logAction("document.saved", {
    projectId: project.id,
    projectName: project.name,
    templateId: template.id,
    template: template.fileName,
  });
  renderDocuments();
  return true;
}

function documentKey(projectId, documentId) {
  return `${projectId}:${documentId}`;
}

function currentDocumentPayload() {
  const project = currentProject();
  const template = state.documentTemplates.find((item) => item.id === session.documentId);
  if (!project || !template) {
    return null;
  }
  const key = documentKey(project.id, template.id);
  const saved = state.documents[key] || { answers: {} };
  const answers = {};
  template.questions.forEach((question, index) => {
    answers[`q${index}`] = documentForm.elements[`q${index}`]?.value ?? saved.answers?.[`q${index}`] ?? "";
  });
  return {
    projectId: project.id,
    projectName: project.name,
    templateId: template.id,
    title: template.title,
    fileName: template.fileName,
    questions: template.questions,
    answers,
    actor: currentUser()?.email || "",
  };
}

async function checkSelectedTemplate() {
  const payload = currentDocumentPayload();
  if (!payload) {
    setBackendMessage("Önce belge seç.", "error");
    return;
  }
  const result = await apiJson("/api/docx/check", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  if (!result) {
    setBackendMessage("Backend kapalı. Komut: python server.py", "warning");
    return;
  }
  setBackendMessage(
    result.ok
      ? `Şablon doğrulandı: ${result.fileName} (${result.sha256.slice(0, 12)})`
      : `Şablon bulunamadı: ${payload.fileName}`,
    result.ok ? "success" : "error",
  );
}

async function exportSelectedDocument() {
  const payload = currentDocumentPayload();
  if (!payload) {
    setBackendMessage("Önce belge seç.", "error");
    return;
  }
  saveDocumentAnswers();
  try {
    if (!canUseBackend() || SELF_TEST_MODE) {
      throw new Error("Backend kapalı");
    }
    const response = await fetch("/api/docx/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    backendOnline = true;
    updateBackendStatus();
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${payload.projectName}-${payload.title}`.replace(/[\\/:*?"<>|]+/g, "-") + ".docx";
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    setBackendMessage("Word dokümanı indirildi.", "success");
    logAction("document.exported", {
      projectId: payload.projectId,
      template: payload.fileName,
    });
  } catch (error) {
    backendOnline = false;
    updateBackendStatus("Backend kapalı: python server.py ile açınca Word indirme aktif olur.");
    setBackendMessage("Word indirme için backend gerekli. Komut: python server.py", "warning");
  }
}

async function uploadSelectedTemplate(file) {
  if (!file) {
    return;
  }
  if (!file.name.toLowerCase().endsWith(".docx")) {
    setBackendMessage("Sadece .docx şablon yüklenebilir.", "error");
    return;
  }
  const knownNames = new Set(documentTemplates.map((template) => template.fileName));
  if (!knownNames.has(file.name)) {
    setBackendMessage("Yüklenen şablon adı verilen Word dosyalarından biri olmalı.", "error");
    return;
  }
  const dataUrl = await fileToDataUrl(file);
  const result = await apiJson("/api/docx/upload", {
    method: "POST",
    body: JSON.stringify({
      fileName: file.name,
      dataBase64: dataUrl.split(",")[1],
      actor: currentUser()?.email || "",
    }),
  });
  setBackendMessage(
    result?.ok ? `Şablon yüklendi ve doğrulandı: ${file.name}` : "Şablon yüklemek için backend gerekli.",
    result?.ok ? "success" : "warning",
  );
  templateUploadInput.value = "";
}

function renderCalendar() {
  const list = document.querySelector("#calendarList");
  const events = projectEvents();
  list.innerHTML = "";

  if (events.length === 0) {
    list.append(emptyState("Takvime henüz giriş eklenmedi."));
    return;
  }

  events.forEach((event) => {
    const item = document.createElement("article");
    item.className = "calendar-item";
    item.innerHTML = `
      <time></time>
      <div>
        <strong></strong>
        <span></span>
        <p></p>
      </div>
    `;
    item.querySelector("time").textContent = formatDate(event.date);
    item.querySelector("strong").textContent = event.title;
    item.querySelector("span").textContent = `${event.type} · ${userName(event.createdBy)}`;
    item.querySelector("p").textContent = event.description || "Açıklama eklenmedi.";
    list.append(item);
  });
}

function renderBusinessModules() {
  renderCrm();
  renderFeed();
  renderReports();
}

function renderCrm() {
  const list = document.querySelector("#crmList");
  const project = currentProject();
  list.innerHTML = "";

  if (!project) {
    list.append(emptyState("CRM kayıtları için proje seç."));
    return;
  }

  const items = (state.crmItems || []).filter((item) => item.projectId === project.id);
  if (items.length === 0) {
    list.append(emptyState("Henüz CRM fırsatı yok."));
    return;
  }

  items.forEach((item) => {
    const card = document.createElement("article");
    card.className = "business-card";
    card.innerHTML = `
      <span></span>
      <strong></strong>
      <p></p>
      <small></small>
    `;
    card.querySelector("span").textContent = item.stage;
    card.querySelector("strong").textContent = item.title;
    card.querySelector("p").textContent = item.company;
    card.querySelector("small").textContent = `${item.value} · ${userName(item.ownerId)}`;
    list.append(card);
  });
}

function renderFeed() {
  const list = document.querySelector("#feedList");
  const project = currentProject();
  list.innerHTML = "";

  if (!project) {
    list.append(emptyState("Akış için proje seç."));
    return;
  }

  const feed = [
    ...(state.feedItems || []).filter((item) => item.projectId === project.id),
    ...projectTasks()
      .flatMap((task) =>
        task.submissions.map((submission) => ({
          id: submission.id,
          projectId: project.id,
          userId: submission.userId,
          type: "Teslim",
          text: `${task.title}: ${submission.note}`,
          createdAt: submission.submittedAt,
        })),
      ),
  ].sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));

  if (feed.length === 0) {
    list.append(emptyState("Henüz akış kaydı yok."));
    return;
  }

  feed.slice(0, 12).forEach((item) => {
    const row = document.createElement("article");
    row.className = "feed-item";
    row.innerHTML = `
      <span class="avatar"></span>
      <div>
        <strong></strong>
        <p></p>
        <small></small>
      </div>
    `;
    row.querySelector(".avatar").textContent = initials(userName(item.userId));
    row.querySelector("strong").textContent = item.type;
    row.querySelector("p").textContent = item.text;
    row.querySelector("small").textContent = `${userName(item.userId)} · ${formatDateTime(item.createdAt)}`;
    list.append(row);
  });
}

function renderReports() {
  const list = document.querySelector("#reportList");
  const project = currentProject();
  list.innerHTML = "";

  if (!project) {
    list.append(emptyState("Rapor için proje seç."));
    return;
  }

  const tasks = projectTasks();
  const memberIds = validProjectMemberIds(project);
  const teams = [...new Set(memberIds.map((userId) => profileFor(project, userId)?.team || "Yönetim"))];
  const cards = [
    ["Ekip sayısı", teams.length],
    ["Üye sayısı", memberIds.length],
    ["Açık görev", tasks.filter((task) => task.status !== "approved").length],
    ["Onaylanan görev", tasks.filter((task) => task.status === "approved").length],
    ["CRM fırsatı", (state.crmItems || []).filter((item) => item.projectId === project.id).length],
    ["Takvim girişi", projectEvents().length],
  ];

  cards.forEach(([label, value]) => {
    const card = document.createElement("article");
    card.className = "business-card report-card";
    card.innerHTML = `
      <span></span>
      <strong></strong>
    `;
    card.querySelector("span").textContent = label;
    card.querySelector("strong").textContent = value;
    list.append(card);
  });
}

function renderDialogs() {
  renderAssigneeOptions();
  renderMemberOptions();
  renderTemplateOptions();
}

function renderAssigneeOptions() {
  const project = currentProject();
  const select = document.querySelector("#taskAssigneeInput");
  select.innerHTML = "";

  if (!project) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "Önce proje seç";
    select.append(option);
    select.disabled = true;
    return;
  }

  const currentProfile = profileFor(project, session.userId);
  let memberIds = validProjectMemberIds(project).filter((userId) => profileFor(project, userId));
  if (roleFor(project, session.userId) === "lead") {
    memberIds = memberIds.filter((userId) => {
      const profile = profileFor(project, userId);
      return profile?.team === currentProfile?.team;
    });
  }

  if (memberIds.length === 0) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "Görev atanabilecek kişi yok";
    select.append(option);
    select.disabled = true;
    return;
  }

  select.disabled = false;
  memberIds.forEach((userId) => {
    const profile = profileFor(project, userId);
    const option = document.createElement("option");
    option.value = userId;
    option.textContent = `${userName(userId)} · ${profile?.team || "Yönetim"}`;
    select.append(option);
  });
}

function renderMemberOptions() {
  const project = currentProject();
  const select = document.querySelector("#memberSelect");
  select.innerHTML = "";
  const unavailable = new Set([
    ...(project?.memberIds || []),
    ...state.invites
      .filter((invite) => invite.projectId === project?.id && invite.status === "pending")
      .map((invite) => invite.userId),
  ]);
  const availableUsers = state.users.filter((user) => !unavailable.has(user.id));

  if (!project || availableUsers.length === 0) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "Eklenebilecek kayıtlı kullanıcı yok";
    select.append(option);
    select.disabled = true;
    memberSubmitButton.disabled = true;
    return;
  }

  select.disabled = false;
  memberSubmitButton.disabled = false;
  availableUsers.forEach((user) => {
    const option = document.createElement("option");
    option.value = user.id;
    option.textContent = `${user.name} (${user.email})`;
    select.append(option);
  });
}

function renderTemplateOptions() {
  const select = document.querySelector("#templateSelect");
  select.innerHTML = "";
  state.documentTemplates.forEach((template) => {
    const option = document.createElement("option");
    option.value = template.id;
    option.textContent = template.title;
    option.selected = template.id === session.documentId;
    select.append(option);
  });
  renderTemplateQuestions();
}

function renderTemplateQuestions() {
  const selectedId = document.querySelector("#templateSelect").value || session.documentId;
  const template = state.documentTemplates.find((item) => item.id === selectedId);
  document.querySelector("#templateQuestionsInput").value = template?.questions.join("\n") || "";
}

function createTask(formData) {
  const project = currentProject();
  if (!project || !canAssignTasks() || !formData.assigneeId) {
    return false;
  }

  const title = formData.title.trim();
  const description = formData.description.trim();
  if (!title || !description || !project.memberIds.includes(formData.assigneeId)) {
    return false;
  }
  const priority = ALLOWED_PRIORITIES.has(formData.priority) ? formData.priority : "normal";

  const currentRole = roleFor(project, session.userId);
  const assigneeProfile = profileFor(project, formData.assigneeId);
  const currentProfile = profileFor(project, session.userId);
  if (!assigneeProfile || (currentRole === "lead" && assigneeProfile.team !== currentProfile?.team)) {
    return false;
  }
  const label = (formData.label || "").trim();
  const checklistText = formData.checklist || "";

  state.tasks.push({
    id: uid(),
    projectId: project.id,
    title,
    description,
    assigneeId: formData.assigneeId,
    createdBy: session.userId,
    dueDate: formData.dueDate,
    status: "todo",
    team: assigneeProfile?.team || "Yönetim",
    priority,
    label: label || assigneeProfile?.team || "Yönetim",
    estimateHours: Number(formData.estimateHours || 0),
    checklist: checklistText
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean)
      .map((text) => ({ id: uid(), text, done: false })),
    comments: [],
    submissions: [],
  });
  saveState();
  logAction("task.created", {
    projectId: project.id,
    title,
    assigneeId: formData.assigneeId,
    priority,
  });
  render();
  return true;
}

function addUserToProject(project, userId, role, team) {
  const safeRole = ALLOWED_ROLES.has(role) ? role : "member";
  const safeTeam = ALLOWED_TEAMS.has(team) ? team : "Yönetim";
  if (!project.memberIds.includes(userId)) {
    project.memberIds.push(userId);
  }

  project.memberProfiles[userId] = {
    role: safeRole,
    team: safeTeam,
    title: safeRole === "admin" ? "Admin" : safeRole === "lead" ? `${safeTeam} kaptanlığı` : `${safeTeam} ekibi`,
  };

  if (safeRole === "admin" && !project.adminIds.includes(userId)) {
    project.adminIds.push(userId);
  }

  if (safeRole !== "admin") {
    project.adminIds = project.adminIds.filter((adminId) => adminId !== userId);
  }
}

function validProjectMemberIds(project) {
  return (project?.memberIds || []).filter((userId) => state.users.some((user) => user.id === userId));
}

function addMemberToProject(userId, role, team, note) {
  const project = currentProject();
  if (!project || !canManageProject() || !userId) {
    return false;
  }
  if (!ALLOWED_ROLES.has(role) || !ALLOWED_TEAMS.has(team)) {
    return false;
  }

  const alreadyMember = project.memberIds.includes(userId);
  const hasPendingInvite = state.invites.some(
    (invite) => invite.projectId === project.id && invite.userId === userId && invite.status === "pending",
  );
  if (alreadyMember || hasPendingInvite) {
    return false;
  }

  addUserToProject(project, userId, role, team);
  state.invites.push({
    id: uid(),
    projectId: project.id,
    userId,
    role,
    team,
    note,
    status: "accepted",
    createdBy: session.userId,
    createdAt: new Date().toISOString(),
  });
  saveState();
  logAction("project.member.added", {
    projectId: project.id,
    userId,
    role,
    team,
  });
  render();
  return true;
}

function addSystemUser(name, email, password) {
  if (!isProjectManager()) {
    return false;
  }
  const cleanName = name.trim();
  const normalized = email.trim().toLowerCase();
  const cleanPassword = password.trim();
  if (!cleanName || !normalized || !cleanPassword || state.users.some((user) => user.email.toLowerCase() === normalized)) {
    return false;
  }
  const user = {
    id: uid(),
    name: cleanName,
    email: normalized,
    password: cleanPassword,
  };
  state.users.push(user);
  saveState();
  logAction("user.created", { userId: user.id, email: user.email });
  render();
  return true;
}

function fallbackAssignee(project) {
  return project?.memberIds.find((userId) => state.users.some((user) => user.id === userId)) || project?.ownerId || session.userId;
}

function removeUserFromProject(userId) {
  const project = currentProject();
  if (!project || !canManageProject() || userId === session.userId || userId === project.ownerId) {
    return false;
  }
  if (!project.memberIds.includes(userId)) {
    return false;
  }
  project.memberIds = project.memberIds.filter((memberId) => memberId !== userId);
  project.adminIds = project.adminIds.filter((adminId) => adminId !== userId);
  delete project.memberProfiles[userId];
  state.invites = state.invites.filter((invite) => !(invite.projectId === project.id && invite.userId === userId));
  const fallback = fallbackAssignee(project);
  state.tasks
    .filter((task) => task.projectId === project.id && task.assigneeId === userId)
    .forEach((task) => {
      task.assigneeId = fallback;
      task.comments.push({
        id: uid(),
        userId: session.userId,
        text: "Kullanıcı projeden çıkarıldığı için görev yeniden atandı.",
        createdAt: new Date().toISOString(),
      });
    });
  saveState();
  logAction("project.member.removed", { projectId: project.id, userId, fallback });
  render();
  return true;
}

function deleteSystemUser(userId) {
  if (!isSystemAdmin() || userId === session.userId || state.projects.some((project) => project.ownerId === userId)) {
    return false;
  }
  state.projects.forEach((project) => {
    project.memberIds = project.memberIds.filter((memberId) => memberId !== userId);
    project.adminIds = project.adminIds.filter((adminId) => adminId !== userId);
    delete project.memberProfiles[userId];
  });
  state.invites = state.invites.filter((invite) => invite.userId !== userId);
  state.users = state.users.filter((user) => user.id !== userId);
  state.tasks.forEach((task) => {
    if (task.assigneeId === userId) {
      const project = state.projects.find((item) => item.id === task.projectId);
      task.assigneeId = fallbackAssignee(project);
    }
  });
  saveState();
  logAction("user.deleted", { userId });
  render();
  return true;
}

function createProject(name, description) {
  if (!isSystemAdmin()) {
    return false;
  }
  const cleanName = name.trim();
  if (!cleanName) {
    return false;
  }

  const id = uid();
  state.projects.push({
    id,
    name: cleanName,
    description: description.trim(),
    ownerId: session.userId,
    memberIds: [session.userId],
    adminIds: [session.userId],
    memberProfiles: {
      [session.userId]: { role: "owner", team: "Yönetim", title: "Ana admin" },
    },
  });
  session.projectId = id;
  session.view = "dashboard";
  saveState();
  saveSession();
  logAction("project.created", { projectId: id, name: cleanName });
  render();
  return true;
}

function createCalendarEvent(formData) {
  const project = currentProject();
  const title = formData.title.trim();
  if (!project || !canAssignTasks() || !title || !formData.date || !ALLOWED_EVENT_TYPES.has(formData.type)) {
    return false;
  }

  state.calendarEvents.push({
    id: uid(),
    projectId: project.id,
    title,
    date: formData.date,
    type: formData.type,
    description: formData.description.trim(),
    createdBy: session.userId,
  });
  saveState();
  logAction("calendar.created", {
    projectId: project.id,
    title,
    date: formData.date,
    type: formData.type,
  });
  render();
  return true;
}

function saveTemplateQuestions(templateId, text) {
  if (!canEditTemplates()) {
    return false;
  }

  const template = state.documentTemplates.find((item) => item.id === templateId);
  if (!template) {
    return false;
  }

  const questions = text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
  if (questions.length === 0) {
    return false;
  }

  template.questions = questions;
  saveState();
  logAction("document.template.updated", { templateId, questionCount: questions.length });
  renderDocuments();
  return true;
}

function emptyState(text) {
  const element = document.createElement("p");
  element.className = "empty-state";
  element.textContent = text;
  return element;
}

function statusLabel(status) {
  const labels = {
    todo: "Yapılacak",
    review: "Onay bekliyor",
    approved: "Onaylandı",
    changes: "Düzeltme",
  };
  return labels[status] || status;
}

function roleLabel(role) {
  const labels = {
    owner: "Ana admin",
    admin: "Admin",
    lead: "Ekip kaptanı",
    member: "Üye",
    none: "Erişim yok",
  };
  return labels[role] || labels.none;
}

function priorityLabel(priority) {
  const labels = {
    urgent: "Acil",
    high: "Yüksek",
    normal: "Normal",
    low: "Düşük",
  };
  return labels[priority] || labels.normal;
}

function priorityRank(priority) {
  const ranks = {
    urgent: 4,
    high: 3,
    normal: 2,
    low: 1,
  };
  return ranks[priority] || ranks.normal;
}

function formatDate(value) {
  return new Intl.DateTimeFormat("tr-TR").format(new Date(value));
}

function formatDateTime(value) {
  return new Intl.DateTimeFormat("tr-TR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

function initials(name) {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

function downloadStateBackup() {
  const blob = new Blob(
    [
      JSON.stringify(
        {
          exportedAt: new Date().toISOString(),
          exportedBy: currentUser()?.email || "",
          state,
        },
        null,
        2,
      ),
    ],
    { type: "application/json" },
  );
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `proje-yonetimi-yedek-${new Date().toISOString().slice(0, 10)}.json`;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  logAction("state.backup.downloaded", { projectId: currentProject()?.id || "" });
}

async function saveSnapshot() {
  const result = await apiJson("/api/snapshot", {
    method: "POST",
    body: JSON.stringify({
      actor: currentUser()?.email || "",
      payload: state,
    }),
  });
  setMaintenanceMessage(
    result?.ok ? `Yedek alındı: #${result.snapshotId}` : "Snapshot için backend gerekli. Komut: python server.py",
    result?.ok ? "success" : "warning",
  );
  await refreshLogs();
}

async function reloadBackendState() {
  const result = await apiJson("/api/state");
  if (!result?.payload) {
    setMaintenanceMessage("Veritabanında yüklenecek state bulunamadı.", "warning");
    return;
  }
  state = normalizeState(result.payload);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  setMaintenanceMessage("Veri veritabanından geri yüklendi.", "success");
  logAction("state.reloaded.from.backend", { projectId: currentProject()?.id || "" });
  render();
}

function repairCurrentState() {
  state = normalizeState(state);
  saveState();
  setMaintenanceMessage("State normalize edildi; eksik listeler, roller ve görev alanları onarıldı.", "success");
  logAction("state.repaired", { projectId: currentProject()?.id || "" });
  render();
}

loginTab.addEventListener("click", () => setAuthTab("login"));
registerTab.addEventListener("click", () => setAuthTab("register"));

document.querySelectorAll("[data-demo-email]").forEach((button) => {
  button.addEventListener("click", () => {
    setAuthTab("login");
    document.querySelector("#loginEmail").value = button.dataset.demoEmail;
    document.querySelector("#loginPassword").value = "123456";
  });
});

loginForm.addEventListener("submit", (event) => {
  event.preventDefault();
  signIn(
    document.querySelector("#loginEmail").value,
    document.querySelector("#loginPassword").value,
  );
});

registerForm.addEventListener("submit", (event) => {
  event.preventDefault();
  registerUser(
    document.querySelector("#registerName").value,
    document.querySelector("#registerEmail").value,
    document.querySelector("#registerPassword").value,
  );
});

logoutButton.addEventListener("click", logout);

projectSelect.addEventListener("change", (event) => {
  selectProject(event.target.value);
});

changeProjectButton.addEventListener("click", showProjectChooser);

navLinks.forEach((link) => {
  link.addEventListener("click", () => {
    session.view = link.dataset.view;
    saveSession();
    render();
  });
});

document.querySelectorAll("[data-close-dialog]").forEach((button) => {
  button.addEventListener("click", () => {
    button.closest("dialog")?.close();
  });
});

openTaskButton.addEventListener("click", () => {
  openTaskDialogForUser();
});

openMemberButton.addEventListener("click", () => {
  if (canManageProject()) {
    memberForm.reset();
    renderMemberOptions();
    safeOpenDialog(memberDialog);
  }
});

openEventButton.addEventListener("click", () => {
  if (canAssignTasks()) {
    eventForm.reset();
    document.querySelector("#eventDateInput").min = new Date().toISOString().slice(0, 10);
    safeOpenDialog(eventDialog);
  }
});

newProjectButton.addEventListener("click", () => {
  if (isSystemAdmin()) {
    projectForm.reset();
    safeOpenDialog(projectDialog);
  }
});

gateNewProjectButton.addEventListener("click", () => {
  if (isSystemAdmin()) {
    projectForm.reset();
    safeOpenDialog(projectDialog);
  }
});

openTemplateEditorButton.addEventListener("click", () => {
  if (canEditTemplates()) {
    renderTemplateOptions();
    safeOpenDialog(templateDialog);
  }
});

taskForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const created = createTask({
    title: document.querySelector("#taskTitleInput").value.trim(),
    description: document.querySelector("#taskDescriptionInput").value.trim(),
    assigneeId: document.querySelector("#taskAssigneeInput").value,
    dueDate: document.querySelector("#taskDueInput").value,
    priority: document.querySelector("#taskPriorityInput").value,
    label: document.querySelector("#taskLabelInput").value,
    estimateHours: document.querySelector("#taskEstimateInput").value,
    checklist: document.querySelector("#taskChecklistInput").value,
  });
  if (created) {
    taskForm.reset();
    taskDialog.close();
  }
});

memberForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const added = addMemberToProject(
    document.querySelector("#memberSelect").value,
    document.querySelector("#memberRoleSelect").value,
    document.querySelector("#memberTeamSelect").value,
    document.querySelector("#memberInviteNote").value.trim(),
  );
  if (added) {
    memberForm.reset();
    memberDialog.close();
  }
});

projectForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const created = createProject(
    document.querySelector("#projectNameInput").value.trim(),
    document.querySelector("#projectDescriptionInput").value.trim(),
  );
  if (created) {
    projectForm.reset();
    projectDialog.close();
  }
});

eventForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const created = createCalendarEvent({
    title: document.querySelector("#eventTitleInput").value.trim(),
    date: document.querySelector("#eventDateInput").value,
    type: document.querySelector("#eventTypeInput").value,
    description: document.querySelector("#eventDescriptionInput").value.trim(),
  });
  if (created) {
    eventForm.reset();
    eventDialog.close();
  }
});

documentForm.addEventListener("submit", (event) => {
  event.preventDefault();
  saveDocumentAnswers();
});

checkTemplateButton?.addEventListener("click", checkSelectedTemplate);
exportDocumentButton?.addEventListener("click", exportSelectedDocument);
templateUploadInput?.addEventListener("change", (event) => {
  uploadSelectedTemplate(event.target.files[0]);
});

adminUserForm?.addEventListener("submit", (event) => {
  event.preventDefault();
  const added = addSystemUser(
    document.querySelector("#adminUserNameInput").value,
    document.querySelector("#adminUserEmailInput").value,
    document.querySelector("#adminUserPasswordInput").value,
  );
  if (added) {
    adminUserForm.reset();
    document.querySelector("#adminUserPasswordInput").value = "123456";
  }
});

refreshLogsButton?.addEventListener("click", refreshLogs);
downloadStateButton?.addEventListener("click", downloadStateBackup);
saveSnapshotButton?.addEventListener("click", saveSnapshot);
reloadBackendStateButton?.addEventListener("click", reloadBackendState);
repairStateButton?.addEventListener("click", repairCurrentState);

document.querySelector("#templateSelect").addEventListener("change", renderTemplateQuestions);

templateForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const saved = saveTemplateQuestions(
    document.querySelector("#templateSelect").value,
    document.querySelector("#templateQuestionsInput").value,
  );
  if (saved) {
    templateDialog.close();
  }
});

bootstrapBackend();

function runSelfTest() {
  const banner = document.createElement("div");
  banner.style.cssText =
    "position:fixed;z-index:9999;top:0;left:0;right:0;padding:14px 18px;font:800 16px system-ui;background:#fff2dd;color:#202124";
  banner.textContent = "Self-test calisiyor...";
  document.body.append(banner);
  const previousState = localStorage.getItem(STORAGE_KEY);
  const previousSession = localStorage.getItem(SESSION_KEY);
  const passed = [];

  function check(condition, message) {
    if (!condition) {
      throw new Error(message);
    }
    passed.push(message);
  }

  function visible(element) {
    return element && !element.classList.contains("hidden");
  }

  try {
    state = createSeedData();
    session = { userId: null, projectId: null, view: "admin", documentId: "fr01" };
    saveState();
    saveSession();
    render();

    signIn("admin@proje.local", "123456");
    check(visible(appView), "Admin girisi uygulama kabugunu acti");
    check(visible(projectGate), "Giris sonrasi once proje secme ekrani aciliyor");
    check(!visible(workspaceView), "Proje secmeden panel acilmiyor");
    check(projectGateList.children.length > 0, "Proje secme ekrani projeleri listeliyor");
    check(selectProject(projectsForUser(session.userId)[0].id) === true, "Proje secilince panele geciliyor");
    check(!visible(projectGate), "Proje secildikten sonra secim ekrani kapaniyor");
    check(visible(workspaceView), "Proje secildikten sonra calisma alani aciliyor");
    check(projectSelect.classList.contains("hidden"), "Eski sol ust proje dropdown gizli");
    showProjectChooser();
    check(visible(projectGate), "Proje degistir ile secim ekranina donuluyor");
    check(selectProject(projectsForUser(session.userId)[0].id) === true, "Proje degistir sonrasi proje tekrar seciliyor");
    check(visible(document.querySelector('[data-view="admin"]')), "Admin panel linki adminde gorunuyor");
    check(visible(openTaskButton), "Admin gorev atama butonunu goruyor");
    check(visible(openMemberButton), "Admin uye ekleme butonunu goruyor");
    check(visible(newProjectButton), "Sistem admini yeni proje butonunu goruyor");
    check(STORAGE_KEY.endsWith(".v5"), "Storage surumu yeni veri modeliyle tutarli");
    check(typeof pendingNotificationsForUser === "function", "Bildirim helper adi guncel");
    session.view = "team";
    saveSession();
    render();
    check(
      [...document.querySelectorAll(".member-task-button")].some((button) => visible(button)),
      "Admin ekip satirindan gorev atama butonunu goruyor",
    );

    const beforeCount = projectTasks().length;
    const adminAssigneeId = document.querySelector("#taskAssigneeInput").value;
    createTask({
      title: "Self Test Gorevi",
      description: "Admin gorev atama kontrolu",
      assigneeId: adminAssigneeId,
      dueDate: "2026-07-10",
      priority: "urgent",
      label: "Test",
      estimateHours: 2.5,
      checklist: "Alt is 1\nAlt is 2",
    });
    check(projectTasks().length === beforeCount + 1, "Admin mevcut kisiye gorev olusturabiliyor");
    renderDashboard();
    check(
      document.querySelector("#openTasks").textContent ===
        String(projectTasks().filter((task) => task.status !== "approved").length),
      "Dashboard acik gorev metrigi dogru",
    );
    const customTask = projectTasks().find((task) => task.title === "Self Test Gorevi");
    check(customTask.priority === "urgent", "Gorev onceligi kaydediliyor");
    check(customTask.label === "Test", "Gorev etiketi kaydediliyor");
    check(customTask.estimateHours === 2.5, "Gorev tahmini saat kaydediliyor");
    check(customTask.checklist.length === 2, "Gorev checklist maddeleri kaydediliyor");
    check(toggleChecklistItem(customTask.id, customTask.checklist[0].id) === true, "Checklist maddesi isaretlenebiliyor");
    check(customTask.checklist[0].done === true, "Checklist durumu state icinde guncelleniyor");
    check(addTaskComment(customTask.id, "Test yorumu") === true, "Goreve yorum eklenebiliyor");
    check(customTask.comments.length === 1, "Gorev yorumlari state icinde tutuluyor");
    const foreignProjectId = uid();
    const foreignTask = {
      id: uid(),
      projectId: foreignProjectId,
      title: "Yabanci proje gorevi",
      description: "Bu goreve dokunulmamali",
      assigneeId: session.userId,
      createdBy: session.userId,
      dueDate: "2026-07-10",
      status: "todo",
      team: "Yönetim",
      priority: "normal",
      label: "Yönetim",
      estimateHours: 1,
      checklist: [{ id: uid(), text: "Kapali alan", done: false }],
      comments: [],
      submissions: [],
    };
    state.tasks.push(foreignTask);
    check(toggleChecklistItem(foreignTask.id, foreignTask.checklist[0].id) === false, "Baska proje checklisti degistirilemiyor");
    check(addTaskComment(foreignTask.id, "Olmamali") === false, "Baska proje gorevine yorum eklenemiyor");
    check(submitTask(foreignTask.id, { note: "Olmamali", fileName: "", fileData: "" }) === false, "Baska proje gorevine teslim yuklenemiyor");
    check(updateTaskStatus(foreignTask.id, "approved") === false, "Baska proje gorevi onaylanamiyor");
    const invalidTaskBefore = projectTasks().length;
    check(
      createTask({
        title: "",
        description: "Bos baslik engellenmeli",
        assigneeId: adminAssigneeId,
        dueDate: "2026-07-10",
        priority: "normal",
        label: "",
        estimateHours: "",
        checklist: "",
      }) === false,
      "Bos baslikli gorev reddediliyor",
    );
    check(projectTasks().length === invalidTaskBefore, "Bos gorev listeye eklenmiyor");
    const badPriorityBefore = projectTasks().length;
    check(
      createTask({
        title: "Gecersiz oncelik",
        description: "Normal oncelige dusmeli",
        assigneeId: adminAssigneeId,
        dueDate: "2026-07-10",
        priority: "patates",
        label: "",
        estimateHours: "",
        checklist: "",
      }) === true,
      "Gecersiz oncelik normal degerine dusuyor",
    );
    check(projectTasks().length === badPriorityBefore + 1, "Gecersiz oncelikli gorev guvenli olusuyor");
    check(projectTasks().at(-1).priority === "normal", "Gecersiz oncelik state icinde normal oldu");

    const brokenMemberId = uid();
    currentProject().memberIds.push(brokenMemberId);
    renderAssigneeOptions();
    check(
      ![...document.querySelector("#taskAssigneeInput").options].some((option) => option.value === brokenMemberId),
      "Profili bozuk uye gorev atama listesine girmiyor",
    );
    check(
      validProjectMemberIds(currentProject()).every((memberId) =>
        state.users.some((user) => user.id === memberId),
      ),
      "Gecerli uye listesi kullanici kaydi olmayanlari dislar",
    );
    currentProject().memberIds = currentProject().memberIds.filter((memberId) => memberId !== brokenMemberId);
    const allMembersBefore = projectTasks().length;
    currentProject().memberIds.forEach((memberId, index) => {
      createTask({
        title: `Uye gorevi ${index + 1}`,
        description: "Her uyeye gorev atama kontrolu",
        assigneeId: memberId,
        dueDate: "2026-07-10",
        priority: "normal",
        label: "Toplu",
        estimateHours: 1,
        checklist: "",
      });
    });
    check(
      projectTasks().length === allMembersBefore + currentProject().memberIds.length,
      "Ana admin tum proje uyelerine gorev atayabiliyor",
    );

    const project = currentProject();
    const newUser = {
      id: uid(),
      name: "Yeni Yazılımcı",
      email: "yeni-yazilimci@proje.local",
      password: "123456",
    };
    state.users.push(newUser);
    saveState();
    render();

    const memberCountBefore = project.memberIds.length;
    addMemberToProject(newUser.id, "member", "Yazılım", "Self-test ile eklendi");
    check(project.memberIds.includes(newUser.id), "Admin kayitli kisiyi projeye direkt ekleyebiliyor");
    check(project.memberIds.length === memberCountBefore + 1, "Yeni uye ekip sayisini bir artiriyor");
    check(
      [...document.querySelector("#taskAssigneeInput").options].some((option) => option.value === newUser.id),
      "Yeni eklenen kisi gorev atama listesine hemen geliyor",
    );

    check(
      addMemberToProject(newUser.id, "member", "Yazılım", "Tekrar ekleme denemesi") === false,
      "Ayni kisi icin ikinci ekleme reddediliyor",
    );
    check(project.memberIds.length === memberCountBefore + 1, "Ayni kisi projeye ikinci kez eklenmiyor");
    const badRoleUser = { id: uid(), name: "Rol Test", email: "rol-test@proje.local", password: "123456" };
    state.users.push(badRoleUser);
    check(addMemberToProject(badRoleUser.id, "patron", "Yazılım", "") === false, "Gecersiz rol ile uye eklenemiyor");
    check(addMemberToProject(badRoleUser.id, "member", "Uzay", "") === false, "Gecersiz ekip ile uye eklenemiyor");

    const assignAfterAdd = projectTasks().length;
    createTask({
      title: "Yeni uyeye gorev",
      description: "Yeni eklenen kisiye direkt gorev",
      assigneeId: newUser.id,
      dueDate: "2026-07-11",
      priority: "high",
      label: "Yeni Uye",
      estimateHours: 1,
      checklist: "Tanisma",
    });
    check(projectTasks().length === assignAfterAdd + 1, "Yeni eklenen kisiye hemen gorev atanabiliyor");

    const outsideUser = { id: uid(), name: "Dis Kullanici", email: "dis@proje.local", password: "123456" };
    state.users.push(outsideUser);
    saveState();
    const outsideBefore = projectTasks().length;
    createTask({
      title: "Hatali gorev",
      description: "Proje disina atanmamali",
      assigneeId: outsideUser.id,
      dueDate: "2026-07-12",
      priority: "normal",
      label: "",
      estimateHours: "",
      checklist: "",
    });
    check(projectTasks().length === outsideBefore, "Proje disindaki kisiye gorev atanamiyor");

    logout();
    signIn("yazilim@proje.local", "123456");
    check(visible(projectGate), "Kullanici girisinden sonra proje secme ekrani aciliyor");
    check(selectProject(projectsForUser(session.userId)[0].id) === true, "Kullanici proje secerek ilerliyor");
    check(!visible(document.querySelector('[data-view="admin"]')), "Kaptan admin panelini gormuyor");
    check(!visible(openMemberButton), "Kaptan uye ekleme butonunu gormuyor");
    check(!visible(newProjectButton), "Kaptan yeni proje butonunu gormuyor");
    check(visible(openTaskButton), "Kaptan gorev atama butonunu goruyor");
    const leadOptions = [...document.querySelector("#taskAssigneeInput").options].map(
      (option) => option.textContent,
    );
    check(leadOptions.length > 0, "Kaptan icin atanacak kisi listesi dolu");
    check(leadOptions.every((text) => text.includes("Yazılım")), "Kaptan sadece kendi ekibini gorebiliyor");
    session.view = "tasks";
    saveSession();
    render();
    check(document.querySelector("#todoTasks").closest(".task-column").querySelector("h3").textContent === "Yapılacak", "Yapilacak kolonu durum etiketiyle uyumlu");

    const designUser = state.users.find((user) => user.email === "tasarim@proje.local");
    const leadBlockedBefore = projectTasks().length;
    createTask({
      title: "Tasarima hatali atama",
      description: "Kaptan baska ekibe atamamali",
      assigneeId: designUser.id,
      dueDate: "2026-07-13",
      priority: "normal",
      label: "",
      estimateHours: "",
      checklist: "",
    });
    check(projectTasks().length === leadBlockedBefore, "Kaptan baska ekibe gorev atayamiyor");

    logout();
    signIn("yazilim2@proje.local", "123456");
    check(visible(projectGate), "Uye girisinden sonra proje secme ekrani aciliyor");
    check(selectProject(projectsForUser(session.userId)[0].id) === true, "Uye proje secerek ilerliyor");
    session.view = "reports";
    saveSession();
    render();
    check(session.view === "dashboard", "Uye raporlar sekmesine zorla gecemiyor");
    check(!visible(document.querySelector('[data-view="admin"]')), "Uye admin panelini gormuyor");
    check(!visible(openTaskButton), "Uye gorev atama butonunu gormuyor");
    check(!visible(openMemberButton), "Uye uye ekleme butonunu gormuyor");
    check(!visible(newProjectButton), "Uye yeni proje butonunu gormuyor");
    check(!visible(openTemplateEditorButton), "Uye belge soru duzenleme butonunu gormuyor");
    renderMyWork();
    check(document.querySelector("#myWorkList").children.length > 0, "Benim islerim atanmis gorevleri gosteriyor");
    renderInbox();
    check(document.querySelector("#inboxList").children.length > 0, "Gelen kutusu yorum veya teslimleri gosteriyor");

    const memberEventBefore = projectEvents().length;
    createCalendarEvent({
      title: "Uye takvim denemesi",
      date: "2026-07-14",
      type: "Not",
      description: "Olusmamali",
    });
    check(projectEvents().length === memberEventBefore, "Uye takvim kaydi olusturamiyor");

    logout();
    signIn("admin@proje.local", "123456");
    selectProject(projectsForUser(session.userId)[0].id);
    session.view = "admin";
    saveSession();
    render();
    check(document.querySelector("#adminProjectList").textContent.includes("bildirim"), "Admin proje karti bildirim dilini kullaniyor");
    const invalidEventBefore = projectEvents().length;
    check(
      createCalendarEvent({ title: "", date: "2026-07-15", type: "Not", description: "" }) === false,
      "Bos baslikli takvim kaydi reddediliyor",
    );
    check(projectEvents().length === invalidEventBefore, "Bos baslikli takvim kaydi olusmuyor");
    check(
      createCalendarEvent({ title: "Gecersiz tur", date: "2026-07-15", type: "Parti", description: "" }) === false,
      "Gecersiz takvim turu reddediliyor",
    );

    createCalendarEvent({
      title: "Self-test toplantisi",
      date: "2026-07-15",
      type: "Toplantı",
      description: "Test",
    });
    check(projectEvents().length === invalidEventBefore + 1, "Admin takvim kaydi olusturabiliyor");

    const template = state.documentTemplates[0];
    check(saveTemplateQuestions(template.id, "") === false, "Bos belge sorusu kaydi reddediliyor");
    saveTemplateQuestions(template.id, "Alan 1\nAlan 2");
    check(template.questions.length === 2, "Ana admin belge sorularini duzenleyebiliyor");
    session.documentId = template.id;
    renderDocuments();
    documentForm.elements.q0.value = "Cevap 1";
    check(saveDocumentAnswers() === true, "Belge cevaplari kaydedilebiliyor");
    document.querySelector("#taskTitleInput").value = "Eski baslik";
    openTaskDialogForUser(adminAssigneeId);
    check(document.querySelector("#taskTitleInput").value === "", "Gorev penceresi acilirken eski form temizleniyor");
    taskDialog.close();

    banner.textContent = `PASS: ${passed.length} tutarlilik kontrolu gecti. Roller, gorevler, bildirimler ve moduller uyumlu.`;
    banner.style.background = "#e7f5ed";
  } catch (error) {
    banner.textContent = `FAIL: ${error.message}`;
    banner.style.background = "#fae8e8";
  } finally {
    if (previousState) {
      localStorage.setItem(STORAGE_KEY, previousState);
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
    if (previousSession) {
      localStorage.setItem(SESSION_KEY, previousSession);
    } else {
      localStorage.removeItem(SESSION_KEY);
    }
    state = loadState();
    session = loadSession();
    render();
  }
}

render();

if (new URLSearchParams(window.location.search).has("selftest")) {
  runSelfTest();
}
