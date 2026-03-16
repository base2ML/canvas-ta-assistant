const W = 480;
const H = 80;
const PAD_X = 40;
const Y_MID = 40;
const BOX_H = 24;

export default function GradeBoxPlot({ stats, pointsPossible }) {
  if (!stats || stats.n < 2) return null;

  const scale = (v) => PAD_X + Math.min(1, v / pointsPossible) * (W - 2 * PAD_X);

  const { min, q1, median, q3, max } = stats;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full">
      {/* Left whisker */}
      <line
        x1={scale(min)}
        y1={Y_MID}
        x2={scale(q1)}
        y2={Y_MID}
        stroke="#6b7280"
        strokeWidth={2}
      />
      {/* Right whisker */}
      <line
        x1={scale(q3)}
        y1={Y_MID}
        x2={scale(max)}
        y2={Y_MID}
        stroke="#6b7280"
        strokeWidth={2}
      />
      {/* IQR box */}
      <rect
        x={scale(q1)}
        y={Y_MID - BOX_H / 2}
        width={scale(q3) - scale(q1)}
        height={BOX_H}
        className="fill-blue-200 stroke-blue-500"
        strokeWidth={2}
      />
      {/* Median line */}
      <line
        x1={scale(median)}
        y1={Y_MID - BOX_H / 2}
        x2={scale(median)}
        y2={Y_MID + BOX_H / 2}
        stroke="#1d4ed8"
        strokeWidth={3}
      />
      {/* Min whisker cap */}
      <line
        x1={scale(min)}
        y1={Y_MID - 8}
        x2={scale(min)}
        y2={Y_MID + 8}
        stroke="#6b7280"
        strokeWidth={2}
      />
      {/* Max whisker cap */}
      <line
        x1={scale(max)}
        y1={Y_MID - 8}
        x2={scale(max)}
        y2={Y_MID + 8}
        stroke="#6b7280"
        strokeWidth={2}
      />
    </svg>
  );
}
