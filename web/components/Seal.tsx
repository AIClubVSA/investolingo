"use client";

/**
 * Achievement mark. Rather than a badge with a glow, this is an engraved seal:
 * a ruled ring, a struck monogram, and a stamped state. Locked seals are
 * drawn in outline so the shape is legible before it is earned.
 */

const MONOGRAMS: Record<string, string> = {
  first_trade: "I",
  diversified: "III",
  survivor: "XXX",
};

/** Server and client must agree bit-for-bit, so trig results are rounded. */
const round = (n: number) => Math.round(n * 1000) / 1000;

export function Seal({
  id,
  earned,
  size = 64,
  animate = false,
}: {
  id: string;
  earned: boolean;
  size?: number;
  animate?: boolean;
}) {
  const monogram = MONOGRAMS[id] ?? "·";
  const stroke = earned ? "var(--brass)" : "var(--line-strong)";
  const text = earned ? "var(--brass-bright)" : "var(--text-faint)";

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      className={animate && earned ? "seal-in" : undefined}
      role="img"
      aria-label={earned ? "Awarded" : "Not yet awarded"}
    >
      <circle
        cx="32"
        cy="32"
        r="29"
        fill="none"
        stroke={stroke}
        strokeWidth="1"
        strokeDasharray={earned ? undefined : "3 3"}
      />
      <circle cx="32" cy="32" r="24" fill="none" stroke={stroke} strokeWidth="2" />

      {/* Twelve struck ticks, as on a ledger seal */}
      {Array.from({ length: 12 }).map((_, i) => {
        const angle = (i * 30 * Math.PI) / 180;
        return (
          <line
            key={i}
            x1={round(32 + Math.cos(angle) * 25.5)}
            y1={round(32 + Math.sin(angle) * 25.5)}
            x2={round(32 + Math.cos(angle) * 28)}
            y2={round(32 + Math.sin(angle) * 28)}
            stroke={stroke}
            strokeWidth="1"
          />
        );
      })}

      <text
        x="32"
        y="32"
        textAnchor="middle"
        dominantBaseline="central"
        fill={text}
        fontFamily="var(--font-display)"
        fontSize="16"
        fontWeight="600"
        letterSpacing="0.06em"
      >
        {monogram}
      </text>
    </svg>
  );
}
