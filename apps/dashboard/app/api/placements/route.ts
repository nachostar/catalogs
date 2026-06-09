import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { queryPlacements, queryPlacementAges, queryPlacementDimensions } from '@/lib/bigquery'

export async function GET(req: NextRequest) {
  const session = await getServerSession(authOptions)
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const p          = req.nextUrl.searchParams
  const type       = p.get('type') || 'data'
  const dateFrom   = p.get('dateFrom') || '2026-06-01'
  const dateTo     = p.get('dateTo')   || '2026-06-08'
  const age        = p.get('age')      || undefined
  const campaign   = p.get('campaign') || undefined
  const adset      = p.get('adset')    || undefined
  const ad         = p.get('ad')       || undefined

  const normalize = (rows: any[]) => rows.map(row => {
    const out: any = {}
    for (const [k, v] of Object.entries(row))
      out[k] = (v && typeof v === 'object' && 'value' in (v as any)) ? (v as any).value : v
    return out
  })

  try {
    if (type === 'ages')       return NextResponse.json(await queryPlacementAges())
    if (type === 'dimensions') {
      const dims = await queryPlacementDimensions({ dateFrom, dateTo })
      return NextResponse.json(dims)
    }
    const data = await queryPlacements({ dateFrom, dateTo, age, campaign, adset, ad })
    return NextResponse.json({
      platforms: normalize(data.platforms as any[]),
      ages:      normalize(data.ages as any[]),
    })
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500 })
  }
}
