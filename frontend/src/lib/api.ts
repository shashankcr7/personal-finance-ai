"use client";

import { supabaseClient } from "./supabaseClient";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function authHeader(): Promise<HeadersInit> {
  const { data } = await supabaseClient.auth.getSession();
  const token = data.session?.access_token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function handleResponse(response: Response) {
  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;
    try {
      const body = await response.json();
      if (body?.detail) detail = body.detail;
    } catch {
      // response had no JSON body; keep the generic message
    }
    throw new ApiError(response.status, detail);
  }
  if (response.status === 204) return null;
  return response.json();
}

export async function apiGet(path: string, params?: Record<string, string | number>) {
  const url = new URL(`${API_BASE_URL}${path}`);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      url.searchParams.set(key, String(value));
    }
  }
  const headers = await authHeader();
  const response = await fetch(url.toString(), { headers });
  return handleResponse(response);
}

export async function apiPostJson(path: string, body: unknown) {
  const headers = await authHeader();
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { ...headers, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return handleResponse(response);
}

export async function apiPutJson(path: string, body: unknown) {
  const headers = await authHeader();
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "PUT",
    headers: { ...headers, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return handleResponse(response);
}

export async function apiDelete(path: string) {
  const headers = await authHeader();
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "DELETE",
    headers,
  });
  return handleResponse(response);
}

export async function apiPostForm(path: string, form: FormData) {
  const headers = await authHeader();
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers,
    body: form,
  });
  return handleResponse(response);
}
