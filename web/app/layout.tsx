export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          minHeight: "100vh",
          fontFamily:
            "ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif",
          background: "#0f1419",
          color: "#f4efe6",
        }}
      >
        <header
          style={{
            display: "flex",
            gap: 18,
            alignItems: "baseline",
            padding: "20px 24px",
            borderBottom: "1px solid #2a333d",
          }}
        >
          <a href="/" style={{ color: "#c4a574", textDecoration: "none", letterSpacing: "0.16em", fontSize: 12 }}>
            LEADSY FLOCK
          </a>
          <a href="/" style={{ color: "#f4efe6", textDecoration: "none", fontSize: 14 }}>
            Chat
          </a>
          <a href="/campaigns" style={{ color: "#f4efe6", textDecoration: "none", fontSize: 14 }}>
            Receipts
          </a>
        </header>
        {children}
      </body>
    </html>
  );
}
