type ProgressProps = {
  value: number;
  tone?: "gold" | "purple" | "blue";
};

const toneClasses = {
  gold: "from-gold to-[#ffe49a]",
  purple: "from-[#a882ff] to-[#d7c6ff]",
  blue: "from-[#72b4ff] to-[#d0ebff]",
};

export function Progress({ value, tone = "gold" }: ProgressProps) {
  const width = Math.max(0, Math.min(100, value));
  return (
    <div className="h-2.5 w-full overflow-hidden rounded-full bg-white/10">
      <div
        className={`h-full rounded-full bg-gradient-to-r ${toneClasses[tone]} transition-[width] duration-500`}
        style={{ width: `${width}%` }}
      />
    </div>
  );
}
