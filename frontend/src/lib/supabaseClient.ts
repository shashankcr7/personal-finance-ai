"use client";

import { createClient } from "@supabase/supabase-js";

// NEXT_PUBLIC_ prefixed on purpose: this client runs in the browser to drive
// the interactive login/MFA flow. The anon key is safe to expose (paired with
// RLS) - this is not the service-role client used server-side in db.py.
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error("Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY env var");
}

export const supabaseClient = createClient(supabaseUrl, supabaseAnonKey);
