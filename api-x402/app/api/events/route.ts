import { supabase } from '@/lib/supabase'

export async function GET() {
  const { data, error } = await supabase
    .from('events')
    .select('name, url, start_date, end_date')
    .order('start_date', { ascending: false })

  if (error) return Response.json({ error: error.message }, { status: 500 })
  return Response.json({ events: data })
}
