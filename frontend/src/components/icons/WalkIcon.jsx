// Walking figure in lucide style (lucide has no "walk" icon).
function WalkIcon({ size = 20, strokeWidth = 1.8 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="13.5" cy="4" r="1.8" />
      <path d="M9 10.5 12 8l2.5 1.5 1.5 3 3 1" />
      <path d="m12 8-1.5 6 3 3 1 5" />
      <path d="m10.5 14-2 3.5L5 19" />
    </svg>
  );
}

export default WalkIcon;
