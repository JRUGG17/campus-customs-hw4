/**
 * Handsome Dan, drawn in SVG (no image files). Used in exactly two places:
 * the chat assistant's avatar/launcher, and peeking out under the Create Account button.
 *
 * variant "face": just his head (chat avatar).
 * variant "hang": paws gripping an edge above him, head hanging below, as if he's peeking
 *                 over the bottom edge of the nav bar.
 */
export default function HandsomeDan({
  variant = 'face',
  size = 48,
  className = '',
}: {
  variant?: 'face' | 'hang'
  size?: number
  className?: string
}) {
  const hang = variant === 'hang'
  return (
    <svg
      className={`dan ${className}`}
      width={size}
      height={hang ? size * 1.1 : size}
      viewBox={hang ? '0 0 120 132' : '0 0 120 120'}
      role="img"
      aria-label="Handsome Dan the bulldog"
    >
      {hang && (
        <>
          {/* front legs reaching up to the edge */}
          <path d="M26 8 L 30 40 L 44 40 L 40 8 Z" fill="#f4ede2" stroke="#2b2b2b" strokeWidth="2" />
          <path d="M94 8 L 90 40 L 76 40 L 80 8 Z" fill="#f4ede2" stroke="#2b2b2b" strokeWidth="2" />
          {/* paws gripping the edge */}
          <ellipse cx="33" cy="8" rx="13" ry="7" fill="#f4ede2" stroke="#2b2b2b" strokeWidth="2" />
          <ellipse cx="87" cy="8" rx="13" ry="7" fill="#f4ede2" stroke="#2b2b2b" strokeWidth="2" />
          <path d="M28 4 v6 M33 3 v7 M38 4 v6 M82 4 v6 M87 3 v7 M92 4 v6" stroke="#b9ad9c" strokeWidth="1.5" />
        </>
      )}
      <g transform={hang ? 'translate(0 16)' : undefined}>
        {/* ears */}
        <path d="M18 34 C 10 18, 26 10, 38 22 L 34 40 Z" fill="#7a5a44" />
        <path d="M102 34 C 110 18, 94 10, 82 22 L 86 40 Z" fill="#7a5a44" />
        {/* head */}
        <ellipse cx="60" cy="58" rx="44" ry="38" fill="#f4ede2" stroke="#2b2b2b" strokeWidth="2.5" />
        {/* brindle patch over one eye */}
        <path d="M24 44 C 28 30, 48 28, 52 44 C 50 56, 30 58, 24 44 Z" fill="#c9a27e" />
        {/* forehead wrinkles */}
        <path d="M46 30 q 14 -6 28 0" stroke="#b9ad9c" strokeWidth="2" fill="none" strokeLinecap="round" />
        <path d="M50 37 q 10 -4 20 0" stroke="#b9ad9c" strokeWidth="2" fill="none" strokeLinecap="round" />
        {/* eyes */}
        <g className="dan-eyes">
          <circle cx="40" cy="50" r="5.5" fill="#1d1d1d" />
          <circle cx="80" cy="50" r="5.5" fill="#1d1d1d" />
          <circle cx="42" cy="48" r="1.6" fill="#fff" />
          <circle cx="82" cy="48" r="1.6" fill="#fff" />
        </g>
        {/* jowls */}
        <ellipse cx="43" cy="76" rx="21" ry="15" fill="#fbf7f0" stroke="#2b2b2b" strokeWidth="2.5" />
        <ellipse cx="77" cy="76" rx="21" ry="15" fill="#fbf7f0" stroke="#2b2b2b" strokeWidth="2.5" />
        {/* underbite + teeth */}
        <path d="M44 88 Q 60 98 76 88 L 74 84 Q 60 90 46 84 Z" fill="#b5475a" stroke="#2b2b2b" strokeWidth="2" />
        <path d="M49 86 l 3 -6 l 3 6 Z" fill="#fff" stroke="#2b2b2b" strokeWidth="1.2" />
        <path d="M65 86 l 3 -6 l 3 6 Z" fill="#fff" stroke="#2b2b2b" strokeWidth="1.2" />
        {/* nose */}
        <path d="M50 62 Q 60 56 70 62 Q 70 70 60 72 Q 50 70 50 62 Z" fill="#1d1d1d" />
        <ellipse cx="56" cy="62" rx="2.5" ry="1.4" fill="#555" />
        {/* Yale-blue collar with a Y tag */}
        <path d="M30 94 Q 60 106 90 94" stroke="#00356b" strokeWidth="6" fill="none" strokeLinecap="round" />
        <circle cx="60" cy="104" r="7" fill="#00356b" />
        <text x="60" y="108" textAnchor="middle" fontFamily="Graduate, Georgia, serif" fontSize="10" fill="#fff">
          Y
        </text>
      </g>
    </svg>
  )
}
