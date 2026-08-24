export default function ErrorBanner({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <div
      style={{
        padding: "12px 16px",
        background: "rgba(226,84,74,.06)",
        border: "1px solid rgba(226,84,74,.2)",
        borderRadius: "var(--radius-sm)" as unknown as string,
        color: "#a23c34",
        fontSize: 13,
        lineHeight: 1.5,
      }}
      role="alert"
    >
      {message}
    </div>
  );
}
