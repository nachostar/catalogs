import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { queryCatalog } from '@/lib/bigquery'

export async function GET(req: NextRequest) {
  const session = await getServerSession()
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const search = req.nextUrl.searchParams.get('search') || undefined
  try {
    const data = await queryCatalog({ search })
    return NextResponse.json(data)
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500 })
  }
}
