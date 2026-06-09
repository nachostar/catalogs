/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: [
      { protocol: 'https', hostname: 'pfmutlcxjnmjlwhozaur.supabase.co' },
      { protocol: 'https', hostname: 'storage.googleapis.com' },
      { protocol: 'https', hostname: 'bucketeer-22ff8c13-22dd-43b9-bdd1-0e675bfd5301.s3.amazonaws.com' },
      { protocol: 'https', hostname: 'cdn.shopify.com' },
    ],
  },
}
module.exports = nextConfig
