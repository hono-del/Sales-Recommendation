import Link from "next/link";

type Props = {
  href?: string;
  onClick?: () => void;
  children: React.ReactNode;
  disabled?: boolean;
};

const buttonStyle: React.CSSProperties = {
  display: "inline-flex",
  minWidth: "200px",
  height: "48px",
  alignItems: "center",
  justifyContent: "center",
  padding: "0 32px",
  borderRadius: "6px",
  border: "none",
  cursor: "pointer",
  fontSize: "16px",
  fontWeight: 500,
  color: "#ffffff",
  backgroundColor: "var(--color-navy, #1a365d)",
  transition: "background-color 0.2s, opacity 0.2s",
};

export function PrimaryButton({ href, onClick, children, disabled }: Props) {
  if (href && !disabled) {
    return (
      <Link
        href={href}
        style={{
          ...buttonStyle,
          textDecoration: "none",
        }}
      >
        {children}
      </Link>
    );
  }

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      style={{
        ...buttonStyle,
        opacity: disabled ? 0.6 : 1,
        cursor: disabled ? "wait" : "pointer",
      }}
      onMouseEnter={(e) => {
        if (!disabled) {
          e.currentTarget.style.backgroundColor = "var(--color-navy-light, #2d5a8e)";
        }
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.backgroundColor = "var(--color-navy, #1a365d)";
      }}
    >
      {children}
    </button>
  );
}
