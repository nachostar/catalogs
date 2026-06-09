import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { queryPlacements } from '@/lib/bigquery'

export async function GET(req: NextRequest) {
  const session = await getServerSession()
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const { searchParams } = req.nextUrl
  const dateFrom = searchParams.get('dateFrom') || '2026-06-01'
  const dateTo   = searchParams.get('dateTo')   || '2026-06-08'

  try {
    const data = await queryPlacements({ dateFrom, dateTo })
    const normalize = (rows: any[]) => rows.map(row => {
      const out: any = {}
      for (const [k, v] of Object.entries(row)) {
        out[k] = (v && typeof v === 'object' && 'value' in (v as any))
          ? (v as any).value : v
      }
      return out
    })
    return NextResponse.json(normalize(data as any[]))
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500 })
  }
}
