import { createClient } from "@supabase/supabase-js";

// No NEXT_PUBLIC_ prefix on purpose: this client is for server components,
// route handlers, and server actions only, never imported into client components.
const supabaseUrl = process.env.SUPABASE_URL;
const supabaseAnonKey = process.env.SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error("Missing SUPABASE_URL or SUPABASE_ANON_KEY env var");
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
