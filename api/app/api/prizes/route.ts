import { NextRequest } from 'next/server'
import { supabase } from '@/lib/supabase'

const SUFFIX_RE = /\s*(\d+(?:st|nd|rd|th)\s+(?:place|prize)|runner\s*up|honorable\s+mention)\s*$/i

function baseTitle(title: string) {
  return title.replace(SUFFIX_RE, '').trim()
}

// GET /api/prizes
// Returns bounties grouped by sponsor, with docs nested under each prize.
// - event: exact event name, case-insensitive (required if sponsor not provided)
// - sponsor: exact sponsor name, case-insensitive (required if event not provided)
//   When sponsor-only, returns most recent 10 unique prizes across all events.
export async function GET(req: NextRequest) {
  const { searchParams } = req.nextUrl
  const event = searchParams.get('event')
  const sponsor = searchParams.get('sponsor')

  if (!event && !sponsor) {
    return Response.json({ error: 'at least one of event or sponsor is required' }, { status: 400 })
  }

  let eventId: number | null = null
  if (event) {
    const { data, error } = await supabase
      .from('events')
      .select('id')
      .ilike('name', event)
      .limit(1)
    if (error) return Response.json({ error: error.message }, { status: 500 })
    if (!data?.length) return Response.json({ results: [] })
    eventId = data[0].id
  }

  let sponsorId: number | null = null
  if (sponsor) {
    const { data, error } = await supabase
      .from('sponsors')
      .select('id')
      .ilike('name', sponsor)
      .limit(1)
    if (error) return Response.json({ error: error.message }, { status: 500 })
    if (!data?.length) return Response.json({ results: [] })
    sponsorId = data[0].id
  }

  // Fetch prizes — join events for start_date so we can sort sponsor-only queries
  let query = supabase
    .from('prizes')
    .select('title, description, qualifications, sponsor_id, sponsors(id, name, about), events(start_date)')

  if (eventId) query = query.eq('event_id', eventId)
  if (sponsorId) query = query.eq('sponsor_id', sponsorId)
  if (!eventId && sponsorId) query = query.order('events(start_date)', { ascending: false })

  const { data, error } = await query
  if (error) return Response.json({ error: error.message }, { status: 500 })

  // Deduplicate: prefer entry with description; for sponsor-only cap at 10
  const best = new Map<string, any>()
  for (const p of data ?? []) {
    const sponsorName = (p.sponsors as any)?.name
    const key = `${sponsorName}::${baseTitle(p.title).toLowerCase()}`
    const existing = best.get(key)
    if (!existing || (!existing.description && p.description)) {
      best.set(key, { ...p, title: baseTitle(p.title) })
    }
  }

  let deduped = [...best.values()]
  if (!eventId && sponsorId) deduped = deduped.slice(0, 10)

  const uniqueSponsorIds = [...new Set(deduped.map((p: any) => p.sponsor_id))]
  let docsQuery = supabase
    .from('sponsor_docs')
    .select('sponsor_id, name, url')
    .in('sponsor_id', uniqueSponsorIds)
  if (eventId) docsQuery = docsQuery.eq('event_id', eventId)
  const { data: docsData } = await docsQuery

  const docsBySponsor = new Map<number, { name: string; url: string }[]>()
  for (const d of docsData ?? []) {
    const existing = docsBySponsor.get(d.sponsor_id) ?? []
    if (!existing.some(e => e.name === d.name)) existing.push({ name: d.name, url: d.url })
    docsBySponsor.set(d.sponsor_id, existing)
  }

  const bySponsor = new Map<number, any>()
  for (const p of deduped) {
    const sid = p.sponsor_id
    const sponsorInfo = p.sponsors as any
    if (!bySponsor.has(sid)) {
      bySponsor.set(sid, {
        name: sponsorInfo?.name ?? null,
        about: sponsorInfo?.about ?? null,
        docs: docsBySponsor.get(sid) ?? [],
        prizes: [],
      })
    }
    bySponsor.get(sid).prizes.push({
      title: p.title,
      description: p.description ?? null,
      qualifications: p.qualifications ?? null,
    })
  }

  return Response.json({ results: [...bySponsor.values()] })
}
