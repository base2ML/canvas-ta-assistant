const SVG_W = 480;
const SVG_H = 200;
const PAD = { top: 10, right: 10, bottom: 30, left: 36 };

export default function GradeHistogram({ bins, pointsPossible }) {
  if (!bins || bins.length === 0) return null;

  const innerW = SVG_W - PAD.left - PAD.right;
  const innerH = SVG_H - PAD.top - PAD.bottom;
  const barW = innerW / bins.length;
  const maxCount = Math.max(...bins.map((b) => b.count), 1);

  return (
    <svg viewBox={`0 0 ${SVG_W} ${SVG_H}`} className="w-full" aria-label={`Grade distribution out of ${pointsPossible} points`}>
      {bins.map((bin, i) => {
        const barH = (bin.count / maxCount) * innerH;
        const x = PAD.left + i * barW;
        const y = PAD.top + innerH - barH;
        return (
          <g key={i}>
            <rect
              x={x + 1}
              y={y}
              width={barW - 2}
              height={barH}
              className="fill-blue-400 hover:fill-blue-600"
            />
            {bin.count > 0 && (
              <text
                x={x + barW / 2}
                y={y - 2}
                textAnchor="middle"
                fontSize="9"
                className="fill-gray-600"
              >
                {bin.count}
              </text>
            )}
            <text
              x={x + barW / 2}
              y={SVG_H - 6}
              textAnchor="middle"
              fontSize="9"
              className="fill-gray-500"
            >
              {bin.bin_start}
            </text>
          </g>
        );
      })}
      <text
        x={12}
        y={SVG_H / 2}
        textAnchor="middle"
        fontSize="10"
        transform={`rotate(-90, 12, ${SVG_H / 2})`}
        className="fill-gray-500"
      >
        Count
      </text>
    </svg>
  );
}
