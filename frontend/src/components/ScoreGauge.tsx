interface ScoreGaugeProps {
  score: number;
  label: string;
  size?: "sm" | "lg";
}

function getScoreColor(score: number): string {
  if (score >= 75) return "#22c55e";
  if (score >= 60) return "#84cc16";
  if (score >= 45) return "#eab308";
  if (score >= 30) return "#f97316";
  return "#ef4444";
}

function getScoreLabel(score: number): string {
  if (score >= 75) return "Strong";
  if (score >= 60) return "Moderate";
  if (score >= 45) return "Neutral";
  if (score >= 30) return "Weak";
  return "Bearish";
}

export default function ScoreGauge({ score, label, size = "sm" }: ScoreGaugeProps) {
  const color = getScoreColor(score);
  const dim = size === "lg" ? 100 : 60;
  const strokeWidth = size === "lg" ? 8 : 5;
  const radius = (dim - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = (score / 100) * circumference;
  const fontSize = size === "lg" ? "1.2rem" : "0.8rem";

  return (
    <div style={{ textAlign: "center" }}>
      <svg width={dim} height={dim} viewBox={`0 0 ${dim} ${dim}`}>
        <circle
          cx={dim / 2}
          cy={dim / 2}
          r={radius}
          fill="none"
          stroke="#2a2a3e"
          strokeWidth={strokeWidth}
        />
        <circle
          cx={dim / 2}
          cy={dim / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeDasharray={`${progress} ${circumference}`}
          strokeLinecap="round"
          transform={`rotate(-90 ${dim / 2} ${dim / 2})`}
          style={{ transition: "stroke-dasharray 0.5s ease" }}
        />
        <text
          x="50%"
          y="50%"
          textAnchor="middle"
          dy="0.35em"
          fill={color}
          fontSize={fontSize}
          fontWeight="bold"
        >
          {score.toFixed(0)}
        </text>
      </svg>
      <div style={{ color: "#aaa", fontSize: "0.7rem", marginTop: 2 }}>
        {label}
      </div>
      {size === "lg" && (
        <div style={{ color, fontSize: "0.85rem", fontWeight: 600 }}>
          {getScoreLabel(score)}
        </div>
      )}
    </div>
  );
}
