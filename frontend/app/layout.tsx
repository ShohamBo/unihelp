import type { Metadata } from 'next'
import { Heebo } from 'next/font/google'
import './globals.css'
import Header from '@/components/Header'
import Footer from '@/components/Footer'

const heebo = Heebo({
  subsets: ['hebrew', 'latin'],
  variable: '--font-heebo',
  display: 'swap',
})

export const metadata: Metadata = {
  title: {
    default: 'מסלול — השוואת תארים אקדמיים בישראל',
    template: '%s | מסלול',
  },
  description:
    'מצא את התואר שמתאים לך. השוואה אמיתית בין תארים ראשונים בישראל — ביקורות סטודנטים, סף קבלה, ותוכן לימודים.',
  openGraph: {
    locale: 'he_IL',
    type: 'website',
  },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="he" dir="rtl" className={heebo.variable}>
      <body className="font-heebo bg-gray-50 text-gray-900 antialiased min-h-screen flex flex-col">
        <Header />
        <main className="flex-1">{children}</main>
        <Footer />
      </body>
    </html>
  )
}
