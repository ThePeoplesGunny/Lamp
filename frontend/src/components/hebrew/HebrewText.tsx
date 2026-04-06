interface HebrewTextProps {
  text: string;
  className?: string;
}

export default function HebrewText({ text, className = '' }: HebrewTextProps) {
  return (
    <span
      dir="rtl"
      lang="he"
      style={{ fontFamily: "var(--font-hebrew)" }}
      className={className}
    >
      {text}
    </span>
  );
}
