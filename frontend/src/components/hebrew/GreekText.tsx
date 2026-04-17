interface GreekTextProps {
  text: string;
  className?: string;
}

export default function GreekText({ text, className = '' }: GreekTextProps) {
  return (
    <span lang="grc" className={className}>
      {text}
    </span>
  );
}
