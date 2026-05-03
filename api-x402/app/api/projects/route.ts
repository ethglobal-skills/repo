import { NextRequest } from 'next/server'
import { supabase } from '@/lib/supabase'

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}))
  const event: string | null = body.event ?? null
  const keyword: string | null = body.keyword ?? null
  const sponsor: string | null = body.sponsor ?? null
  const prize: string | null = body.prize ?? null
  const pool: boolean = body.pool === true
  const limit: number = Math.min(body.limit ?? 30, 100)
  const include = new Set<string>(
    Array.isArray(body.include)
      ? body.include
      : (body.include ?? '').split(',').map((s: string) => s.trim()).filter(Boolean)
  )

  const selectFields = ['title', 'url', 'tagline', 'github', 'live_demo', 'event_id', 'events(name)']
  if (include.has('description')) selectFields.push('description')
  if (include.has('how_its_made')) selectFields.push('how_its_made')

  let eventId: number | null = null
  if (event) {
    const { data, error } = await supabase
      .from('events')
      .select('id')
      .ilike('name', event)
      .limit(1)
    if (error) return Response.json({ error: error.message }, { status: 500 })
    if (!data?.length) return Response.json({ projects: [] })
    eventId = data[0].id
  }

  let prizeMap: Map<number, string[]> | null = null
  if (prize || sponsor) {
    let sponsorId: number | null = null
    if (sponsor) {
      const { data, error } = await supabase
        .from('sponsors')
        .select('id')
        .ilike('name', sponsor)
        .limit(1)
      if (error) return Response.json({ error: error.message }, { status: 500 })
      if (!data?.length) return Response.json({ projects: [] })
      sponsorId = data[0].id
    }

    let prizeQuery = supabase.from('prizes').select('id')
    if (eventId) prizeQuery = prizeQuery.eq('event_id', eventId)
    if (sponsorId) prizeQuery = prizeQuery.eq('sponsor_id', sponsorId)
    if (prize) prizeQuery = prizeQuery.ilike('title', `%${prize}%`)
    if (sponsor && !prize && !pool) {
      prizeQuery = prizeQuery
        .not('title', 'ilike', '%pool prize%')
        .not('title', 'ilike', '%prize pool%')
    }

    const { data: prizeData, error: prizeErr } = await prizeQuery
    if (prizeErr) return Response.json({ error: prizeErr.message }, { status: 500 })
    if (!prizeData?.length) return Response.json({ projects: [] })

    const prizeIds = prizeData.map((p: any) => p.id)
    const { data: ppData, error: ppErr } = await supabase
      .from('project_prizes')
      .select('project_id, prize_id, prizes(title)')
      .in('prize_id', prizeIds)
    if (ppErr) return Response.json({ error: ppErr.message }, { status: 500 })

    prizeMap = new Map<number, string[]>()
    for (const row of ppData ?? []) {
      const existing = prizeMap.get(row.project_id) ?? []
      const title = ((row.prizes as any)?.title ?? '').replace(/([a-z])([A-Z])/g, '$1 $2')
      existing.push(title)
      prizeMap.set(row.project_id, existing)
    }
    if (!prizeMap.size) return Response.json({ projects: [] })
  }

  let query = supabase
    .from('projects')
    .select(['id', ...selectFields].join(', '))
    .limit(limit)

  if (eventId) query = query.eq('event_id', eventId)
  if (prizeMap) query = query.in('id', [...prizeMap.keys()])
  if (keyword) {
    query = query.or(
      `title.ilike.%${keyword}%,tagline.ilike.%${keyword}%,description.ilike.%${keyword}%,how_its_made.ilike.%${keyword}%`
    )
  }

  const { data, error } = await query
  if (error) return Response.json({ error: error.message }, { status: 500 })

  const projects = (data ?? []).map(({ id, event_id, events, ...p }: any) => ({
    ...p,
    hackathon: events?.name ?? null,
    ...(prizeMap ? { prizes_won: prizeMap.get(id) ?? [] } : {}),
  }))

  return Response.json({ projects })
}
