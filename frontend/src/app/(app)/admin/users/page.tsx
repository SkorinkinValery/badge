"use client";

import { useCallback, useEffect, useState } from "react";
import { authHeaders } from "@/lib/auth";
import { useIsAdmin } from "@/lib/use-admin";
import type { User } from "@/lib/types";
import { Page } from "@/components/app-shell/Page";
import { Forbidden } from "@/components/system";
import {
  Button,
  ConfirmDialog,
  DataTable,
  EmptyState,
  Field,
  Skeleton,
  inputClass,
  toast,
} from "@/components/ui";

export default function UsersPage() {
  const admin = useIsAdmin();
  const [users, setUsers] = useState<User[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("viewer");
  const [error, setError] = useState<string | null>(null);
  const [toDelete, setToDelete] = useState<User | null>(null);

  const reload = useCallback(() => {
    fetch("/api/admin/users", { headers: authHeaders() })
      .then((r) => r.json())
      .then((data) => {
        setUsers(data as User[]);
        setLoaded(true);
      });
  }, []);

  useEffect(() => {
    if (admin) reload();
  }, [admin, reload]);

  if (admin === false) return <Forbidden />;

  async function createUser() {
    setError(null);
    const resp = await fetch("/api/admin/users", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ login, password, role }),
    });
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      setError(body?.detail ?? `Ошибка ${resp.status}`);
      return;
    }
    setLogin("");
    setPassword("");
    setRole("viewer");
    toast("Пользователь создан", "success");
    reload();
  }

  async function toggleActive(u: User) {
    await fetch(`/api/admin/users/${u.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ is_active: !u.is_active }),
    });
    reload();
  }

  async function removeUser(u: User) {
    await fetch(`/api/admin/users/${u.id}`, { method: "DELETE", headers: authHeaders() });
    toast("Пользователь удалён", "success");
    reload();
  }

  return (
    <Page title="Пользователи" kicker="Администрирование">
      <div className="mb-6 flex flex-wrap items-end gap-3 border border-border bg-bg p-[18px]">
        <div className="w-[180px]">
          <Field label="Логин">
            <input className={inputClass} value={login} onChange={(e) => setLogin(e.target.value)} />
          </Field>
        </div>
        <div className="w-[180px]">
          <Field label="Пароль">
            <input className={inputClass} type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </Field>
        </div>
        <div className="w-[160px]">
          <Field label="Роль">
            <select className={inputClass} value={role} onChange={(e) => setRole(e.target.value)}>
              <option value="viewer">viewer</option>
              <option value="admin">admin</option>
            </select>
          </Field>
        </div>
        <Button sm onClick={createUser} disabled={!login || !password}>
          Создать
        </Button>
      </div>
      {error && (
        <div role="alert" className="mb-4 border border-danger/40 bg-danger/[0.08] px-[13px] py-[10px] text-[12.5px] text-danger">
          {error}
        </div>
      )}

      {!loaded ? (
        <div className="border border-border">
          {[0, 1, 2].map((i) => (
            <div key={i} className="border-b border-border px-[18px] py-4">
              <Skeleton h={16} />
            </div>
          ))}
        </div>
      ) : users.length === 0 ? (
        <EmptyState title="Нет пользователей" desc="Создайте учётную запись, чтобы открыть доступ к анализу звонков." />
      ) : (
        <DataTable
          highlightCol={1}
          rows={users}
          cols={[
            { h: "Логин", nowrap: true, cell: (u) => <span className="mono text-[13px]">{u.login}</span> },
            {
              h: "Роль",
              nowrap: true,
              cell: (u) => (
                <span
                  className="mono border px-[9px] py-1 text-[10.5px] uppercase tracking-[.08em]"
                  style={{
                    borderColor: u.role === "admin" ? "var(--accent)" : "var(--border-2)",
                    color: u.role === "admin" ? "var(--accent)" : "var(--muted)",
                  }}
                >
                  {u.role}
                </span>
              ),
            },
            {
              h: "Статус",
              nowrap: true,
              cell: (u) => (
                <span
                  className="mono inline-flex items-center gap-[7px] text-[11px]"
                  style={{ color: u.is_active ? "var(--success)" : "var(--muted-2)" }}
                >
                  <span style={{ width: 7, height: 7, background: u.is_active ? "var(--success)" : "var(--muted-2)" }} />
                  {u.is_active ? "Активен" : "Неактивен"}
                </span>
              ),
            },
            {
              h: "",
              align: "right",
              nowrap: true,
              cell: (u) => (
                <span className="flex justify-end gap-3">
                  <button className="mono text-[11px] text-muted hover:text-accent" onClick={() => toggleActive(u)}>
                    {u.is_active ? "деактивировать" : "активировать"}
                  </button>
                  <button className="mono text-[11px] text-danger" onClick={() => setToDelete(u)}>
                    удалить
                  </button>
                </span>
              ),
            },
          ]}
        />
      )}

      <ConfirmDialog
        open={toDelete != null}
        title="Удалить пользователя?"
        body={`Доступ для «${toDelete?.login}» будет отозван немедленно. Это действие необратимо.`}
        confirmText="Удалить"
        danger
        onConfirm={() => toDelete && removeUser(toDelete)}
        onClose={() => setToDelete(null)}
      />
    </Page>
  );
}
