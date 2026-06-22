"use client";

import { useEffect, useState } from "react";

import { apiGet, apiPostForm, apiPostJson, ApiError } from "@/lib/api";
import type { RecentUpload } from "@/lib/types";

function StatusBadge({ status }: { status: RecentUpload["status"] }) {
  const styles: Record<RecentUpload["status"], string> = {
    success: "bg-green-100 text-green-700",
    error: "bg-red-100 text-red-700",
    parsing: "bg-yellow-100 text-yellow-700",
    pending: "bg-gray-100 text-gray-600",
  };
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${styles[status]}`}>
      {status}
    </span>
  );
}

function CasUploadCard({ onDone }: { onDone: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!file) return;
    setSubmitting(true);
    setMessage(null);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("password", password);
      const result = await apiPostForm("/upload/cas", form);
      setMessage(`Parsed ${result.holdings_count} holdings.`);
      setFile(null);
      setPassword("");
      onDone();
    } catch (err) {
      setMessage(err instanceof ApiError ? err.message : "Could not parse this file.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="rounded-lg border border-gray-200 bg-white p-5">
      <h3 className="text-sm font-semibold text-gray-900">CAS PDF</h3>
      <p className="mt-1 text-xs text-gray-500">Consolidated Account Statement (NSDL/CDSL)</p>
      <div className="mt-4 space-y-3">
        <input
          type="file"
          accept="application/pdf"
          required
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="block w-full text-sm"
        />
        <input
          type="password"
          required
          placeholder="CAS password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-md bg-gray-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {submitting ? "Parsing…" : "Upload CAS"}
        </button>
        {message && <p className="text-xs text-gray-600">{message}</p>}
      </div>
    </form>
  );
}

function BankUploadCard({ onDone }: { onDone: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [bank, setBank] = useState("icici");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!file) return;
    setSubmitting(true);
    setMessage(null);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("bank", bank);
      const result = await apiPostForm("/upload/bank", form);
      setMessage(
        `Inserted ${result.transactions_inserted} transactions (` +
          `${result.categorized_by_rule} by rule, ${result.categorized_by_ai} by AI, ` +
          `${result.uncategorized} uncategorized).`
      );
      setFile(null);
      onDone();
    } catch (err) {
      setMessage(err instanceof ApiError ? err.message : "Could not parse this file.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="rounded-lg border border-gray-200 bg-white p-5">
      <h3 className="text-sm font-semibold text-gray-900">Bank CSV / Excel</h3>
      <p className="mt-1 text-xs text-gray-500">ICICI · Kotak</p>
      <div className="mt-4 space-y-3">
        <select
          value={bank}
          onChange={(e) => setBank(e.target.value)}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
        >
          <option value="icici">ICICI</option>
          <option value="kotak">Kotak</option>
        </select>
        <input
          type="file"
          accept=".csv,.xls,.xlsx"
          required
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="block w-full text-sm"
        />
        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-md bg-gray-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {submitting ? "Parsing…" : "Upload statement"}
        </button>
        {message && <p className="text-xs text-gray-600">{message}</p>}
      </div>
    </form>
  );
}

function LoanForm() {
  const [form, setForm] = useState({
    institution_name: "SBI",
    original_principal: "",
    principal_outstanding: "",
    interest_rate: "",
    emi_amount: "",
    tenure_months_left: "",
    as_of_date: new Date().toISOString().slice(0, 10),
  });
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  function update(field: keyof typeof form, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setMessage(null);
    try {
      await apiPostJson("/loan", {
        ...form,
        tenure_months_left: Number(form.tenure_months_left),
      });
      setMessage("Loan saved.");
    } catch (err) {
      setMessage(err instanceof ApiError ? err.message : "Could not save this loan.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="rounded-lg border border-gray-200 bg-white p-5">
      <h3 className="text-sm font-semibold text-gray-900">Loan — manual entry</h3>
      <p className="mt-1 text-xs text-gray-500">e.g. SBI education/home loan</p>
      <div className="mt-4 space-y-3">
        <input
          type="text"
          required
          placeholder="Institution (e.g. SBI)"
          value={form.institution_name}
          onChange={(e) => update("institution_name", e.target.value)}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
        />
        <input
          type="text"
          required
          placeholder="Original principal (₹)"
          value={form.original_principal}
          onChange={(e) => update("original_principal", e.target.value)}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
        />
        <input
          type="text"
          required
          placeholder="Outstanding principal (₹)"
          value={form.principal_outstanding}
          onChange={(e) => update("principal_outstanding", e.target.value)}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
        />
        <input
          type="text"
          required
          placeholder="Interest rate (%)"
          value={form.interest_rate}
          onChange={(e) => update("interest_rate", e.target.value)}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
        />
        <input
          type="text"
          required
          placeholder="EMI amount (₹)"
          value={form.emi_amount}
          onChange={(e) => update("emi_amount", e.target.value)}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
        />
        <input
          type="number"
          required
          placeholder="Months left"
          value={form.tenure_months_left}
          onChange={(e) => update("tenure_months_left", e.target.value)}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
        />
        <input
          type="date"
          required
          value={form.as_of_date}
          onChange={(e) => update("as_of_date", e.target.value)}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-md bg-gray-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {submitting ? "Saving…" : "Save loan"}
        </button>
        {message && <p className="text-xs text-gray-600">{message}</p>}
      </div>
    </form>
  );
}

export default function UploadPage() {
  const [uploads, setUploads] = useState<RecentUpload[]>([]);
  const [loading, setLoading] = useState(true);

  async function loadUploads() {
    try {
      const data = await apiGet("/uploads");
      setUploads(data);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadUploads();
  }, []);

  return (
    <div className="max-w-4xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-gray-900">Upload</h1>
        <p className="mt-1 text-sm text-gray-500">
          Raw statements are parsed, then deleted. Only structured data is stored.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <CasUploadCard onDone={loadUploads} />
        <BankUploadCard onDone={loadUploads} />
        <LoanForm />
      </div>

      <div className="rounded-lg border border-gray-200 bg-white p-5">
        <h3 className="text-sm font-semibold text-gray-900">Recent uploads</h3>
        {loading ? (
          <p className="mt-3 text-sm text-gray-500">Loading…</p>
        ) : uploads.length === 0 ? (
          <p className="mt-3 text-sm text-gray-500">No uploads yet.</p>
        ) : (
          <table className="mt-3 w-full text-left text-sm">
            <thead>
              <tr className="text-xs text-gray-500">
                <th className="pb-2">Type</th>
                <th className="pb-2">File</th>
                <th className="pb-2">As of</th>
                <th className="pb-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {uploads.map((upload) => (
                <tr key={upload.id} className="border-t border-gray-100">
                  <td className="py-2 text-gray-700">{upload.source_type}</td>
                  <td className="py-2 text-gray-700">{upload.original_filename ?? "—"}</td>
                  <td className="py-2 text-gray-700">{upload.as_of_date ?? "—"}</td>
                  <td className="py-2">
                    <StatusBadge status={upload.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
