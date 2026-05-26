import {
  Activity,
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  Clock3,
  Database,
  Download,
  FileText,
  Gauge,
  Laptop,
  ListChecks,
  LockKeyhole,
  LogOut,
  RefreshCw,
  ScrollText,
  Search,
  Server,
  Shield,
  UsersRound,
} from "lucide-react";
import { createRoot } from "react-dom/client";
import { useEffect, useMemo, useState } from "react";
import "./styles.css";
import logoTceAl from "./assets/logo-tceal.png";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || window.localStorage.getItem("apiBaseUrl") || "http://localhost:8080";

const tabs = [
  { id: "dashboard", label: "Painel", icon: Gauge },
  { id: "users", label: "Usuarios", icon: UsersRound },
  { id: "groups", label: "Grupos", icon: Shield },
  { id: "computers", label: "Computadores", icon: Laptop },
  { id: "reports", label: "Relatorios", icon: Download },
  { id: "operations", label: "Operacoes", icon: Activity },
  { id: "logons", label: "Logons", icon: Clock3 },
  { id: "logs", label: "Logs", icon: ScrollText },
];

const userStatuses = [
  "active",
  "all",
  "disabled",
  "locked",
  "inactive",
  "never_logged_on",
  "password_never_expires",
];

const groupStatuses = ["all", "empty", "with_members", "without_description", "without_owner"];

const computerStatuses = [
  "active",
  "all",
  "disabled",
  "inactive",
  "never_logged_on",
  "servers",
  "workstations",
  "domain_controllers",
  "old_machine_password",
  "missing_metadata",
];

const labels = {
  statuses: {
    active: "Ativos",
    all: "Todos",
    disabled: "Desabilitados",
    locked: "Bloqueados",
    inactive: "Inativos",
    never_logged_on: "Nunca fizeram logon",
    password_never_expires: "Senha nunca expira",
    empty: "Vazios",
    with_members: "Com membros",
    without_description: "Sem descricao",
    without_owner: "Sem responsavel",
    servers: "Servidores",
    workstations: "Estacoes de trabalho",
    domain_controllers: "Controladores de dominio",
    old_machine_password: "Senha de maquina antiga",
    missing_metadata: "Sem metadados",
  },
  roles: {
    admin: "Administrador",
    operator: "Operador",
    viewer: "Leitor",
    auditor: "Auditor",
  },
  formats: {
    json: "JSON",
    csv: "CSV",
    pdf: "PDF",
  },
  objectTypes: {
    users: "Usuarios",
    groups: "Grupos",
    computers: "Computadores",
  },
  metadata: {
    description: "Descricao",
    location: "Localizacao",
    managed_by: "Responsavel DN",
  },
  fields: {
    distinguished_name: "DN",
    sam_account_name: "Login",
    user_principal_name: "UPN",
    display_name: "Nome",
    email: "Email",
    department: "Departamento",
    title: "Cargo",
    manager: "Gerente",
    enabled: "Ativo",
    locked: "Bloqueado",
    password_never_expires: "Senha nunca expira",
    created_at: "Criado em",
    changed_at: "Alterado em",
    last_logon_at: "Ultimo logon",
    last_logon_computer: "Computador do logon",
    last_logon_ip: "IP do logon",
    workstation_status_at: "Status recebido em",
    password_last_set_at: "Senha alterada em",
    password_expires_at: "Senha expira em",
    account_expires_at: "Conta expira em",
    common_name: "CN",
    name: "Nome",
    description: "Descricao",
    member_count: "Membros",
    managed_by: "Responsavel",
    dns_hostname: "DNS",
    operating_system: "Sistema",
    operating_system_version: "Versao",
    location: "Localizacao",
  },
};

function labelFor(group, value) {
  return labels[group]?.[value] || value;
}

class ApiError extends Error {
  constructor(message, status = 0) {
    super(message);
    this.status = status;
  }
}

function authHeaders(token) {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function buildQuery(params) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      search.set(key, value);
    }
  });
  return search.toString();
}

function parsePrometheusMetrics(text) {
  const result = {
    uptimeSeconds: 0,
    httpRequests: 0,
    events: 0,
  };

  text.split("\n").forEach((line) => {
    if (line.startsWith("#") || !line.trim()) return;
    const [nameWithLabels, rawValue] = line.trim().split(/\s+/);
    const value = Number(rawValue || 0);
    if (nameWithLabels === "admanager_uptime_seconds") {
      result.uptimeSeconds = value;
    }
    if (nameWithLabels.startsWith("admanager_http_requests_total")) {
      result.httpRequests += value;
    }
    if (nameWithLabels.startsWith("admanager_events_total")) {
      result.events += value;
    }
  });

  return result;
}

function formatDuration(seconds) {
  if (!seconds) return "0m";
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

function isDateLike(value) {
  return (
    typeof value === "string" &&
    /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/.test(value)
  );
}

function formatDateTime(value) {
  if (!value || !isDateLike(value)) return value;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(date);
}

function todayDateInputValue() {
  const date = new Date();
  const offsetDate = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return offsetDate.toISOString().slice(0, 10);
}

function dateStartIso(value) {
  if (!value) return "";
  return new Date(`${value}T00:00:00`).toISOString();
}

function dateEndIso(value) {
  if (!value) return "";
  return new Date(`${value}T23:59:59`).toISOString();
}

function dateInputFromIso(value) {
  if (!value || !isDateLike(value)) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  if (date.getFullYear() >= 9999) return "";
  const offsetDate = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return offsetDate.toISOString().slice(0, 10);
}

function isNeverAccountExpiration(value) {
  if (!value) return true;
  if (typeof value === "string" && value.startsWith("9999-12-31")) return true;
  const date = new Date(value);
  return !Number.isNaN(date.getTime()) && date.getFullYear() >= 9999;
}

function displayValue(value) {
  if (value === undefined || value === null || value === "") return "";
  if (typeof value === "boolean") return value ? "Sim" : "Nao";
  if (isDateLike(value)) return formatDateTime(value);
  return String(value);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function printableReportHtml(payload) {
  const items = payload?.items || [];
  const metadata = payload?.metadata || {};
  const columns = Object.keys(items[0] || {}).slice(0, 8);
  const rowsHtml = items
    .map(
      (row) =>
        `<tr>${columns
          .map((column) => `<td>${escapeHtml(displayValue(row[column]))}</td>`)
          .join("")}</tr>`
    )
    .join("");
  const headerHtml = columns.map((column) => `<th>${escapeHtml(labelFor("fields", column))}</th>`).join("");

  return `<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <title>${escapeHtml(metadata.report_id || "relatorio")}</title>
  <style>
    body { color: #18252f; font-family: Arial, sans-serif; margin: 32px; }
    h1 { font-size: 24px; margin: 0 0 6px; }
    .eyebrow { color: #516671; font-size: 12px; font-weight: 700; letter-spacing: 0; text-transform: uppercase; }
    .meta { border-bottom: 1px solid #cfdbe2; color: #516671; display: grid; gap: 4px; margin: 18px 0; padding-bottom: 14px; }
    table { border-collapse: collapse; font-size: 11px; width: 100%; }
    th, td { border: 1px solid #d7e0e5; padding: 7px; text-align: left; vertical-align: top; }
    th { background: #eef3f6; color: #334955; font-size: 10px; text-transform: uppercase; }
    @page { margin: 16mm; }
  </style>
</head>
<body>
  <div class="eyebrow">TCE-AL · Active Directory Manager</div>
  <h1>${escapeHtml(labelFor("objectTypes", metadata.report_type || "Relatorio"))}</h1>
  <div class="meta">
    <span>Gerado por: ${escapeHtml(metadata.generated_by || "")}</span>
    <span>Gerado em: ${escapeHtml(formatDateTime(metadata.generated_at) || "")}</span>
    <span>Linhas: ${escapeHtml(metadata.row_count ?? items.length)}</span>
  </div>
  <table>
    <thead><tr>${headerHtml}</tr></thead>
    <tbody>${rowsHtml || `<tr><td colspan="${Math.max(columns.length, 1)}">Sem dados</td></tr>`}</tbody>
  </table>
  <script>window.onload = () => window.print();</script>
</body>
</html>`;
}

function exportReportPdf(payload) {
  const previousFrame = document.getElementById("report-print-frame");
  if (previousFrame) {
    previousFrame.remove();
  }

  const frame = document.createElement("iframe");
  frame.id = "report-print-frame";
  frame.title = "Relatorio PDF";
  frame.style.position = "fixed";
  frame.style.right = "0";
  frame.style.bottom = "0";
  frame.style.width = "0";
  frame.style.height = "0";
  frame.style.border = "0";
  frame.style.visibility = "hidden";
  document.body.appendChild(frame);

  const printDocument = frame.contentWindow?.document;
  if (!printDocument) {
    throw new ApiError("Nao foi possivel preparar o PDF.", 0);
  }

  printDocument.open();
  printDocument.write(printableReportHtml(payload));
  printDocument.close();

  frame.onload = () => {
    frame.contentWindow?.focus();
    frame.contentWindow?.print();
  };
}

function rolesText(roles) {
  if (!Array.isArray(roles) || !roles.length) return "";
  return roles.map((role) => labelFor("roles", role)).join(", ");
}

const userActionLogEvents = ["user_write_operation", "computer_write_operation", "group_write_operation"];

const logActionOptions = [
  { value: "all", label: "Todas as acoes", events: userActionLogEvents },
  { value: "unlock_user", label: "Desbloquear usuario", event: "user_write_operation", operation: "unlock" },
  {
    value: "force_password_change",
    label: "Forcar troca de senha",
    event: "user_write_operation",
    operation: "force_password_change",
  },
  { value: "enable_user", label: "Habilitar usuario", event: "user_write_operation", operation: "enable" },
  { value: "disable_user", label: "Desabilitar usuario", event: "user_write_operation", operation: "disable" },
  {
    value: "reset_password",
    label: "Resetar senha",
    event: "user_write_operation",
    operation: "reset_password",
  },
  {
    value: "account_expiration",
    label: "Alterar expiracao da conta",
    event: "user_write_operation",
    operation: "account_expiration",
  },
  {
    value: "enable_computer",
    label: "Habilitar computador",
    event: "computer_write_operation",
    operation: "enable",
  },
  {
    value: "disable_computer",
    label: "Desabilitar computador",
    event: "computer_write_operation",
    operation: "disable",
  },
  {
    value: "update_computer_metadata",
    label: "Atualizar metadados",
    event: "computer_write_operation",
    operation: "update_metadata",
  },
  {
    value: "add_group_member",
    label: "Adicionar usuario ao grupo",
    event: "group_write_operation",
    operation: "add_member",
  },
  {
    value: "remove_group_member",
    label: "Remover usuario do grupo",
    event: "group_write_operation",
    operation: "remove_member",
  },
];

function actionLabel(event, operation) {
  const labelsByOperation = {
    "user_write_operation:unlock": "Desbloquear usuario",
    "user_write_operation:force_password_change": "Forcar troca de senha",
    "user_write_operation:enable": "Habilitar usuario",
    "user_write_operation:disable": "Desabilitar usuario",
    "user_write_operation:reset_password": "Resetar senha",
    "user_write_operation:account_expiration": "Alterar expiracao da conta",
    "computer_write_operation:enable": "Habilitar computador",
    "computer_write_operation:disable": "Desabilitar computador",
    "computer_write_operation:update_metadata": "Atualizar metadados",
    "group_write_operation:add_member": "Adicionar usuario ao grupo",
    "group_write_operation:remove_member": "Remover usuario do grupo",
  };
  const labelsByEvent = {
    user_write_operation: "Operacao em usuario",
    group_write_operation: "Operacao em grupo",
    computer_write_operation: "Operacao em computador",
  };
  return labelsByOperation[`${event}:${operation || ""}`] || labelsByEvent[event] || event;
}

function operatorMessage(error) {
  if (error?.status === 401) return "Usuario ou senha invalidos, ou sessao expirada.";
  if (error?.status === 403) return error.message || "Perfil sem permissao para esta operacao.";
  if (error?.status === 404) return error.message || "Recurso nao encontrado.";
  if (error?.status >= 500) return "Servico indisponivel. Verifique API, banco, worker ou AD.";
  if (error?.message?.includes("Failed to fetch")) {
    return "Nao foi possivel acessar a API. Verifique URL, CORS e disponibilidade do servico.";
  }
  return error?.message || "Falha inesperada.";
}

function ProtectedNotice({ token, permission }) {
  if (token) return null;
  return (
    <div className="access-notice">
      <LockKeyhole size={18} />
      <div>
        <strong>Login necessario</strong>
        <span>{permission}</span>
      </div>
    </div>
  );
}

function useApi(token, setMessage) {
  return useMemo(() => {
    async function request(path, options = {}) {
      let response;
      try {
        response = await fetch(`${API_BASE_URL}${path}`, {
          ...options,
          headers: {
            ...authHeaders(token),
            ...(options.body ? { "Content-Type": "application/json" } : {}),
            ...options.headers,
          },
        });
      } catch (error) {
        throw new ApiError(error.message, 0);
      }
      if (!response.ok) {
        let detail = `HTTP ${response.status}`;
        try {
          const payload = await response.json();
          detail = payload.detail || detail;
        } catch {
          // Keep generic message.
        }
        throw new ApiError(detail, response.status);
      }
      return response;
    }

    async function getJson(path) {
      const response = await request(path);
      return response.json();
    }

    async function postJson(path, body) {
      const response = await request(path, {
        method: "POST",
        body: JSON.stringify(body),
      });
      return response.json();
    }

    async function downloadCsv(path, filename) {
      const response = await request(path);
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      anchor.click();
      URL.revokeObjectURL(url);
      setMessage({ type: "success", text: "CSV gerado." });
    }

    return { getJson, postJson, downloadCsv };
  }, [token, setMessage]);
}

function LoginPanel({ setToken, setPrincipal, setMessage }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  async function login(event) {
    event.preventDefault();
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/auth/ad-login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ username, password }),
      });
      if (!response.ok) {
        let detail = "Falha ao autenticar no Active Directory.";
        try {
          const payload = await response.json();
          detail = payload.detail || detail;
        } catch {
          // Keep generic message.
        }
        throw new ApiError(detail, response.status);
      }
      const payload = await response.json();
      setToken(payload.access_token);
      setPrincipal(payload);
      window.localStorage.setItem("accessToken", payload.access_token);
      window.localStorage.setItem("principal", JSON.stringify(payload));
      setMessage({ type: "success", text: "Login realizado." });
    } catch (error) {
      setMessage({ type: "error", text: operatorMessage(error) });
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="login-shell">
      <div className="login-panel">
        <div className="login-brand">
          <img className="brand-logo" src={logoTceAl} alt="TCE-AL" />
          <div>
            <p className="eyebrow">Tribunal de Contas do Estado de Alagoas</p>
            <h1>Active Directory Manager</h1>
          </div>
        </div>
        <form className="login-form" onSubmit={login}>
          <label>
            Usuario do AD
            <input
              autoComplete="username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              placeholder="usuario ou usuario@dominio"
            />
          </label>
          <label>
            Senha
            <input
              autoComplete="current-password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>
          <button type="submit" disabled={loading || !username || !password}>
            <LockKeyhole size={18} />
            Entrar
          </button>
        </form>
        <div className="login-foot">
          <span>Acesso definido pelos grupos do Active Directory</span>
          <span>Administrador · Operador · Leitor · Auditor</span>
        </div>
      </div>
    </section>
  );
}

function DataTable({ rows, columns }) {
  if (!rows.length) {
    return <div className="empty">Sem dados</div>;
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.key}>{column.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={`${row.distinguished_name || row.sam_account_name || row.name}-${index}`}>
              {columns.map((column) => (
                <td key={column.key}>{displayValue(row[column.key])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function UserGroupsLookup({ token, setMessage }) {
  const api = useApi(token, setMessage);
  const [userQuery, setUserQuery] = useState("");
  const [selectedUser, setSelectedUser] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [suggestionsOpen, setSuggestionsOpen] = useState(false);
  const [searchLoading, setSearchLoading] = useState(false);
  const [groups, setGroups] = useState([]);
  const [groupOwner, setGroupOwner] = useState("");
  const [loadingGroups, setLoadingGroups] = useState(false);

  useEffect(() => {
    const normalizedQuery = userQuery.trim();
    if (!token || selectedUser || normalizedQuery.length < 2) {
      setSuggestions([]);
      setSearchLoading(false);
      return undefined;
    }

    let canceled = false;
    const timer = window.setTimeout(async () => {
      setSearchLoading(true);
      try {
        const params = buildQuery({ status: "all", query: normalizedQuery, limit: 8 });
        const payload = await api.getJson(`/users?${params}`);
        if (!canceled) {
          setSuggestions(payload.items || []);
          setSuggestionsOpen(true);
        }
      } catch {
        if (!canceled) {
          setSuggestions([]);
        }
      } finally {
        if (!canceled) {
          setSearchLoading(false);
        }
      }
    }, 350);

    return () => {
      canceled = true;
      window.clearTimeout(timer);
    };
  }, [api, selectedUser, token, userQuery]);

  function updateUserQuery(value) {
    setUserQuery(value);
    setSelectedUser("");
    setGroups([]);
    setGroupOwner("");
    setSuggestionsOpen(value.trim().length >= 2);
  }

  async function loadUserGroups(identifier = selectedUser || userQuery) {
    const normalizedIdentifier = identifier.trim();
    if (normalizedIdentifier.length < 2) {
      setMessage({ type: "error", text: "Informe pelo menos 2 caracteres para localizar o usuario." });
      return;
    }

    setLoadingGroups(true);
    try {
      const params = buildQuery({ limit: 500, include_nested: true });
      const payload = await api.getJson(`/groups/by-user/${encodeURIComponent(normalizedIdentifier)}?${params}`);
      setGroups(payload.groups || []);
      setGroupOwner(payload.sam_account_name || normalizedIdentifier);
      setSelectedUser(payload.sam_account_name || normalizedIdentifier);
      setUserQuery(payload.sam_account_name || normalizedIdentifier);
      setSuggestions([]);
      setSuggestionsOpen(false);
      setMessage({ type: "success", text: `${payload.count || 0} grupo(s) encontrado(s).` });
    } catch (error) {
      setMessage({ type: "error", text: operatorMessage(error) });
    } finally {
      setLoadingGroups(false);
    }
  }

  function selectUser(user) {
    const identifier = targetIdentifier("users", user);
    setSelectedUser(identifier);
    setUserQuery(identifier);
    setSuggestions([]);
    setSuggestionsOpen(false);
    loadUserGroups(identifier);
  }

  return (
    <div className="lookup-panel">
      <div className="lookup-head">
        <div>
          <h3>Grupos de um usuario</h3>
          <p>{groupOwner ? `${groups.length} grupo(s) para ${groupOwner}` : "Pesquise pelo login, nome ou email"}</p>
        </div>
        <button className="action-button" onClick={() => loadUserGroups()} disabled={!token || loadingGroups}>
          <Search size={18} />
          Consultar
        </button>
      </div>
      <div className="lookup-form">
        <label>
          Usuario
          <div className="target-picker">
            <div className="searchbox target-search">
              <Search size={18} />
              <input
                autoComplete="off"
                value={userQuery}
                onBlur={() => window.setTimeout(() => setSuggestionsOpen(false), 120)}
                onChange={(event) => updateUserQuery(event.target.value)}
                onFocus={() => setSuggestionsOpen(userQuery.trim().length >= 2 && !selectedUser)}
                placeholder="digite parte do nome, login ou email"
              />
            </div>
            {suggestionsOpen && (
              <div className="target-suggestions">
                {searchLoading && <div className="target-suggestion muted">Buscando...</div>}
                {!searchLoading &&
                  suggestions.map((user) => {
                    const identifier = targetIdentifier("users", user);
                    return (
                      <button key={identifier} type="button" onMouseDown={() => selectUser(user)}>
                        <strong>{targetTitle("users", user)}</strong>
                        <span>{targetSubtitle("users", user) || identifier}</span>
                      </button>
                    );
                  })}
                {!searchLoading && !suggestions.length && (
                  <div className="target-suggestion muted">Nenhum usuario encontrado</div>
                )}
              </div>
            )}
          </div>
        </label>
      </div>
      <DataTable
        rows={groups}
        columns={[
          { key: "sam_account_name", label: "Grupo" },
          { key: "common_name", label: "CN" },
          { key: "description", label: "Descricao" },
          { key: "member_count", label: "Membros" },
          { key: "managed_by", label: "Responsavel" },
        ]}
      />
    </div>
  );
}

function groupIdentifier(item) {
  return item.distinguished_name || item.sam_account_name || item.name || item.common_name || "";
}

function groupTitle(item) {
  return item.common_name || item.name || item.sam_account_name || "";
}

function groupSubtitle(item) {
  return [item.sam_account_name, item.description].filter(Boolean).join(" · ");
}

function GroupMembersLookup({ token, setMessage }) {
  const api = useApi(token, setMessage);
  const [groupQuery, setGroupQuery] = useState("");
  const [selectedGroup, setSelectedGroup] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [suggestionsOpen, setSuggestionsOpen] = useState(false);
  const [searchLoading, setSearchLoading] = useState(false);
  const [members, setMembers] = useState([]);
  const [groupName, setGroupName] = useState("");
  const [loadingMembers, setLoadingMembers] = useState(false);

  useEffect(() => {
    const normalizedQuery = groupQuery.trim();
    if (!token || selectedGroup || normalizedQuery.length < 2) {
      setSuggestions([]);
      setSearchLoading(false);
      return undefined;
    }

    let canceled = false;
    const timer = window.setTimeout(async () => {
      setSearchLoading(true);
      try {
        const params = buildQuery({ status: "all", query: normalizedQuery, limit: 8 });
        const payload = await api.getJson(`/groups?${params}`);
        if (!canceled) {
          setSuggestions(payload.items || []);
          setSuggestionsOpen(true);
        }
      } catch {
        if (!canceled) {
          setSuggestions([]);
        }
      } finally {
        if (!canceled) {
          setSearchLoading(false);
        }
      }
    }, 350);

    return () => {
      canceled = true;
      window.clearTimeout(timer);
    };
  }, [api, groupQuery, selectedGroup, token]);

  function updateGroupQuery(value) {
    setGroupQuery(value);
    setSelectedGroup("");
    setMembers([]);
    setGroupName("");
    setSuggestionsOpen(value.trim().length >= 2);
  }

  async function loadGroupMembers(identifier = selectedGroup || groupQuery) {
    const normalizedIdentifier = identifier.trim();
    if (normalizedIdentifier.length < 2) {
      setMessage({ type: "error", text: "Informe pelo menos 2 caracteres para localizar o grupo." });
      return;
    }

    setLoadingMembers(true);
    try {
      const params = buildQuery({ limit: 500 });
      const payload = await api.getJson(`/groups/${encodeURIComponent(normalizedIdentifier)}/members?${params}`);
      setMembers(payload.members || []);
      setGroupName(payload.group?.common_name || payload.group?.sam_account_name || normalizedIdentifier);
      setSelectedGroup(groupIdentifier(payload.group || {}) || normalizedIdentifier);
      setGroupQuery(payload.group?.common_name || payload.group?.sam_account_name || normalizedIdentifier);
      setSuggestions([]);
      setSuggestionsOpen(false);
      setMessage({ type: "success", text: `${payload.count || 0} membro(s) encontrado(s).` });
    } catch (error) {
      setMessage({ type: "error", text: operatorMessage(error) });
    } finally {
      setLoadingMembers(false);
    }
  }

  function selectGroup(group) {
    const identifier = groupIdentifier(group);
    setSelectedGroup(identifier);
    setGroupQuery(groupTitle(group) || identifier);
    setSuggestions([]);
    setSuggestionsOpen(false);
    loadGroupMembers(identifier);
  }

  return (
    <div className="lookup-panel">
      <div className="lookup-head">
        <div>
          <h3>Membros de um grupo</h3>
          <p>{groupName ? `${members.length} membro(s) em ${groupName}` : "Pesquise pelo nome, login ou descricao do grupo"}</p>
        </div>
        <button className="action-button" onClick={() => loadGroupMembers()} disabled={!token || loadingMembers}>
          <Search size={18} />
          Consultar
        </button>
      </div>
      <div className="lookup-form">
        <label>
          Grupo
          <div className="target-picker">
            <div className="searchbox target-search">
              <Search size={18} />
              <input
                autoComplete="off"
                value={groupQuery}
                onBlur={() => window.setTimeout(() => setSuggestionsOpen(false), 120)}
                onChange={(event) => updateGroupQuery(event.target.value)}
                onFocus={() => setSuggestionsOpen(groupQuery.trim().length >= 2 && !selectedGroup)}
                placeholder="digite parte do nome, login ou descricao"
              />
            </div>
            {suggestionsOpen && (
              <div className="target-suggestions">
                {searchLoading && <div className="target-suggestion muted">Buscando...</div>}
                {!searchLoading &&
                  suggestions.map((group) => {
                    const identifier = groupIdentifier(group);
                    return (
                      <button key={identifier} type="button" onMouseDown={() => selectGroup(group)}>
                        <strong>{groupTitle(group)}</strong>
                        <span>{groupSubtitle(group) || identifier}</span>
                      </button>
                    );
                  })}
                {!searchLoading && !suggestions.length && (
                  <div className="target-suggestion muted">Nenhum grupo encontrado</div>
                )}
              </div>
            )}
          </div>
        </label>
      </div>
      <DataTable
        rows={members}
        columns={[
          { key: "sam_account_name", label: "Login" },
          { key: "display_name", label: "Nome" },
          { key: "common_name", label: "CN" },
          { key: "email", label: "Email" },
          { key: "distinguished_name", label: "DN" },
        ]}
      />
    </div>
  );
}

function StatusPill({ tone = "neutral", children }) {
  return <span className={`status-pill ${tone}`}>{children}</span>;
}

function MetricTile({ icon: Icon, label, value, detail, tone = "neutral" }) {
  return (
    <div className="metric-tile">
      <div className={`metric-icon ${tone}`}>
        <Icon size={18} />
      </div>
      <div>
        <p>{label}</p>
        <strong>{value}</strong>
        {detail && <span>{detail}</span>}
      </div>
    </div>
  );
}

function ConfigChecklist({ summary }) {
  const items = [
    ["Dominio", summary?.ad_domain_configured],
    ["Base DN", summary?.ad_base_dn_configured],
    ["Servidor AD", summary?.ad_server_configured],
    ["Bind DN", summary?.ad_bind_dn_configured],
    ["LDAPS", summary?.ad_use_ldaps],
    ["Validacao TLS", summary?.ad_tls_require_cert],
    ["Auditoria DB", summary?.audit_database_enabled],
    ["Bloqueio escrita sem LDAPS", summary?.require_ldaps_for_writes],
  ];

  return (
    <div className="check-grid">
      {items.map(([label, ok]) => (
        <div className={`check-row ${ok ? "good" : "warn"}`} key={label}>
          {ok ? <CheckCircle2 size={17} /> : <AlertTriangle size={17} />}
          <span>{label}</span>
        </div>
      ))}
    </div>
  );
}

function snapshotCount(snapshot, objectType, status) {
  return Number(snapshot?.summary?.[objectType]?.[status]?.count || 0);
}

function snapshotCapped(snapshot, objectType, status) {
  return Boolean(snapshot?.summary?.[objectType]?.[status]?.capped);
}

function snapshotDelta(snapshot, objectType, status) {
  const value = snapshot?.delta_from_previous?.summary?.[objectType]?.[status];
  return typeof value === "number" ? value : null;
}

function formatDelta(value) {
  if (value === null || value === undefined || value === 0) return "sem variacao";
  return value > 0 ? `+${value} desde ultimo snapshot` : `${value} desde ultimo snapshot`;
}

function InventoryCard({ title, total, active, attention, delta, capped }) {
  return (
    <div className="inventory-card">
      <div className="inventory-head">
        <h3>{title}</h3>
        {capped && <StatusPill tone="warn">limite</StatusPill>}
      </div>
      <strong>{total}</strong>
      <div className="inventory-stats">
        <span>{active} ativos</span>
        <span>{attention} revisar</span>
      </div>
      <p>{formatDelta(delta)}</p>
    </div>
  );
}

function InventorySnapshot({ snapshot }) {
  if (!snapshot) {
    return (
      <div className="inventory-empty">
        <Database size={20} />
        <span>Snapshot indisponivel. Gere token com perfil que possa executar relatorios.</span>
      </div>
    );
  }

  const risks = [
    {
      label: "Usuarios inativos",
      value: snapshotCount(snapshot, "users", "inactive"),
      detail: "sem logon no periodo configurado",
    },
    {
      label: "Usuarios com senha nunca expira",
      value: snapshotCount(snapshot, "users", "password_never_expires"),
      detail: "revisao de politica recomendada",
    },
    {
      label: "Grupos vazios",
      value: snapshotCount(snapshot, "groups", "empty"),
      detail: "possivel limpeza controlada",
    },
    {
      label: "Grupos sem responsavel",
      value: snapshotCount(snapshot, "groups", "without_owner"),
      detail: "governanca pendente",
    },
    {
      label: "Computadores sem metadados",
      value: snapshotCount(snapshot, "computers", "missing_metadata"),
      detail: "descricao, localizacao ou responsavel",
    },
    {
      label: "Senha de maquina antiga",
      value: snapshotCount(snapshot, "computers", "old_machine_password"),
      detail: "revisar estacoes obsoletas",
    },
  ];

  return (
    <div className="snapshot-panel">
      <div className="panel-title">
        <BarChart3 size={18} />
        <h3>Inventario AD</h3>
        <StatusPill tone="neutral">{formatDateTime(snapshot.generated_at) || "sem data"}</StatusPill>
      </div>
      <div className="inventory-grid">
        <InventoryCard
          title="Usuarios"
          total={snapshotCount(snapshot, "users", "all")}
          active={snapshotCount(snapshot, "users", "active")}
          attention={snapshotCount(snapshot, "users", "inactive")}
          delta={snapshotDelta(snapshot, "users", "all")}
          capped={snapshotCapped(snapshot, "users", "all")}
        />
        <InventoryCard
          title="Grupos"
          total={snapshotCount(snapshot, "groups", "all")}
          active={snapshotCount(snapshot, "groups", "with_members")}
          attention={snapshotCount(snapshot, "groups", "without_owner")}
          delta={snapshotDelta(snapshot, "groups", "all")}
          capped={snapshotCapped(snapshot, "groups", "all")}
        />
        <InventoryCard
          title="Computadores"
          total={snapshotCount(snapshot, "computers", "all")}
          active={snapshotCount(snapshot, "computers", "active")}
          attention={snapshotCount(snapshot, "computers", "missing_metadata")}
          delta={snapshotDelta(snapshot, "computers", "all")}
          capped={snapshotCapped(snapshot, "computers", "all")}
        />
      </div>
      <div className="risk-grid">
        {risks.map((risk) => (
          <div className="risk-row" key={risk.label}>
            <strong>{risk.value}</strong>
            <div>
              <span>{risk.label}</span>
              <p>{risk.detail}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function WorkerStatusPanel({ workerStatus }) {
  if (!workerStatus) {
    return (
      <div className="worker-panel">
        <div className="panel-title">
          <Activity size={18} />
          <h3>Worker</h3>
          <StatusPill tone="warn">sem leitura</StatusPill>
        </div>
        <div className="inventory-empty">
          <Clock3 size={20} />
          <span>Status do worker ainda nao carregado.</span>
          <span>Use perfil Auditor ou Administrador para consultar historico de jobs.</span>
        </div>
      </div>
    );
  }

  const errorCount = Number(workerStatus.jobs_error_total || 0);
  const totalCount = Number(workerStatus.jobs_total || 0);
  const lastJobs = workerStatus.last_jobs || [];
  const lastJob = lastJobs[lastJobs.length - 1];

  return (
    <div className="worker-panel">
      <div className="panel-title">
        <Activity size={18} />
        <h3>Jobs e worker</h3>
        <StatusPill tone={errorCount > 0 ? "warn" : "good"}>
          {errorCount > 0 ? "com falhas" : "normal"}
        </StatusPill>
      </div>
      <div className="worker-summary">
        <MetricTile
          icon={ListChecks}
          label="Execucoes"
          value={totalCount}
          detail={`${errorCount} falha(s) registradas`}
          tone={errorCount > 0 ? "warn" : "good"}
        />
        <MetricTile
          icon={Clock3}
          label="Ultimo job"
          value={lastJob?.job_name || "sem historico"}
          detail={formatDateTime(lastJob?.timestamp || workerStatus.timestamp) || "sem data"}
          tone="neutral"
        />
      </div>
      <DataTable
        rows={lastJobs.slice().reverse()}
        columns={[
          { key: "timestamp", label: "Quando" },
          { key: "job_name", label: "Job" },
          { key: "status", label: "Status" },
        ]}
      />
    </div>
  );
}

function DashboardView({ token, setMessage }) {
  const api = useApi(token, setMessage);
  const [health, setHealth] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [principal, setPrincipal] = useState(null);
  const [config, setConfig] = useState(null);
  const [snapshot, setSnapshot] = useState(null);
  const [workerStatus, setWorkerStatus] = useState(null);
  const [auditEvents, setAuditEvents] = useState([]);
  const [adCheck, setAdCheck] = useState(null);
  const [loading, setLoading] = useState(false);

  async function refreshDashboard(showMessage = true) {
    setLoading(true);
    try {
      const [healthData, metricsResponse] = await Promise.all([
        api.getJson("/health"),
        fetch(`${API_BASE_URL}/metrics`),
      ]);
      const metricsText = await metricsResponse.text();
      setHealth(healthData);
      setMetrics(parsePrometheusMetrics(metricsText));

      if (token) {
        const [meResult, configResult, auditResult, snapshotResult, workerResult] = await Promise.allSettled([
          api.getJson("/auth/me"),
          api.getJson("/config/summary"),
          api.getJson("/audit/events?limit=5"),
          api.getJson("/reports/inventory-snapshot"),
          api.getJson("/reports/worker-status?limit=8"),
        ]);
        if (meResult.status === "fulfilled") setPrincipal(meResult.value);
        if (configResult.status === "fulfilled") setConfig(configResult.value);
        if (auditResult.status === "fulfilled") setAuditEvents(auditResult.value);
        if (snapshotResult.status === "fulfilled") setSnapshot(snapshotResult.value);
        if (snapshotResult.status === "rejected") setSnapshot(null);
        if (workerResult.status === "fulfilled") setWorkerStatus(workerResult.value);
        if (workerResult.status === "rejected") setWorkerStatus(null);
      } else {
        setPrincipal(null);
        setConfig(null);
        setAuditEvents([]);
        setSnapshot(null);
        setWorkerStatus(null);
      }

      if (showMessage) setMessage({ type: "success", text: "Painel atualizado." });
    } catch (error) {
      setMessage({ type: "error", text: operatorMessage(error) });
    } finally {
      setLoading(false);
    }
  }

  async function testAdConnection() {
    try {
      const result = await api.getJson("/ad/connection-test");
      setAdCheck(result);
      setMessage({ type: result.bind_successful ? "success" : "error", text: result.message });
    } catch (error) {
      setMessage({ type: "error", text: operatorMessage(error) });
    }
  }

  useEffect(() => {
    refreshDashboard(false);
  }, [token]);

  const apiOnline = health?.status === "ok";
  const adReady = config?.ad_ready_for_connection_test;

  return (
    <section className="section dashboard-section">
      <div className="section-head">
        <div>
          <h2>Painel operacional</h2>
          <p>Saude, seguranca e atividade recente do ambiente</p>
        </div>
        <div className="section-actions">
          <button onClick={() => refreshDashboard()} disabled={loading}>
            <RefreshCw size={18} />
          </button>
          <button onClick={testAdConnection} disabled={!token}>
            <Server size={18} />
          </button>
        </div>
      </div>

      <div className="metrics-grid">
        <MetricTile
          icon={Server}
          label="API"
          value={apiOnline ? "online" : "indisponivel"}
          detail={formatDateTime(health?.timestamp) || "aguardando leitura"}
          tone={apiOnline ? "good" : "warn"}
        />
        <MetricTile
          icon={Clock3}
          label="Uptime"
          value={formatDuration(metrics?.uptimeSeconds)}
          detail={`${metrics?.httpRequests || 0} requisicoes`}
          tone="neutral"
        />
        <MetricTile
          icon={Activity}
          label="Eventos"
          value={metrics?.events || 0}
          detail="registrados em metricas"
          tone="neutral"
        />
        <MetricTile
          icon={Shield}
          label="Operador"
          value={principal?.subject || "sem token"}
          detail={principal?.roles?.join(", ") || "autenticacao pendente"}
          tone={principal ? "good" : "warn"}
        />
      </div>

      <ProtectedNotice token={token} permission="Gere um token para carregar inventario, worker, prontidao e auditoria." />

      <InventorySnapshot snapshot={snapshot} />

      <WorkerStatusPanel workerStatus={workerStatus} />

      <div className="ops-grid">
        <div className="ops-panel">
          <div className="panel-title">
            <ListChecks size={18} />
            <h3>Prontidao</h3>
            {adReady !== undefined && (
              <StatusPill tone={adReady ? "good" : "warn"}>
                {adReady ? "configurada" : "pendente"}
              </StatusPill>
            )}
          </div>
          <ConfigChecklist summary={config} />
          {adCheck && (
            <div className="ad-check">
              <StatusPill tone={adCheck.bind_successful ? "good" : "warn"}>
                {adCheck.status}
              </StatusPill>
              <span>{adCheck.server}</span>
              <span>{adCheck.message}</span>
            </div>
          )}
        </div>

        <div className="ops-panel">
          <div className="panel-title">
            <Database size={18} />
            <h3>Auditoria recente</h3>
          </div>
          <DataTable
            rows={auditEvents}
            columns={[
              { key: "occurred_at", label: "Quando" },
              { key: "event", label: "Evento" },
              { key: "operator", label: "Operador" },
              { key: "target", label: "Alvo" },
            ]}
          />
        </div>
      </div>
    </section>
  );
}

function DirectoryView({ type, token, setMessage }) {
  const api = useApi(token, setMessage);
  const statusOptions =
    type === "users" ? userStatuses : type === "groups" ? groupStatuses : computerStatuses;
  const [status, setStatus] = useState(statusOptions[0]);
  const [query, setQuery] = useState("");
  const [ouDn, setOuDn] = useState("");
  const [groupDn, setGroupDn] = useState("");
  const [operatingSystem, setOperatingSystem] = useState("");
  const [inactiveDays, setInactiveDays] = useState(90);
  const [machinePasswordDays, setMachinePasswordDays] = useState(90);
  const [limit, setLimit] = useState(100);
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [userSuggestions, setUserSuggestions] = useState([]);
  const [userSuggestionsOpen, setUserSuggestionsOpen] = useState(false);
  const [userSearchLoading, setUserSearchLoading] = useState(false);
  const [userSearchSelected, setUserSearchSelected] = useState(false);

  const columns = {
    users: [
      { key: "sam_account_name", label: "Login" },
      { key: "display_name", label: "Nome" },
      { key: "email", label: "Email" },
      { key: "enabled", label: "Ativo" },
      { key: "last_logon_at", label: "Ultimo logon" },
      { key: "password_expires_at", label: "Senha expira em" },
      { key: "last_logon_computer", label: "Computador do logon" },
      { key: "last_logon_ip", label: "IP" },
    ],
    groups: [
      { key: "sam_account_name", label: "Grupo" },
      { key: "description", label: "Descricao" },
      { key: "member_count", label: "Membros" },
      { key: "managed_by", label: "Responsavel" },
    ],
    computers: [
      { key: "name", label: "Nome" },
      { key: "dns_hostname", label: "DNS" },
      { key: "operating_system", label: "Sistema" },
      { key: "enabled", label: "Ativo" },
      { key: "last_logon_at", label: "Ultimo logon" },
    ],
  }[type];

  useEffect(() => {
    setStatus(statusOptions[0]);
    setQuery("");
    setOuDn("");
    setGroupDn("");
    setOperatingSystem("");
    setInactiveDays(90);
    setMachinePasswordDays(90);
    setLimit(100);
    setRows([]);
    setUserSuggestions([]);
    setUserSuggestionsOpen(false);
    setUserSearchSelected(false);
  }, [type]);

  useEffect(() => {
    const normalizedQuery = query.trim();
    if (type !== "users" || !token || userSearchSelected || normalizedQuery.length < 2) {
      setUserSuggestions([]);
      setUserSearchLoading(false);
      return undefined;
    }

    let canceled = false;
    const timer = window.setTimeout(async () => {
      setUserSearchLoading(true);
      try {
        const params = buildQuery({
          status: "all",
          query: normalizedQuery,
          limit: 8,
        });
        const payload = await api.getJson(`/users?${params}`);
        if (!canceled) {
          setUserSuggestions(payload.items || []);
          setUserSuggestionsOpen(true);
        }
      } catch {
        if (!canceled) {
          setUserSuggestions([]);
        }
      } finally {
        if (!canceled) {
          setUserSearchLoading(false);
        }
      }
    }, 350);

    return () => {
      canceled = true;
      window.clearTimeout(timer);
    };
  }, [api, query, token, type, userSearchSelected]);

  function updateDirectoryQuery(value) {
    setQuery(value);
    setUserSearchSelected(false);
    setUserSuggestionsOpen(type === "users" && value.trim().length >= 2);
  }

  async function load(queryOverride = query) {
    const normalizedQuery = queryOverride.trim();
    if (normalizedQuery.length === 1) {
      setMessage({ type: "error", text: "Use pelo menos 2 caracteres na busca." });
      return;
    }

    setLoading(true);
    try {
      const params = buildQuery({
        status,
        query: normalizedQuery,
        ou_dn: ouDn.trim(),
        group_dn: type === "users" ? groupDn.trim() : "",
        operating_system: type === "computers" ? operatingSystem.trim() : "",
        inactive_days: ["users", "computers"].includes(type) ? inactiveDays : "",
        machine_password_days: type === "computers" ? machinePasswordDays : "",
        limit,
      });
      const payload = await api.getJson(`/${type}?${params}`);
      setRows(payload.items || []);
      setMessage({ type: "success", text: `${payload.count || 0} registro(s).` });
    } catch (error) {
      setMessage({ type: "error", text: operatorMessage(error) });
    } finally {
      setLoading(false);
    }
  }

  function selectDirectoryUser(user) {
    const identifier = targetIdentifier("users", user);
    setQuery(identifier);
    setUserSearchSelected(true);
    setUserSuggestions([]);
    setUserSuggestionsOpen(false);
    load(identifier);
  }

  return (
    <section className="section">
      <div className="section-head">
        <div>
          <h2>{tabs.find((tab) => tab.id === type).label}</h2>
          <p>{rows.length} item(ns)</p>
        </div>
        <button className="action-button" onClick={load} disabled={!token || loading}>
          <Search size={18} />
          Consultar
        </button>
      </div>
      <ProtectedNotice token={token} permission="Permissao necessaria: leitura do tipo selecionado." />
      <div className="advanced-filters">
        <label>
          Status
          <select value={status} onChange={(event) => setStatus(event.target.value)}>
            {statusOptions.map((option) => (
              <option key={option} value={option}>
                {labelFor("statuses", option)}
              </option>
            ))}
          </select>
        </label>
        <label className="wide">
          Busca
          <div className={type === "users" ? "target-picker" : ""}>
            <div className={type === "users" ? "searchbox target-search" : "searchbox"}>
              <Search size={18} />
              <input
                autoComplete={type === "users" ? "off" : undefined}
                value={query}
                onBlur={
                  type === "users"
                    ? () => window.setTimeout(() => setUserSuggestionsOpen(false), 120)
                    : undefined
                }
                onChange={(event) => updateDirectoryQuery(event.target.value)}
                onFocus={
                  type === "users"
                    ? () => setUserSuggestionsOpen(query.trim().length >= 2 && !userSearchSelected)
                    : undefined
                }
                placeholder={type === "users" ? "digite parte do nome, login ou email" : undefined}
              />
            </div>
            {type === "users" && userSuggestionsOpen && (
              <div className="target-suggestions">
                {userSearchLoading && <div className="target-suggestion muted">Buscando...</div>}
                {!userSearchLoading &&
                  userSuggestions.map((user) => {
                    const identifier = targetIdentifier("users", user);
                    return (
                      <button key={identifier} type="button" onMouseDown={() => selectDirectoryUser(user)}>
                        <strong>{targetTitle("users", user)}</strong>
                        <span>{targetSubtitle("users", user) || identifier}</span>
                      </button>
                    );
                  })}
                {!userSearchLoading && !userSuggestions.length && (
                  <div className="target-suggestion muted">Nenhum usuario encontrado</div>
                )}
              </div>
            )}
          </div>
        </label>
        <label className="wide">
          OU DN
          <input
            value={ouDn}
            onChange={(event) => setOuDn(event.target.value)}
            placeholder="Ex: OU=Usuarios,OU=AD Manager,DC=tce,DC=hml"
          />
        </label>
        {type === "users" && (
          <label className="wide">
            Grupo DN
            <input value={groupDn} onChange={(event) => setGroupDn(event.target.value)} />
          </label>
        )}
        {type === "computers" && (
          <label>
            Sistema operacional
            <input value={operatingSystem} onChange={(event) => setOperatingSystem(event.target.value)} />
          </label>
        )}
        {["users", "computers"].includes(type) && (
          <label>
            Inatividade dias
            <input
              min="1"
              max="3650"
              type="number"
              value={inactiveDays}
              onChange={(event) => setInactiveDays(event.target.value)}
            />
          </label>
        )}
        {type === "computers" && (
          <label>
            Senha maquina dias
            <input
              min="1"
              max="3650"
              type="number"
              value={machinePasswordDays}
              onChange={(event) => setMachinePasswordDays(event.target.value)}
            />
          </label>
        )}
        <label>
          Limite
          <input
            min="1"
            max="500"
            type="number"
            value={limit}
            onChange={(event) => setLimit(event.target.value)}
          />
        </label>
      </div>
      {type === "groups" && <UserGroupsLookup token={token} setMessage={setMessage} />}
      {type === "groups" && <GroupMembersLookup token={token} setMessage={setMessage} />}
      <DataTable rows={rows} columns={columns} />
    </section>
  );
}

function ReportsView({ token, setMessage }) {
  const api = useApi(token, setMessage);
  const [reportType, setReportType] = useState("users");
  const [status, setStatus] = useState("active");
  const [format, setFormat] = useState("json");
  const [query, setQuery] = useState("");
  const [ouDn, setOuDn] = useState("");
  const [groupDn, setGroupDn] = useState("");
  const [operatingSystem, setOperatingSystem] = useState("");
  const [inactiveDays, setInactiveDays] = useState(90);
  const [machinePasswordDays, setMachinePasswordDays] = useState(90);
  const [limit, setLimit] = useState(1000);
  const [payload, setPayload] = useState(null);

  const statusOptions =
    reportType === "users"
      ? userStatuses
      : reportType === "groups"
        ? groupStatuses
        : computerStatuses;

  async function runReport() {
    const normalizedQuery = query.trim();
    if (normalizedQuery.length === 1) {
      setMessage({ type: "error", text: "Use pelo menos 2 caracteres na busca." });
      return;
    }

    try {
      const commonParams = {
        status,
        query: normalizedQuery,
        ou_dn: ouDn.trim(),
        group_dn: reportType === "users" ? groupDn.trim() : "",
        operating_system: reportType === "computers" ? operatingSystem.trim() : "",
        inactive_days: ["users", "computers"].includes(reportType) ? inactiveDays : "",
        machine_password_days: reportType === "computers" ? machinePasswordDays : "",
        limit,
      };
      const jsonParams = buildQuery({ ...commonParams, format: "json" });
      const data = await api.getJson(`/reports/${reportType}?${jsonParams}`);
      setPayload(data);
      if (format === "csv") {
        const csvParams = buildQuery({ ...commonParams, format: "csv" });
        if (!data?.items?.length) {
          setMessage({
            type: "error",
            text: "Nenhum registro encontrado para os filtros informados. Verifique OU DN, status e limite.",
          });
          return;
        }
        await api.downloadCsv(`/reports/${reportType}?${csvParams}`, `${reportType}.csv`);
        return;
      }
      if (format === "pdf") {
        if (!data?.items?.length) {
          setMessage({
            type: "error",
            text: "Nenhum registro encontrado para os filtros informados. Verifique OU DN, status e limite.",
          });
          return;
        }
        exportReportPdf(data);
      }
      setMessage({ type: "success", text: "Relatorio gerado." });
    } catch (error) {
      setMessage({ type: "error", text: operatorMessage(error) });
    }
  }

  return (
    <section className="section">
      <div className="section-head">
        <div>
          <h2>Relatorios</h2>
          <p>{payload?.metadata?.row_count ?? 0} linha(s)</p>
        </div>
        <button className="action-button" onClick={runReport} disabled={!token}>
          {format === "pdf" ? <FileText size={18} /> : <Download size={18} />}
          Gerar
        </button>
      </div>
      <ProtectedNotice token={token} permission="Permissao necessaria: run:reports." />
      <div className="filters">
        <select
          value={reportType}
          onChange={(event) => {
            setReportType(event.target.value);
            setStatus(event.target.value === "groups" ? "all" : "active");
            setQuery("");
            setOuDn("");
            setGroupDn("");
            setOperatingSystem("");
            setInactiveDays(90);
            setMachinePasswordDays(90);
            setLimit(1000);
            setPayload(null);
          }}
        >
          <option value="users">Usuarios</option>
          <option value="groups">Grupos</option>
          <option value="computers">Computadores</option>
        </select>
        <select value={status} onChange={(event) => setStatus(event.target.value)}>
          {statusOptions.map((option) => (
            <option key={option} value={option}>
              {labelFor("statuses", option)}
            </option>
          ))}
        </select>
        <select value={format} onChange={(event) => setFormat(event.target.value)}>
          <option value="json">{labelFor("formats", "json")}</option>
          <option value="csv">{labelFor("formats", "csv")}</option>
          <option value="pdf">{labelFor("formats", "pdf")}</option>
        </select>
      </div>
      <div className="advanced-filters report-filters">
        <label className="wide">
          Busca
          <div className="searchbox">
            <Search size={18} />
            <input value={query} onChange={(event) => setQuery(event.target.value)} />
          </div>
        </label>
        <label className="wide">
          OU DN
          <input value={ouDn} onChange={(event) => setOuDn(event.target.value)} />
        </label>
        {reportType === "users" && (
          <label className="wide">
            Grupo DN
            <input value={groupDn} onChange={(event) => setGroupDn(event.target.value)} />
          </label>
        )}
        {reportType === "computers" && (
          <label>
            Sistema operacional
            <input value={operatingSystem} onChange={(event) => setOperatingSystem(event.target.value)} />
          </label>
        )}
        {["users", "computers"].includes(reportType) && (
          <label>
            Inatividade dias
            <input
              min="1"
              max="3650"
              type="number"
              value={inactiveDays}
              onChange={(event) => setInactiveDays(event.target.value)}
            />
          </label>
        )}
        {reportType === "computers" && (
          <label>
            Senha maquina dias
            <input
              min="1"
              max="3650"
              type="number"
              value={machinePasswordDays}
              onChange={(event) => setMachinePasswordDays(event.target.value)}
            />
          </label>
        )}
        <label>
          Limite
          <input
            min="1"
            max="5000"
            type="number"
            value={limit}
            onChange={(event) => setLimit(event.target.value)}
          />
        </label>
      </div>
      <DataTable rows={payload?.items || []} columns={Object.keys(payload?.items?.[0] || {}).slice(0, 6).map((key) => ({ key, label: labelFor("fields", key) }))} />
    </section>
  );
}

function WorkstationLogonsView({ token, setMessage }) {
  const api = useApi(token, setMessage);
  const [user, setUser] = useState("");
  const [computer, setComputer] = useState("");
  const [ip, setIp] = useState("");
  const [startDate, setStartDate] = useState(todayDateInputValue());
  const [endDate, setEndDate] = useState(todayDateInputValue());
  const [limit, setLimit] = useState(100);
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);

  async function loadLogons() {
    const normalizedUser = user.trim();
    const normalizedComputer = computer.trim();
    const normalizedIp = ip.trim();
    if ([normalizedUser, normalizedComputer, normalizedIp].some((value) => value.length === 1)) {
      setMessage({ type: "error", text: "Use pelo menos 2 caracteres nos filtros de texto." });
      return;
    }

    setLoading(true);
    try {
      const params = buildQuery({
        user: normalizedUser,
        computer: normalizedComputer,
        ip: normalizedIp,
        start: dateStartIso(startDate),
        end: dateEndIso(endDate),
        limit,
      });
      const data = await api.getJson(`/workstation-logons?${params}`);
      setRows(data || []);
      setMessage({ type: "success", text: `${data?.length || 0} logon(s) encontrado(s).` });
    } catch (error) {
      setMessage({ type: "error", text: operatorMessage(error) });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (token) {
      loadLogons();
    }
  }, [token]);

  return (
    <section className="section">
      <div className="section-head">
        <div>
          <h2>Logons recentes</h2>
          <p>{rows.length} evento(s) do coletor de estacao</p>
        </div>
        <button className="action-button" onClick={loadLogons} disabled={!token || loading}>
          <Search size={18} />
          Consultar
        </button>
      </div>
      <ProtectedNotice token={token} permission="Permissao necessaria: leitura de usuarios." />
      <div className="advanced-filters logon-filters">
        <label>
          Usuario
          <div className="searchbox">
            <Search size={18} />
            <input
              value={user}
              onChange={(event) => setUser(event.target.value)}
              placeholder="login ou usuario\\dominio"
            />
          </div>
        </label>
        <label>
          Computador
          <input
            value={computer}
            onChange={(event) => setComputer(event.target.value)}
            placeholder="nome da estacao"
          />
        </label>
        <label>
          IP
          <input value={ip} onChange={(event) => setIp(event.target.value)} placeholder="192.168" />
        </label>
        <label>
          Inicio
          <input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} />
        </label>
        <label>
          Fim
          <input type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} />
        </label>
        <label>
          Limite
          <input
            min="1"
            max="500"
            type="number"
            value={limit}
            onChange={(event) => setLimit(event.target.value)}
          />
        </label>
      </div>
      <DataTable
        rows={rows}
        columns={[
          { key: "received_at", label: "Recebido em" },
          { key: "reported_at", label: "Reportado em" },
          { key: "sam_account_name", label: "Usuario" },
          { key: "reported_user", label: "Usuario informado" },
          { key: "computer_name", label: "Computador" },
          { key: "ip_address", label: "IP" },
          { key: "source", label: "Origem" },
        ]}
      />
    </section>
  );
}

function LogsView({ token, setMessage }) {
  const api = useApi(token, setMessage);
  const [action, setAction] = useState("all");
  const [query, setQuery] = useState("");
  const [limit, setLimit] = useState(80);
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);

  async function loadLogs() {
    const normalizedQuery = query.trim();
    if (normalizedQuery.length === 1) {
      setMessage({ type: "error", text: "Use pelo menos 2 caracteres na busca." });
      return;
    }

    setLoading(true);
    try {
      const selectedAction = logActionOptions.find((option) => option.value === action) || logActionOptions[0];
      const eventNames = selectedAction.events || [selectedAction.event];
      const params = buildQuery({
        events: eventNames.join(","),
        operation: selectedAction.operation || "",
        q: normalizedQuery,
        limit,
      });
      const data = await api.getJson(`/audit/events?${params}`);
      setRows(data || []);
      setMessage({ type: "success", text: `${data?.length || 0} acao(oes) carregada(s).` });
    } catch (error) {
      setMessage({ type: "error", text: operatorMessage(error) });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (token) {
      loadLogs();
    }
  }, [token]);

  const normalizedRows = rows.map((row) => {
    const payload = row.payload || {};
    return {
      id: row.id,
      occurred_at: row.occurred_at,
      operator: row.operator || payload.operator || payload.username || "",
      roles: rolesText(payload.roles),
      action: actionLabel(row.event, payload.operation),
      target:
        payload.sam_account_name ||
        payload.target ||
        payload.identifier ||
        row.target ||
        payload.group_dn ||
        payload.user_dn ||
        payload.distinguished_name ||
        "",
      origin: payload.origin || payload.client_host || "",
      mode: payload.dry_run === false ? "Executado no AD" : "Simulacao",
      reason: payload.reason || "",
      raw_event: row.event,
    };
  });

  return (
    <section className="section">
      <div className="section-head">
        <div>
          <h2>Logs</h2>
          <p>{rows.length} acao(oes)</p>
        </div>
        <button className="action-button" onClick={loadLogs} disabled={!token || loading}>
          <Search size={18} />
          Consultar
        </button>
      </div>
      <ProtectedNotice token={token} permission="Permissao necessaria: leitura de auditoria." />
      <div className="advanced-filters log-filters">
        <label>
          Acao
          <select value={action} onChange={(event) => setAction(event.target.value)}>
            {logActionOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label className="wide">
          Busca
          <div className="searchbox">
            <Search size={18} />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="usuario, acao, alvo, origem ou grupo"
            />
          </div>
        </label>
        <label>
          Linhas
          <input
            min="20"
            max="500"
            type="number"
            value={limit}
            onChange={(event) => setLimit(event.target.value)}
          />
        </label>
      </div>
      <div className="log-table-wrap">
        <table className="log-table">
          <thead>
            <tr>
              <th>Data/hora</th>
              <th>Usuario AD</th>
              <th>Origem</th>
              <th>Perfil</th>
              <th>Acao</th>
              <th>Modo</th>
              <th>Alvo</th>
              <th>Justificativa</th>
            </tr>
          </thead>
          <tbody>
            {normalizedRows.map((row) => (
              <tr key={row.id}>
                <td>{displayValue(row.occurred_at)}</td>
                <td>{row.operator}</td>
                <td>{row.origin}</td>
                <td>{row.roles}</td>
                <td>{row.action}</td>
                <td>{row.mode}</td>
                <td className="clip-cell" title={row.target}>{row.target}</td>
                <td className="clip-cell" title={row.reason}>{row.reason}</td>
              </tr>
            ))}
            {!normalizedRows.length && (
              <tr>
                <td colSpan="8">Sem dados</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

const operationCatalog = {
  users: [
    {
      id: "unlock",
      label: "Desbloquear usuario",
      impact: "Remove o bloqueio da conta, sem alterar senha ou habilitacao.",
      severity: "moderate",
    },
    {
      id: "force-password-change",
      label: "Forcar troca de senha",
      impact: "Marca a conta para alterar senha no proximo logon.",
      severity: "moderate",
    },
    {
      id: "enable",
      label: "Habilitar usuario",
      impact: "Permite autenticacao da conta no dominio.",
      severity: "high",
    },
    {
      id: "disable",
      label: "Desabilitar usuario",
      impact: "Bloqueia autenticacao da conta no dominio.",
      severity: "high",
    },
    {
      id: "reset-password",
      label: "Resetar senha",
      impact: "Define uma senha temporaria. Execucao real exige LDAPS.",
      severity: "critical",
    },
    {
      id: "account-expiration",
      label: "Alterar expiracao da conta",
      impact: "Carrega a configuracao atual e permite simular nova data de expiracao da conta.",
      severity: "high",
    },
    {
      id: "add-group",
      label: "Adicionar usuario a grupo",
      impact: "Adiciona o usuario selecionado como membro de um grupo carregado.",
      severity: "high",
    },
    {
      id: "remove-group",
      label: "Remover usuario de grupo",
      impact: "Remove o usuario selecionado de um grupo carregado.",
      severity: "high",
    },
  ],
  computers: [
    {
      id: "enable",
      label: "Habilitar computador",
      impact: "Permite que a conta de computador autentique no dominio.",
      severity: "high",
    },
    {
      id: "disable",
      label: "Desabilitar computador",
      impact: "Impede autenticacao da conta de computador.",
      severity: "critical",
    },
    {
      id: "metadata",
      label: "Atualizar metadados",
      impact: "Atualiza descricao, localizacao ou responsavel do computador.",
      severity: "moderate",
    },
  ],
};

function objectLabel(type) {
  return type === "users" ? "Usuario" : "Computador";
}

function operationPath(type, target, operation) {
  const encodedTarget = encodeURIComponent(target.trim());
  return type === "users" ? `/users/${encodedTarget}/${operation}` : `/computers/${encodedTarget}/${operation}`;
}

function targetIdentifier(type, item) {
  if (type === "users") return item.sam_account_name || item.user_principal_name || item.distinguished_name || "";
  return item.name || item.sam_account_name || item.dns_hostname || item.distinguished_name || "";
}

function targetTitle(type, item) {
  if (type === "users") return item.display_name || item.sam_account_name || item.user_principal_name || "";
  return item.name || item.dns_hostname || item.sam_account_name || "";
}

function targetSubtitle(type, item) {
  if (type === "users") return [item.sam_account_name, item.email].filter(Boolean).join(" · ");
  return [item.dns_hostname, item.operating_system].filter(Boolean).join(" · ");
}

function isGroupMembershipOperation(operation) {
  return ["add-group", "remove-group"].includes(operation);
}

function OperationSummary({
  targetType,
  operation,
  target,
  reason,
  metadata,
  executionMode,
  selectedGroup,
}) {
  const selected = operationCatalog[targetType].find((item) => item.id === operation);
  const metadataChanges = Object.entries(metadata).filter(([, value]) => value.trim());
  const isRealExecution = executionMode === "execute";

  return (
    <div className={`operation-summary ${isRealExecution ? "real-execution" : ""}`}>
      <div className="panel-title">
        {isRealExecution ? <AlertTriangle size={18} /> : <Shield size={18} />}
        <h3>{isRealExecution ? "Resumo da execucao no AD" : "Resumo da simulacao"}</h3>
        <StatusPill tone={isRealExecution || selected?.severity === "critical" ? "warn" : "neutral"}>
          {isRealExecution ? "alteracao real" : selected?.severity || "normal"}
        </StatusPill>
      </div>
      <dl>
        <div>
          <dt>Objeto</dt>
          <dd>{objectLabel(targetType)}</dd>
        </div>
        <div>
          <dt>Alvo</dt>
          <dd>{target || "pendente"}</dd>
        </div>
        <div>
          <dt>Acao</dt>
          <dd>{selected?.label}</dd>
        </div>
        <div>
          <dt>Modo</dt>
          <dd>{isRealExecution ? "Executar no AD" : "Simulacao"}</dd>
        </div>
        {isGroupMembershipOperation(operation) && (
          <div>
            <dt>Grupo</dt>
            <dd>{selectedGroup?.common_name || selectedGroup?.sam_account_name || "pendente"}</dd>
          </div>
        )}
      </dl>
      <p>{selected?.impact}</p>
      {isRealExecution && (
        <div className="real-execution-warning">
          Esta acao sera enviada com alteracao real para o Active Directory. Confirme o alvo, a acao
          e a justificativa antes de executar.
        </div>
      )}
      {metadataChanges.length > 0 && (
        <div className="change-list">
          {metadataChanges.map(([key, value]) => (
            <span key={key}>
              {labelFor("metadata", key)}: {value}
            </span>
          ))}
        </div>
      )}
      <div className={reason.length >= 8 ? "reason-state good" : "reason-state warn"}>
        {reason.length >= 8 ? "Justificativa pronta" : "Justificativa minima: 8 caracteres"}
      </div>
    </div>
  );
}

function DirectoryStateCard({ title, state }) {
  if (!state) return null;
  const rows = [
    ["Nome", state.display_name || state.name || state.common_name],
    ["Login", state.sam_account_name],
    ["Ativo", state.enabled === undefined ? "" : state.enabled ? "sim" : "nao"],
    ["Bloqueado", state.locked === undefined ? "" : state.locked ? "sim" : "nao"],
    ["Expiracao da conta", state.account_expires_at || "Nunca"],
    ["Ultimo logon", state.last_logon_at],
    ["Computador do logon", state.last_logon_computer],
    ["IP do logon", state.last_logon_ip],
    ["Status recebido em", state.workstation_status_at],
    ["DN", state.distinguished_name],
  ].filter(([, value]) => value !== undefined && value !== null && value !== "");

  return (
    <div className="state-card">
      <h3>{title}</h3>
      <dl>
        {rows.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{displayValue(value)}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

function OperationResult({ result }) {
  if (!result) return null;
  const isGroupOperation = Boolean(result.group);
  return (
    <div className="operation-result">
      <div className="result-banner">
        <CheckCircle2 size={18} />
        <div>
          <strong>{result.message}</strong>
          <span>
            {result.dry_run ? "Simulacao sem alteracao no AD" : "Alteracao real executada"} ·{" "}
            {result.changed ? "com mudanca" : "sem mudanca real"}
          </span>
        </div>
      </div>
      {isGroupOperation ? (
        <div className="state-card">
          <h3>Grupo</h3>
          <dl>
            <div>
              <dt>Grupo</dt>
              <dd>{result.group.common_name || result.group.sam_account_name}</dd>
            </div>
            <div>
              <dt>Usuario</dt>
              <dd>{result.sam_account_name}</dd>
            </div>
            <div>
              <dt>Grupo protegido</dt>
              <dd>{result.protected_group ? "Sim" : "Nao"}</dd>
            </div>
            <div>
              <dt>DN do grupo</dt>
              <dd>{result.group.distinguished_name}</dd>
            </div>
          </dl>
        </div>
      ) : (
        <div className="state-grid">
          <DirectoryStateCard title="Antes" state={result.before} />
          <DirectoryStateCard title="Depois" state={result.after} />
        </div>
      )}
    </div>
  );
}

function OperationsView({ token, setMessage }) {
  const api = useApi(token, setMessage);
  const [runtimeConfig, setRuntimeConfig] = useState(null);
  const [targetType, setTargetType] = useState("users");
  const [target, setTarget] = useState("");
  const [operation, setOperation] = useState("unlock");
  const [executionMode, setExecutionMode] = useState("simulate");
  const [reason, setReason] = useState("");
  const [confirmOperation, setConfirmOperation] = useState(false);
  const [newPassword, setNewPassword] = useState("");
  const [forceChangeAtNextLogon, setForceChangeAtNextLogon] = useState(true);
  const [accountExpirationLoaded, setAccountExpirationLoaded] = useState(false);
  const [currentAccountExpiration, setCurrentAccountExpiration] = useState(null);
  const [accountNeverExpires, setAccountNeverExpires] = useState(true);
  const [accountExpirationDate, setAccountExpirationDate] = useState("");
  const [groupQuery, setGroupQuery] = useState("");
  const [selectedGroup, setSelectedGroup] = useState(null);
  const [groupLoaded, setGroupLoaded] = useState(false);
  const [groupSuggestions, setGroupSuggestions] = useState([]);
  const [groupSearchOpen, setGroupSearchOpen] = useState(false);
  const [groupSearchLoading, setGroupSearchLoading] = useState(false);
  const [confirmGroupMembership, setConfirmGroupMembership] = useState(false);
  const [metadata, setMetadata] = useState({ description: "", location: "", managed_by: "" });
  const [result, setResult] = useState(null);
  const [targetSuggestions, setTargetSuggestions] = useState([]);
  const [targetSearchOpen, setTargetSearchOpen] = useState(false);
  const [targetSearchLoading, setTargetSearchLoading] = useState(false);
  const [targetSelected, setTargetSelected] = useState(false);

  const operations = operationCatalog[targetType];
  const selectedOperation = operations.find((item) => item.id === operation);
  const runtimeConfigLoaded = Boolean(runtimeConfig);
  const simulationAvailable = runtimeConfigLoaded && runtimeConfig.operation_simulation_enabled !== false;
  const isProduction = runtimeConfig?.is_production || runtimeConfig?.app_env?.toLowerCase() === "production";
  const isRealExecution = runtimeConfigLoaded && (!simulationAvailable || executionMode === "execute");
  const metadataReady =
    operation !== "metadata" || Object.values(metadata).some((value) => value.trim().length > 0);
  const passwordReady = operation !== "reset-password" || newPassword.length >= 8;
  const accountExpirationReady =
    operation !== "account-expiration" ||
    (accountExpirationLoaded && (accountNeverExpires || accountExpirationDate));
  const groupMembershipReady = !isGroupMembershipOperation(operation) || (groupLoaded && selectedGroup);
  const groupConfirmationReady = !isGroupMembershipOperation(operation) || confirmGroupMembership;
  const canSubmit =
    runtimeConfigLoaded &&
    Boolean(token) &&
    target.trim().length > 0 &&
    reason.trim().length >= 8 &&
    confirmOperation &&
    metadataReady &&
    passwordReady &&
    accountExpirationReady &&
    groupMembershipReady &&
    groupConfirmationReady;

  function resetAccountExpirationState() {
    setAccountExpirationLoaded(false);
    setCurrentAccountExpiration(null);
    setAccountNeverExpires(true);
    setAccountExpirationDate("");
  }

  function resetGroupMembershipState() {
    setGroupQuery("");
    setSelectedGroup(null);
    setGroupLoaded(false);
    setGroupSuggestions([]);
    setGroupSearchOpen(false);
    setGroupSearchLoading(false);
    setConfirmGroupMembership(false);
  }

  function resetOperationState(nextType = targetType, nextOperation = operation) {
    setTarget("");
    setTargetSuggestions([]);
    setTargetSearchOpen(false);
    setTargetSelected(false);
    setExecutionMode(simulationAvailable ? "simulate" : "execute");
    setReason("");
    setConfirmOperation(false);
    setNewPassword("");
    setForceChangeAtNextLogon(true);
    resetAccountExpirationState();
    resetGroupMembershipState();
    setMetadata({ description: "", location: "", managed_by: "" });
    setResult(null);
    setOperation(nextOperation || operationCatalog[nextType][0].id);
  }

  useEffect(() => {
    if (!token) {
      setRuntimeConfig(null);
      return undefined;
    }

    let canceled = false;
    async function loadRuntimeConfig() {
      try {
        const payload = await api.getJson("/config/runtime");
        if (canceled) return;
        setRuntimeConfig(payload);
        if (payload.operation_simulation_enabled === false) {
          setExecutionMode("execute");
        }
      } catch {
        if (!canceled) {
          setRuntimeConfig(null);
          setMessage({ type: "error", text: "Nao foi possivel carregar o modo operacional." });
        }
      }
    }

    loadRuntimeConfig();
    return () => {
      canceled = true;
    };
  }, [api, token]);

  function updateTarget(value) {
    setTarget(value);
    setTargetSelected(false);
    setConfirmOperation(false);
    setResult(null);
    resetAccountExpirationState();
    resetGroupMembershipState();
    setTargetSearchOpen(value.trim().length >= 2);
  }

  function selectTarget(item) {
    const identifier = targetIdentifier(targetType, item);
    setTarget(identifier);
    setTargetSelected(true);
    setTargetSuggestions([]);
    setTargetSearchOpen(false);
    setConfirmOperation(false);
    setResult(null);
    resetAccountExpirationState();
    resetGroupMembershipState();
  }

  useEffect(() => {
    const normalizedTarget = target.trim();
    if (!token || targetSelected || normalizedTarget.length < 2) {
      setTargetSuggestions([]);
      setTargetSearchLoading(false);
      return undefined;
    }

    let canceled = false;
    const timer = window.setTimeout(async () => {
      setTargetSearchLoading(true);
      try {
        const params = buildQuery({
          status: "all",
          query: normalizedTarget,
          limit: 8,
        });
        const payload = await api.getJson(`/${targetType}?${params}`);
        if (!canceled) {
          setTargetSuggestions(payload.items || []);
          setTargetSearchOpen(true);
        }
      } catch {
        if (!canceled) {
          setTargetSuggestions([]);
        }
      } finally {
        if (!canceled) {
          setTargetSearchLoading(false);
        }
      }
    }, 350);

    return () => {
      canceled = true;
      window.clearTimeout(timer);
    };
  }, [api, target, targetSelected, targetType, token]);

  useEffect(() => {
    const normalizedGroup = groupQuery.trim();
    if (
      !token ||
      !isGroupMembershipOperation(operation) ||
      selectedGroup ||
      groupLoaded ||
      normalizedGroup.length < 2
    ) {
      setGroupSuggestions([]);
      setGroupSearchLoading(false);
      return undefined;
    }

    let canceled = false;
    const timer = window.setTimeout(async () => {
      setGroupSearchLoading(true);
      try {
        const params = buildQuery({
          status: "all",
          query: normalizedGroup,
          limit: 8,
        });
        const payload = await api.getJson(`/groups?${params}`);
        if (!canceled) {
          setGroupSuggestions(payload.items || []);
          setGroupSearchOpen(true);
        }
      } catch {
        if (!canceled) {
          setGroupSuggestions([]);
        }
      } finally {
        if (!canceled) {
          setGroupSearchLoading(false);
        }
      }
    }, 350);

    return () => {
      canceled = true;
      window.clearTimeout(timer);
    };
  }, [api, groupLoaded, groupQuery, operation, selectedGroup, token]);

  async function loadAccountExpiration() {
    const normalizedTarget = target.trim();
    if (targetType !== "users" || normalizedTarget.length < 2) {
      setMessage({ type: "error", text: "Selecione um usuario antes de carregar a expiracao da conta." });
      return;
    }

    try {
      const user = await api.getJson(`/users/${encodeURIComponent(normalizedTarget)}`);
      const expiresAt = isNeverAccountExpiration(user.account_expires_at) ? "" : user.account_expires_at || "";
      setCurrentAccountExpiration(expiresAt);
      setAccountNeverExpires(!expiresAt);
      setAccountExpirationDate(dateInputFromIso(expiresAt));
      setAccountExpirationLoaded(true);
      setResult(null);
      setMessage({ type: "success", text: "Configuracao atual carregada." });
    } catch (error) {
      setMessage({ type: "error", text: operatorMessage(error) });
    }
  }

  function updateGroupQuery(value) {
    setGroupQuery(value);
    setSelectedGroup(null);
    setGroupLoaded(false);
    setConfirmGroupMembership(false);
    setConfirmOperation(false);
    setResult(null);
    setGroupSearchOpen(value.trim().length >= 2);
  }

  function selectOperationGroup(group) {
    const identifier = groupIdentifier(group);
    setSelectedGroup(group);
    setGroupQuery(groupTitle(group) || identifier);
    setGroupLoaded(false);
    setConfirmGroupMembership(false);
    setGroupSuggestions([]);
    setGroupSearchOpen(false);
    setConfirmOperation(false);
    setResult(null);
  }

  async function loadOperationGroup() {
    const normalizedGroup = groupQuery.trim();
    if (!isGroupMembershipOperation(operation) || normalizedGroup.length < 2) {
      setMessage({ type: "error", text: "Selecione um grupo antes de carregar." });
      return;
    }

    try {
      const params = buildQuery({ status: "all", query: normalizedGroup, limit: 8 });
      const payload = await api.getJson(`/groups?${params}`);
      const exactGroup =
        (payload.items || []).find((group) => {
          const identifier = groupIdentifier(group);
          return (
            identifier === normalizedGroup ||
            group.sam_account_name === normalizedGroup ||
            group.common_name === normalizedGroup ||
            group.name === normalizedGroup
          );
        }) || (payload.items || [])[0];

      if (!exactGroup) {
        setMessage({ type: "error", text: "Grupo nao encontrado." });
        return;
      }

      setSelectedGroup(exactGroup);
      setGroupQuery(groupTitle(exactGroup) || groupIdentifier(exactGroup));
      setGroupLoaded(true);
      setConfirmGroupMembership(false);
      setGroupSuggestions([]);
      setGroupSearchOpen(false);
      setResult(null);
      setMessage({ type: "success", text: "Grupo carregado." });
    } catch (error) {
      setMessage({ type: "error", text: operatorMessage(error) });
    }
  }

  async function runOperation(event) {
    event.preventDefault();
    try {
      const requestBody = {
        confirm: true,
        dry_run: simulationAvailable ? !isRealExecution : false,
        reason: reason.trim(),
      };
      if (operation === "reset-password") {
        requestBody.new_password = newPassword;
        requestBody.force_change_at_next_logon = forceChangeAtNextLogon;
      }
      if (operation === "account-expiration") {
        requestBody.never_expires = accountNeverExpires;
        requestBody.expires_at = accountNeverExpires ? null : dateEndIso(accountExpirationDate);
      }
      if (operation === "metadata") {
        Object.entries(metadata).forEach(([key, value]) => {
          if (value.trim()) requestBody[key] = value.trim();
        });
      }
      let path = operationPath(targetType, target, operation);
      if (isGroupMembershipOperation(operation)) {
        requestBody.sam_account_name = target.trim();
        requestBody.protected_group_confirm = confirmGroupMembership;
        const groupTarget = groupIdentifier(selectedGroup || {});
        path = `/groups/${encodeURIComponent(groupTarget)}/members/${
          operation === "add-group" ? "add" : "remove"
        }`;
      }
      const payload = await api.postJson(path, requestBody);
      setResult(payload);
      setConfirmOperation(false);
      setMessage({
        type: "success",
        text: isRealExecution ? "Alteracao executada no AD." : "Simulacao concluida.",
      });
    } catch (error) {
      setMessage({ type: "error", text: operatorMessage(error) });
    }
  }

  return (
    <section className="section">
      <div className="section-head">
        <div>
          <h2>Operacoes</h2>
          <p>{selectedOperation?.impact}</p>
        </div>
        <StatusPill tone={isRealExecution ? "warn" : "neutral"}>
          {!runtimeConfigLoaded ? "carregando" : isRealExecution ? (isProduction ? "producao" : "executar no AD") : "simulacao"}
        </StatusPill>
      </div>
      <ProtectedNotice token={token} permission="Permissao necessaria: write:users, write:groups ou write:computers." />
      <form className="sensitive-operation" onSubmit={runOperation}>
        {!runtimeConfigLoaded ? (
          <div className="production-execution-mode pending">
            <Activity size={18} />
            <div>
              <strong>Carregando modo operacional</strong>
              <span>Aguarde a leitura da configuracao antes de executar operacoes.</span>
            </div>
          </div>
        ) : simulationAvailable ? (
          <div className={`execution-mode-selector ${isRealExecution ? "real" : ""}`}>
            <button
              className={executionMode === "simulate" ? "active" : ""}
              type="button"
              onClick={() => {
                setExecutionMode("simulate");
                setConfirmOperation(false);
                setResult(null);
              }}
            >
              <Shield size={18} />
              Simular
            </button>
            <button
              className={executionMode === "execute" ? "active" : ""}
              type="button"
              onClick={() => {
                setExecutionMode("execute");
                setConfirmOperation(false);
                setResult(null);
              }}
            >
              <AlertTriangle size={18} />
              Executar no AD
            </button>
          </div>
        ) : (
          <div className="production-execution-mode">
            <AlertTriangle size={18} />
            <div>
              <strong>Modo producao</strong>
              <span>Simulacao indisponivel. As operacoes confirmadas serao executadas no AD.</span>
            </div>
          </div>
        )}
        <div className="operation-fields">
          <label>
            Objeto
            <select
              value={targetType}
              onChange={(event) => {
                const nextType = event.target.value;
                setTargetType(nextType);
                resetOperationState(nextType, operationCatalog[nextType][0].id);
              }}
            >
              <option value="users">Usuario</option>
              <option value="computers">Computador</option>
            </select>
          </label>
          <label>
            Acao
            <select
              value={operation}
              onChange={(event) => {
                setOperation(event.target.value);
                setConfirmOperation(false);
                setResult(null);
                resetAccountExpirationState();
                resetGroupMembershipState();
              }}
            >
              {operations.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          <label className="wide">
            Alvo
            <div className="target-picker">
              <div className="searchbox target-search">
                <Search size={18} />
                <input
                  autoComplete="off"
                  value={target}
                  onChange={(event) => updateTarget(event.target.value)}
                  onFocus={() => setTargetSearchOpen(target.trim().length >= 2)}
                  onBlur={() => window.setTimeout(() => setTargetSearchOpen(false), 120)}
                  placeholder={
                    targetType === "users"
                      ? "digite parte do nome, login ou email"
                      : "digite parte do nome, DNS ou sistema"
                  }
                />
              </div>
              {targetSearchOpen && (
                <div className="target-suggestions">
                  {targetSearchLoading && <div className="target-suggestion muted">Buscando...</div>}
                  {!targetSearchLoading &&
                    targetSuggestions.map((item) => {
                      const identifier = targetIdentifier(targetType, item);
                      return (
                        <button key={identifier} type="button" onMouseDown={() => selectTarget(item)}>
                          <strong>{targetTitle(targetType, item)}</strong>
                          <span>{targetSubtitle(targetType, item) || identifier}</span>
                        </button>
                      );
                    })}
                  {!targetSearchLoading && !targetSuggestions.length && (
                    <div className="target-suggestion muted">Nenhum resultado encontrado</div>
                  )}
                </div>
              )}
            </div>
          </label>
          <label className="wide">
            Justificativa
            <input value={reason} onChange={(event) => setReason(event.target.value)} />
          </label>
          {operation === "reset-password" && (
            <>
              <label className="wide">
                Senha temporaria
                <input
                  type="password"
                  value={newPassword}
                  onChange={(event) => setNewPassword(event.target.value)}
                />
              </label>
              <label className="toggle-row">
                <input
                  checked={forceChangeAtNextLogon}
                  type="checkbox"
                  onChange={(event) => setForceChangeAtNextLogon(event.target.checked)}
                />
                Forcar troca no proximo logon
              </label>
            </>
          )}
          {operation === "account-expiration" && (
            <>
              <label className="wide account-expiration-state">
                Expiracao atual
                <div className="readonly-field">
                  {accountExpirationLoaded
                    ? currentAccountExpiration
                      ? displayValue(currentAccountExpiration)
                      : "Nunca"
                    : "Carregue a configuracao atual para alterar"}
                </div>
              </label>
              <button
                className="inline-action-button"
                type="button"
                onClick={loadAccountExpiration}
                disabled={!token || targetType !== "users" || target.trim().length < 2}
              >
                <Search size={18} />
                Carregar atual
              </button>
              <div className="account-expiration-picker">
                <label>
                  <input
                    checked={accountNeverExpires}
                    disabled={!accountExpirationLoaded}
                    name="account-expiration-mode"
                    type="radio"
                    onChange={() => setAccountNeverExpires(true)}
                  />
                  Nunca
                </label>
                <label>
                  <input
                    checked={!accountNeverExpires}
                    disabled={!accountExpirationLoaded}
                    name="account-expiration-mode"
                    type="radio"
                    onChange={() => {
                      setAccountNeverExpires(false);
                      if (!accountExpirationDate) setAccountExpirationDate(todayDateInputValue());
                    }}
                  />
                  Expira em
                </label>
                <input
                  disabled={!accountExpirationLoaded || accountNeverExpires}
                  type="date"
                  value={accountExpirationDate}
                  onChange={(event) => setAccountExpirationDate(event.target.value)}
                />
              </div>
            </>
          )}
          {isGroupMembershipOperation(operation) && (
            <>
              <label className="wide">
                Grupo
                <div className="target-picker">
                  <div className="searchbox target-search">
                    <Search size={18} />
                    <input
                      autoComplete="off"
                      value={groupQuery}
                      onBlur={() => window.setTimeout(() => setGroupSearchOpen(false), 120)}
                      onChange={(event) => updateGroupQuery(event.target.value)}
                      onFocus={() => setGroupSearchOpen(groupQuery.trim().length >= 2 && !groupLoaded)}
                      placeholder="digite parte do nome ou descricao do grupo"
                    />
                  </div>
                  {groupSearchOpen && (
                    <div className="target-suggestions">
                      {groupSearchLoading && <div className="target-suggestion muted">Buscando...</div>}
                      {!groupSearchLoading &&
                        groupSuggestions.map((group) => {
                          const identifier = groupIdentifier(group);
                          return (
                            <button key={identifier} type="button" onMouseDown={() => selectOperationGroup(group)}>
                              <strong>{groupTitle(group)}</strong>
                              <span>{groupSubtitle(group) || identifier}</span>
                            </button>
                          );
                        })}
                      {!groupSearchLoading && !groupSuggestions.length && (
                        <div className="target-suggestion muted">Nenhum grupo encontrado</div>
                      )}
                    </div>
                  )}
                </div>
              </label>
              <button
                className="inline-action-button"
                type="button"
                onClick={loadOperationGroup}
                disabled={!token || groupQuery.trim().length < 2}
              >
                <Search size={18} />
                Carregar grupo
              </button>
              <label className="wide account-expiration-state">
                Grupo carregado
                <div className="readonly-field">
                  {groupLoaded && selectedGroup
                    ? `${groupTitle(selectedGroup) || selectedGroup.sam_account_name} · ${
                        selectedGroup.member_count ?? 0
                      } membro(s)`
                    : "Carregue o grupo antes de executar"}
                </div>
              </label>
              <label className="toggle-row">
                <input
                  checked={confirmGroupMembership}
                  disabled={!groupLoaded}
                  type="checkbox"
                  onChange={(event) => setConfirmGroupMembership(event.target.checked)}
                />
                Confirmo o grupo carregado para esta operacao.
              </label>
            </>
          )}
          {operation === "metadata" && (
            <>
              <label>
                Descricao
                <input
                  value={metadata.description}
                  onChange={(event) => setMetadata({ ...metadata, description: event.target.value })}
                />
              </label>
              <label>
                Localizacao
                <input
                  value={metadata.location}
                  onChange={(event) => setMetadata({ ...metadata, location: event.target.value })}
                />
              </label>
              <label className="wide">
                Responsavel DN
                <input
                  value={metadata.managed_by}
                  onChange={(event) => setMetadata({ ...metadata, managed_by: event.target.value })}
                />
              </label>
            </>
          )}
        </div>
        <OperationSummary
          metadata={metadata}
          operation={operation}
          reason={reason}
          target={target}
          targetType={targetType}
          executionMode={executionMode}
          selectedGroup={selectedGroup}
        />
        <label className="confirm-row">
          <input
            checked={confirmOperation}
            type="checkbox"
            onChange={(event) => setConfirmOperation(event.target.checked)}
          />
          {isRealExecution
            ? "Confirmo executar esta alteracao diretamente no AD."
            : "Confirmo a simulacao para este alvo."}
        </label>
        <button className={isRealExecution ? "danger-action" : ""} type="submit" disabled={!canSubmit}>
          {isRealExecution ? <AlertTriangle size={18} /> : <Activity size={18} />}
          {isRealExecution ? "Executar no AD" : "Executar simulacao"}
        </button>
      </form>
      <OperationResult result={result} />
    </section>
  );
}

function App() {
  const [token, setToken] = useState(window.localStorage.getItem("accessToken") || "");
  const [principal, setPrincipal] = useState(() => {
    try {
      return JSON.parse(window.localStorage.getItem("principal") || "null");
    } catch {
      return null;
    }
  });
  const [activeTab, setActiveTab] = useState("dashboard");
  const [message, setMessage] = useState(null);

  function logout() {
    setToken("");
    setPrincipal(null);
    window.localStorage.removeItem("accessToken");
    window.localStorage.removeItem("principal");
    setMessage({ type: "success", text: "Sessao encerrada." });
  }

  if (!token) {
    return (
      <>
        <LoginPanel setToken={setToken} setPrincipal={setPrincipal} setMessage={setMessage} />
        {message && (
          <div className={`notice login-notice ${message.type}`}>
            <span>{message.text}</span>
          </div>
        )}
      </>
    );
  }

  return (
    <main className="shell">
      <header className="topbar">
        <div className="topbar-brand">
          <img className="topbar-logo" src={logoTceAl} alt="TCE-AL" />
          <div>
            <p className="eyebrow">TCE-AL · Active Directory Manager</p>
            <h1>Console operacional</h1>
          </div>
        </div>
        <div className="session-box">
          <div className="token-state on">
            <CheckCircle2 size={18} />
            <span>{principal?.display_name || principal?.subject || "autenticado"}</span>
          </div>
          <div className="role-row">
            {(principal?.roles || []).map((role) => (
              <StatusPill key={role} tone="neutral">{labelFor("roles", role)}</StatusPill>
            ))}
          </div>
          <button className="logout-button" type="button" onClick={logout}>
            <LogOut size={18} />
            Sair
          </button>
        </div>
      </header>

      {message && (
        <div className={`notice ${message.type}`}>
          <span>{message.text}</span>
        </div>
      )}

      <nav className="tabs">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              className={activeTab === tab.id ? "active" : ""}
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
            >
              <Icon size={18} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </nav>

      {activeTab === "dashboard" && <DashboardView token={token} setMessage={setMessage} />}
      {["users", "groups", "computers"].includes(activeTab) && (
        <DirectoryView type={activeTab} token={token} setMessage={setMessage} />
      )}
      {activeTab === "reports" && <ReportsView token={token} setMessage={setMessage} />}
      {activeTab === "operations" && <OperationsView token={token} setMessage={setMessage} />}
      {activeTab === "logons" && <WorkstationLogonsView token={token} setMessage={setMessage} />}
      {activeTab === "logs" && <LogsView token={token} setMessage={setMessage} />}
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
