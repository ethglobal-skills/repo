import { NextRequest } from 'next/server'
import { supabase } from '@/lib/supabase'

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}))
  const keyword: string | null = body.keyword ?? null

  let query = supabase
    .from('sponsors')
    .select('name')
    .order('name', { ascending: true })

  if (keyword) query = query.ilike('name', `%${keyword}%`)

  const { data, error } = await query
  if (error) return Response.json({ error: error.message }, { status: 500 })

  return Response.json({ sponsors: data?.map((s: any) => s.name) ?? [] })
}
