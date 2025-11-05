import './globals.css';

export const metadata = { title: 'Bot Trader', description: 'Trading SaaS UI' };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
