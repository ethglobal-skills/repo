import { NextRequest } from 'next/server'
import { supabase } from '@/lib/supabase'

// GET /api/sponsors
// Returns all sponsor names, optionally filtered by keyword.
// Use to find the exact sponsor name to pass to /api/prizes or /api/projects.
// - keyword: partial name match (optional)
export async function GET(req: NextRequest) {
  const { searchParams } = req.nextUrl
  const keyword = searchParams.get('keyword')

  let query = supabase
    .from('sponsors')
    .select('name')
    .order('name', { ascending: true })

  if (keyword) query = query.ilike('name', `%${keyword}%`)

  const { data, error } = await query
  if (error) return Response.json({ error: error.message }, { status: 500 })

  return Response.json({ sponsors: data?.map((s: any) => s.name) ?? [] })
}
