import GoogleProvider from 'next-auth/providers/google'
import type { NextAuthOptions } from 'next-auth'

export const authOptions: NextAuthOptions = {
  providers: [
    GoogleProvider({
      clientId:     process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
      authorization: {
        params: {
          scope: [
            'openid',
            'email',
            'profile',
            'https://www.googleapis.com/auth/analytics.readonly',
          ].join(' '),
          access_type: 'offline',
          prompt: 'consent',
        },
      },
    }),
  ],
  pages: { signIn: '/login' },
  callbacks: {
    async jwt({ token, account }) {
      if (account) {
        token.access_token  = account.access_token
        token.refresh_token = account.refresh_token
      }
      return token
    },
    async session({ session, token }) {
      (session as any).access_token = token.access_token
      return session
    },
  },
}
