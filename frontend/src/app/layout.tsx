export const metadata = { title: 'Bot Trader', description: 'Trading SaaS UI' };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{ fontFamily: 'ui-sans-serif, system-ui', margin: 0 }}>{children}</body>
    </html>
  );
}
