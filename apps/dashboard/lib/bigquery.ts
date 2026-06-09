import { BigQuery } from '@google-cloud/bigquery'

const PROJECT = process.env.GCP_PROJECT || 'quetri'
const DATASET = process.env.GCP_DATASET || 'meta_ads'

function getClient() {
  const saJson = process.env.GOOGLE_SERVICE_ACCOUNT_JSON
  if (saJson) {
    const credentials = JSON.parse(saJson)
    return new BigQuery({ projectId: PROJECT, credentials })
  }
  return new BigQuery({ projectId: PROJECT })
}

export async function queryMetrics(params: {
  dateFrom: string
  dateTo: string
  campaign?: string
  productId?: string
}) {
  const client = getClient()
  const { dateFrom, dateTo, campaign, productId } = params

  const filters: string[] = [`date BETWEEN '${dateFrom}' AND '${dateTo}'`]
  if (campaign) filters.push(`campaign_name = '${campaign.replace(/'/g, "''")}'`)
  if (productId) filters.push(`product_id = '${productId}'`)
  const where = filters.join(' AND ')

  // Productos: agrupados por product_id (sin duplicados por anuncio)
  const productsQuery = `
    SELECT
      product_id,
      MAX(product_name)    AS product_name,
      MAX(product_url)     AS product_url,
      SUM(impressions)     AS impressions,
      SUM(reach)           AS reach,
      SUM(clicks)          AS clicks,
      SAFE_DIVIDE(SUM(clicks), NULLIF(SUM(impressions),0)) * 100 AS ctr,
      SUM(spend)           AS spend,
      SAFE_DIVIDE(SUM(spend), NULLIF(SUM(clicks),0)) AS cpc,
      SUM(view_content)    AS view_content,
      SUM(add_to_cart)     AS add_to_cart,
      SUM(purchase)        AS purchase,
      SUM(purchase_value)  AS purchase_value,
      SAFE_DIVIDE(SUM(purchase_value), NULLIF(SUM(spend), 0)) AS roas
    FROM \`${PROJECT}.${DATASET}.daily_metrics\`
    WHERE ${where} AND product_id IS NOT NULL
    GROUP BY product_id
    ORDER BY spend DESC
  `

  // Anuncios: agrupados por ad (sin product breakdown)
  const adsQuery = `
    SELECT
      campaign_name,
      adset_name,
      ad_name,
      destination_url,
      MAX(thumbnail_url) AS thumbnail_url,
      SUM(impressions)     AS impressions,
      SUM(reach)           AS reach,
      SUM(clicks)          AS clicks,
      SAFE_DIVIDE(SUM(clicks), NULLIF(SUM(impressions),0)) * 100 AS ctr,
      SUM(spend)           AS spend,
      SAFE_DIVIDE(SUM(spend), NULLIF(SUM(clicks),0)) AS cpc,
      SUM(view_content)    AS view_content,
      SUM(add_to_cart)     AS add_to_cart,
      SUM(purchase)        AS purchase,
      SUM(purchase_value)  AS purchase_value,
      SAFE_DIVIDE(SUM(purchase_value), NULLIF(SUM(spend), 0)) AS roas
    FROM \`${PROJECT}.${DATASET}.daily_metrics\`
    WHERE ${where} AND product_id IS NULL
    GROUP BY 1,2,3,4
    ORDER BY SUM(spend) DESC
  `

  const [[products], [ads]] = await Promise.all([
    client.query(productsQuery),
    client.query(adsQuery),
  ])

  return { products, ads }
}

export async function queryTrend(params: {
  dateFrom: string
  dateTo: string
  campaign?: string
}) {
  const client = getClient()
  const { dateFrom, dateTo, campaign } = params
  const filters: string[] = [`date BETWEEN '${dateFrom}' AND '${dateTo}'`]
  if (campaign) filters.push(`campaign_name = '${campaign.replace(/'/g, "''")}'`)

  const query = `
    SELECT
      date,
      SUM(spend)          AS spend,
      SUM(impressions)    AS impressions,
      SUM(clicks)         AS clicks,
      SUM(purchase)       AS purchase,
      SUM(purchase_value) AS purchase_value,
      SAFE_DIVIDE(SUM(purchase_value), NULLIF(SUM(spend), 0)) AS roas
    FROM \`${PROJECT}.${DATASET}.daily_metrics\`
    WHERE ${filters.join(' AND ')}
    GROUP BY date
    ORDER BY date
  `
  const [rows] = await client.query(query)
  return rows
}

export async function queryCatalog(params: { search?: string }) {
  const client = getClient()
  const having = params.search
    ? `HAVING LOWER(MAX(title)) LIKE '%${params.search.toLowerCase().replace(/'/g, "''")}%'`
    : ''
  const query = `
    SELECT
      family_id,
      MAX(title)        AS title,
      MAX(brand)        AS brand,
      MAX(category)     AS category,
      AVG(price)        AS price,
      MAX(availability) AS availability,
      MAX(link)         AS link,
      MAX(image_link)   AS image_link
    FROM \`${PROJECT}.${DATASET}.hereneo_catalog\`
    GROUP BY family_id
    ${having}
    ORDER BY title
    LIMIT 2000
  `
  const [rows] = await client.query(query)
  return rows
}

export async function queryPlacements(params: {
  dateFrom: string; dateTo: string; age?: string
}) {
  const client = getClient()
  const { dateFrom, dateTo, age } = params
  const dateFilter = `date BETWEEN '${dateFrom}' AND '${dateTo}'`

  // Por plataforma
  const platformQuery = `
    SELECT platform, '' AS age,
      SUM(impressions) AS impressions, SUM(reach) AS reach, SUM(clicks) AS clicks,
      SAFE_DIVIDE(SUM(clicks), NULLIF(SUM(impressions),0)) * 100 AS ctr,
      SUM(spend) AS spend, SUM(view_content) AS view_content,
      SUM(add_to_cart) AS add_to_cart, SUM(purchase) AS purchase,
      SUM(purchase_value) AS purchase_value,
      SAFE_DIVIDE(SUM(purchase_value), NULLIF(SUM(spend),0)) AS roas
    FROM \`${PROJECT}.${DATASET}.placement_metrics\`
    WHERE ${dateFilter} AND breakdown_type = 'platform'
    GROUP BY platform ORDER BY spend DESC
  `

  // Por edad (con filtro opcional)
  const ageWhere = age ? `AND age = '${age}'` : ''
  const ageQuery = `
    SELECT '' AS platform, age,
      SUM(impressions) AS impressions, SUM(reach) AS reach, SUM(clicks) AS clicks,
      SAFE_DIVIDE(SUM(clicks), NULLIF(SUM(impressions),0)) * 100 AS ctr,
      SUM(spend) AS spend, SUM(view_content) AS view_content,
      SUM(add_to_cart) AS add_to_cart, SUM(purchase) AS purchase,
      SUM(purchase_value) AS purchase_value,
      SAFE_DIVIDE(SUM(purchase_value), NULLIF(SUM(spend),0)) AS roas
    FROM \`${PROJECT}.${DATASET}.placement_metrics\`
    WHERE ${dateFilter} AND breakdown_type = 'age' ${ageWhere}
    GROUP BY age ORDER BY spend DESC
  `

  const [[platforms], [ages]] = await Promise.all([
    client.query(platformQuery),
    client.query(ageQuery),
  ])
  return { platforms, ages }
}

export async function queryPlacementAges() {
  const client = getClient()
  const [rows] = await client.query(`
    SELECT DISTINCT age FROM \`${PROJECT}.${DATASET}.placement_metrics\`
    WHERE age IS NOT NULL AND age != '' AND breakdown_type = 'age'
    ORDER BY age
  `)
  return rows.map((r: any) => r.age)
}

export async function queryCampaigns() {
  const client = getClient()
  const [rows] = await client.query(`
    SELECT DISTINCT campaign_name
    FROM \`${PROJECT}.${DATASET}.daily_metrics\`
    WHERE campaign_name IS NOT NULL
    ORDER BY campaign_name
  `)
  return rows.map((r: any) => r.campaign_name)
}
