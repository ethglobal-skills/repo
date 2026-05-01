import { NextRequest } from 'next/server'
import { supabase } from '@/lib/supabase'

// GET /api/events
// Returns all hackathon events, sorted by start_date descending.
export async function GET(_req: NextRequest) {
  const { data, error } = await supabase
    .from('events')
    .select('name, url, start_date, end_date')
    .order('start_date', { ascending: false })

  if (error) return Response.json({ error: error.message }, { status: 500 })
  return Response.json({ events: data })
}
