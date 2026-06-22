"use client";

import { useEffect, useState } from "react";

import { apiDelete, apiGet, apiPostJson, apiPutJson, ApiError } from "@/lib/api";
import { formatINR, formatPercent } from "@/lib/money";
import type { GoalProgress } from "@/lib/types";

type GoalFormState = {
  name: string;
  target_amount: string;
  target_date: string;
  priority: string;
  assumed_return: string;
  notes: string;
};

const EMPTY_FORM: GoalFormState = {
  name: "",
  target_amount: "",
  target_date: "",
  priority: "",
  assumed_return: "",
  notes: "",
};

function GoalModal({
  initial,
  onClose,
  onSaved,
}: {
  initial: { id: string; form: GoalFormState } | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [form, setForm] = useState<GoalFormState>(initial?.form ?? EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function update(field: keyof GoalFormState, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    const body = {
      name: form.name,
      target_amount: form.target_amount,
      target_date: form.target_date,
      priority: form.priority || null,
      assumed_return: form.assumed_return,
      notes: form.notes || null,
    };
    try {
      if (initial) {
        await apiPutJson(`/goals/${initial.id}`, body);
      } else {
        await apiPostJson("/goals", body);
      }
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save this goal.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 flex items-center justify-center bg-black/30">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm rounded-lg bg-white p-6 shadow-lg"
      >
        <h2 className="text-sm font-semibold text-gray-900">
          {initial ? "Edit goal" : "Add goal"}
        </h2>
        <div className="mt-4 space-y-3">
          <input
            type="text"
            required
            placeholder="Goal name"
            value={form.name}
            onChange={(e) => update("name", e.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          />
          <input
            type="text"
            required
            placeholder="Target amount (₹)"
            value={form.target_amount}
            onChange={(e) => update("target_amount", e.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          />
          <input
            type="date"
            required
            value={form.target_date}
            onChange={(e) => update("target_date", e.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          />
          <input
            type="text"
            placeholder="Priority (e.g. high)"
            value={form.priority}
            onChange={(e) => update("priority", e.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          />
          <input
            type="text"
            required
            placeholder="Assumed annual return (%)"
            value={form.assumed_return}
            onChange={(e) => update("assumed_return", e.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          />
          <textarea
            placeholder="Notes"
            value={form.notes}
            onChange={(e) => update("notes", e.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          />
          {error && <p className="text-sm text-red-600">{error}</p>}
        </div>
        <div className="mt-5 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-md px-3 py-2 text-sm font-medium text-gray-600"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={submitting}
            className="rounded-md bg-gray-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {submitting ? "Saving…" : "Save"}
          </button>
        </div>
      </form>
    </div>
  );
}

function GoalCard({
  goal,
  onEdit,
  onDeleted,
}: {
  goal: GoalProgress;
  onEdit: () => void;
  onDeleted: () => void;
}) {
  const [deleting, setDeleting] = useState(false);

  async function handleDelete() {
    if (!confirm(`Delete goal "${goal.name}"?`)) return;
    setDeleting(true);
    try {
      await apiDelete(`/goals/${goal.id}`);
      onDeleted();
    } finally {
      setDeleting(false);
    }
  }

  const percentFunded = Math.min(Number(goal.percent_funded), 100);

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-5">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-sm font-semibold text-gray-900">{goal.name}</h3>
          <p className="text-xs text-gray-500">
            {formatINR(goal.target_amount)} by {goal.target_date}
          </p>
        </div>
        <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700">
          {goal.assumed_return}% assumed
        </span>
      </div>

      <div className="mt-3 h-2 w-full rounded-full bg-gray-100">
        <div className="h-2 rounded-full bg-gray-900" style={{ width: `${percentFunded}%` }} />
      </div>
      <div className="mt-1 flex items-center justify-between text-xs text-gray-500">
        <span>{formatPercent(goal.percent_funded)} funded</span>
        <span
          className={`rounded-full px-2 py-0.5 font-medium ${
            goal.on_track ? "bg-green-100 text-green-700" : "bg-yellow-100 text-yellow-700"
          }`}
        >
          {goal.on_track ? "On track" : "Behind"}
        </span>
      </div>
      <p className="mt-2 text-xs text-gray-500">
        Projected {formatINR(goal.projected_value)} by target date — a projection, not a
        guarantee.
      </p>

      <div className="mt-3 flex gap-3 text-xs">
        <button onClick={onEdit} className="font-medium text-gray-700 hover:underline">
          Edit
        </button>
        <button
          onClick={handleDelete}
          disabled={deleting}
          className="font-medium text-red-600 hover:underline disabled:opacity-50"
        >
          Delete
        </button>
      </div>
    </div>
  );
}

export default function GoalsPage() {
  const [goals, setGoals] = useState<GoalProgress[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modalState, setModalState] = useState<
    { mode: "create" } | { mode: "edit"; goal: GoalProgress } | null
  >(null);

  async function loadGoals() {
    setLoading(true);
    setError(null);
    try {
      const data = await apiGet("/goals");
      setGoals(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load goals.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadGoals();
  }, []);

  function handleSaved() {
    setModalState(null);
    loadGoals();
  }

  return (
    <div className="max-w-4xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Goals</h1>
          <p className="mt-1 text-sm text-gray-500">
            Projections use your own return assumptions — shown and editable on each goal.
          </p>
        </div>
        <button
          onClick={() => setModalState({ mode: "create" })}
          className="rounded-md bg-gray-900 px-3 py-2 text-sm font-medium text-white"
        >
          + Add goal
        </button>
      </div>

      {loading && <p className="text-sm text-gray-500">Loading…</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}

      {!loading && !error && goals.length === 0 && (
        <p className="text-sm text-gray-500">No goals yet — add one to start tracking progress.</p>
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {goals.map((goal) => (
          <GoalCard
            key={goal.id}
            goal={goal}
            onEdit={() => setModalState({ mode: "edit", goal })}
            onDeleted={loadGoals}
          />
        ))}
      </div>

      {modalState?.mode === "create" && (
        <GoalModal initial={null} onClose={() => setModalState(null)} onSaved={handleSaved} />
      )}
      {modalState?.mode === "edit" && (
        <GoalModal
          initial={{
            id: modalState.goal.id,
            form: {
              name: modalState.goal.name,
              target_amount: modalState.goal.target_amount,
              target_date: modalState.goal.target_date,
              priority: modalState.goal.priority ?? "",
              assumed_return: modalState.goal.assumed_return,
              notes: modalState.goal.notes ?? "",
            },
          }}
          onClose={() => setModalState(null)}
          onSaved={handleSaved}
        />
      )}
    </div>
  );
}
